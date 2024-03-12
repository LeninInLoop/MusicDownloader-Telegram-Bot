from run import Button
from utils import requests, asyncio, re, os, load_dotenv, combinations
from utils import db, process_flac_music, process_mp3_music
from utils import Image, BytesIO, YoutubeDL, lyricsgenius
from utils import SpotifyClientCredentials, spotipy

class Spotify_Downloader():

    @classmethod
    def _load_dotenv_and_create_folders(cls):
        try:
            load_dotenv('config.env')
            cls.SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
            cls.SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
            cls.GENIUS_ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
        except FileNotFoundError:
            print("Failed to Load .env variables")
        
        # Create a directory for the download
        cls.download_directory = "repository/Spotify_music"
        if not os.path.isdir(cls.download_directory):
            os.makedirs(cls.download_directory, exist_ok=True)
            
        cls.download_icon_directory = "repository/Spotify_icon"
        if not os.path.isdir(cls.download_icon_directory):
            os.makedirs(cls.download_icon_directory, exist_ok=True)

    @classmethod
    def initialize(cls):
        cls._load_dotenv_and_create_folders()
        cls.MAXIMUM_DOWNLOAD_SIZE_MB = 50
        cls.Spotify_info = {}
        cls.spotify_account = spotipy.Spotify(client_credentials_manager=
                SpotifyClientCredentials(client_id=cls.SPOTIFY_CLIENT_ID,
                                         client_secret=cls.SPOTIFY_CLIENT_SECRET))
        cls.genius = lyricsgenius.Genius(cls.GENIUS_ACCESS_TOKEN)
             
    @staticmethod
    def is_spotify_link(url):
        pattern = r'https?://open\.spotify\.com/.*'
        return re.match(pattern, url) is not None
    
    @staticmethod
    def identify_spotify_link_type(spotify_url) -> str:
        # Try to get the resource using the ID
        try:
            track = Spotify_Downloader.spotify_account.track(spotify_url)
            return 'track'
        except Exception as e:
            pass

        try:
            album = Spotify_Downloader.spotify_account.album(spotify_url)
            return 'album'
        except Exception as e:
            pass

        try:
            artist = Spotify_Downloader.spotify_account.artist(spotify_url)
            return 'artist'
        except Exception as e:
            pass

        try:
            playlist = Spotify_Downloader.spotify_account.playlist(spotify_url)
            return 'playlist'
        except Exception as e:
            pass
        
        return 'none'

    @staticmethod
    async def extract_data_from_spotify_link(event, spotify_url):
        user_id = event.sender_id
        link_info = {}

        link_type = Spotify_Downloader.identify_spotify_link_type(spotify_url)
        if link_type != "track":
            link_info = {
                'type': None,
                'track_name': None,
                'artist_name': None,
                'artist_ids': None,
                'artist_url': None,
                'album_name': None,
                'album_url': None,
                'release_year': None,
                'image_url': None,
                'track_id': None,
                'isrc': None,
                'track_url': None,
                'youtube_link': None,
                'preview_url': None,
                'duration_ms': None
            }
            await db.set_user_spotify_link_info(user_id, link_info)
            return

        track_info = Spotify_Downloader.spotify_account.track(spotify_url)

        artists = track_info['artists']
        album = track_info['album']

        link_info = {
            'type': "track",
            'track_name': track_info['name'],
            'artist_name': ', '.join(artist['name'] for artist in artists),
            'artist_ids': [artist['id'] for artist in artists],
            'artist_url': artists[0]['external_urls']['spotify'],
            'album_name': album['name'].translate(str.maketrans('', '', '()[]')),
            'album_url': album['external_urls']['spotify'],
            'release_year': album['release_date'].split('-')[0],
            'image_url': album['images'][0]['url'],
            'track_id': track_info['id'],
            'isrc': track_info['external_ids']['isrc'],
            'track_url': spotify_url,
            'youtube_link': track_info.get('external_urls', {}).get('youtube', None),
            'preview_url': track_info.get('preview_url', None),
            'duration_ms': track_info['duration_ms']
        }

        if link_info['youtube_link'] is None:
            link_info['youtube_link'] = await Spotify_Downloader.extract_yt_video_info(event, link_info)

        await db.set_user_spotify_link_info(user_id, link_info)
        
    @staticmethod
    async def extract_yt_video_info(event, spotify_link_info) -> str:
        if spotify_link_info is None:
            return None

        # Check if a YouTube link is provided
        video_url = spotify_link_info.get('youtube_link')
        if video_url:
            return video_url

        # Construct the search query
        artist_name = spotify_link_info["artist_name"]
        track_name = spotify_link_info["track_name"]
        release_year = spotify_link_info["release_year"]
        track_duration = spotify_link_info.get("duration_ms", 0) / 1000  # Convert milliseconds to seconds
        query = f'"{artist_name}" "{track_name}" lyrics {release_year} '

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'ytsearch': 8,  # Retrieve the top 8 search results
            'skip_download': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'  # Specify the desired format
        }

        with YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(f'ytsearch:{query}', download=False)
                entries = info.get('entries', [])

                for video_info in entries:
                    video_url = video_info.get('webpage_url')
                    video_duration = video_info.get('duration', 0)

                    # Compare the video duration with the track duration from Spotify
                    duration_diff = abs(video_duration - track_duration)
                    if duration_diff <= 40:  # Adjust the tolerance as needed
                        break
                    else:
                        video_url = None
            except Exception:
                video_url = None

        return video_url
        
    @staticmethod  
    async def download_and_send_spotify_info(client, event) -> bool :

        user_id = event.sender_id
        if not user_id in Spotify_Downloader.Spotify_info:
            Spotify_Downloader.Spotify_info[user_id] = None
        
        link_info = await db.get_user_spotify_link_info(user_id)
        if Spotify_Downloader.Spotify_info[user_id] != None:
            try:
                await Spotify_Downloader.Spotify_info[user_id].edit(buttons=None)
            except:
                pass
            
        music_quality, downloading_core = await db.get_user_settings(event.sender_id)
        if not await db.get_user_updated_flag(user_id) :
            await event.respond("We Have Updated The Bot, Please start Over using the /start command.")
            return True
        
        spotdl = True if downloading_core == "SpotDL" else False
        if not link_info["type"] == "track":
            await event.respond("The Provided Link is not a track.")
            return False
             
        artist_names = link_info['artist_name'].split(', ')
          
        # Generate all possible combinations of artist names
        for r in range(1, len(artist_names) +  1):
            for combination in combinations(artist_names, r):

                filename = f"{', '.join(combination)} - {link_info['track_name']}".replace("/", "")
                _filename = filename
                filename = filename + f"-{music_quality['quality']}" if spotdl == False else filename

                dir = f"{Spotify_Downloader.download_directory}/{filename}"
                file_path = f"{dir}.{music_quality['format']}"
                is_local = os.path.isfile(file_path)

                if is_local == True:
                    break
            if is_local == True:
                break
        
        icon_name = f"{link_info['track_name']} - {link_info['artist_name']}.jpeg".replace("/"," ")
        icon_path = os.path.join(Spotify_Downloader.download_icon_directory, icon_name)
        
        if not is_local:
            filename = f"{link_info['artist_name']} - {link_info['track_name']}".replace("/","")
            _filename = filename
            filename = filename + f"-{music_quality['quality']}" if spotdl == False else filename
            
            dir = f"{Spotify_Downloader.download_directory}/{filename}"
            file_path = f"{dir}.{music_quality['format']}"
            
        if not os.path.isfile(icon_path):
            response = requests.get(link_info["image_url"])
            img = Image.open(BytesIO(response.content))
            img.save(icon_path)
        
            
        listen_on_youtube_button = Button.url("Listen On Youtube", url=link_info['youtube_link']) if link_info['youtube_link'] else Button.inline("Listen On Youtube", data=b"@unavailable_feature")
        SpotifyInfoButtons = [
            [Button.inline("Download 30s Preview", data=b"@music_info_preview")],
            [Button.inline("Download Track", data=b"@music")],
            [Button.inline("Download Icon", data=b"@music_icon")],
            [Button.inline("Artist Info", data=b"@music_artist_info")],
            [Button.inline("Lyrics", data=b"@music_lyrics")],
            [Button.url("Listen On Spotify", url=link_info["track_url"]),
            listen_on_youtube_button],
            [Button.inline("Cancel", data=b"cancel")]
        ]

        try :    
            Spotify_Downloader.Spotify_info[user_id] = await client.send_file(
                event.chat_id,
                icon_path,
                caption=f"""
**🎧 Title:** [{link_info["track_name"]}]({link_info["track_url"]})
**🎤 Artist:** [{link_info["artist_name"]}]({link_info["artist_url"]})
**💽 Album:** [{link_info["album_name"]}]({link_info["album_url"]})
**🗓 Release Year:** {link_info["release_year"]}
**❗️ Is Local:** {is_local}
**🌐 ISRC:** {link_info["isrc"]}
**🔄 Downloaded:** {await db.get_song_downloads(_filename)} times

**Image URL:** [Click here]({link_info["image_url"]})
**Track id:** {link_info["track_id"]}
""",parse_mode='Markdown'
            ,buttons=SpotifyInfoButtons)
            
            return True
        except Exception as Err:
            return False
        
    @staticmethod
    async def send_localfile(client,event,file_info,spotify_link_info) -> bool:

        user_id = event.sender_id
        
        was_Local = file_info['is_local']
        file_path = file_info['file_path']
        icon_path = file_info['icon_path']
        video_url = file_info['video_url']
        
        is_local_message = await event.respond("Found in DataBase. Result in Sending Faster :)") if was_Local else None

        upload_message = await event.reply("Uploading")

        try:
            async with client.action(event.chat_id, 'document'):
                    await client.send_file(
                        event.chat_id,
                        file_path,
                        caption=f"""
💽 {spotify_link_info["track_name"]} - {spotify_link_info["artist_name"]}

-->[Listen On Spotify]({spotify_link_info["track_url"]})
-->[Listen On Youtube]({video_url})
            """,
                        supports_streaming=True,  # This flag enables streaming for compatible formats
                        force_document=False,  # This flag sends the file as a document or not
                        thumb=icon_path
                    )
        except:
            try:
                async with client.action(event.chat_id, 'document'):
                        await client.send_file(
                            event.chat_id,
                            file_path,
                            caption=f"""
💽 {spotify_link_info["track_name"]} - {spotify_link_info["artist_name"]}

-->[Listen On Spotify]({spotify_link_info["track_url"]})
-->[Listen On Youtube]({video_url})
                """,
                            supports_streaming=True,  # This flag enables streaming for compatible formats
                            force_document=False,  # This flag sends the file as a document or not
                            thumb=icon_path
                        )
            except Exception as e:
                await db.set_file_processing_flag(user_id,0)
                await event.respond(f"Failed To Upload.\nReason:{str(e)}")
            
        await is_local_message.delete() if was_Local else None
        await upload_message.delete()
        
        await db.set_file_processing_flag(user_id,0)
        return True
    
    @staticmethod
    async def download_SpotDL(event, music_quality, spotify_link_info, initial_message=None, audio_option: str = "piped") -> bool:
        user_id = event.sender_id
        command = f'python3 -m spotdl --client-id {Spotify_Downloader.SPOTIFY_CLIENT_ID} --client-secret {Spotify_Downloader.SPOTIFY_CLIENT_SECRET} --format {music_quality["format"]} --audio {audio_option} --output "{Spotify_Downloader.download_directory}" "{spotify_link_info["track_url"]}"'
        
        try:
            # Start the subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL
            )
        except Exception as e:
            Spotify_Downloader.logger.error(f"Failed to start subprocess. Error: {e}")
            await event.respond(f"Failed to download. Error: {e}")
            await db.set_file_processing_flag(user_id,0)
            return False

        if initial_message is None:
            # Send an initial message to the user with a progress bar
            initial_message = await event.reply("SpotDL: Downloading...\nApproach: Piped")

        # Function to send updates to the user
        async def send_updates(process, message):
            while True:
                # Read a line from stdout
                line = await process.stdout.readline()
                line = line.decode().strip()

                if audio_option == "piped":
                    await message.edit(f"SpotDL: Downloading...\nApproach: Piped\n\n{line}")
                elif audio_option == "soundcloud":
                    await message.edit(f"SpotDL: Downloading...\nApproach: SoundCloud\n\n{line}")
                else:
                    await message.edit(f"SpotDL: Downloading...\nApproach: YouTube\n\n{line}")
                
                # Check for errors
                if any(err in line for err in ("LookupError", "FFmpegError", "JSONDecodeError", "ReadTimeout", "KeyError", "Forbidden")):
                    if audio_option == "piped":
                        await message.edit(f"SpotDL: Downloading...\nApproach: Piped Failed, Using SoundCloud Approach.\n\n{line}")
                        return False  # Indicate that an error occurred
                    elif audio_option == "soundcloud":
                        await message.edit(f"SpotDL: Downloading...\nApproach: SoundCloud Failed, Using Youtube Approach.\n\n{line}")
                        return False
                    else:
                        await message.edit(f"SpotDL: Downloading...\nApproach: All Approaches Failed.\n\n{line}")
                        return False
                elif not line:
                    return True

        success = await send_updates(process, initial_message)       
        if not success and audio_option == "piped":
            await initial_message.edit(f"SpotDL: Downloading...\nApproach: Piped Failed, Using SoundCloud Approach.")       
            return False, initial_message
        elif not success and audio_option == "soundcloud":
            await initial_message.edit(f"SpotDL: Downloading...\nApproach: SoundCloud Failed, Using Youtube Approach.")       
            return False, initial_message
        elif not success and audio_option == "youtube":
            return False, False
        # Wait for the process to finish
        await process.wait()
        await initial_message.delete()
        return True, True

    @staticmethod
    async def download_YoutubeDL(event,file_info,music_quality):
        
        user_id = event.sender_id
        
        video_url = file_info['video_url']
        filename = file_info['file_name']
        
        download_message = await event.respond("Downloading .")

        # Define the options for yt-dlp to simulate the download
        ydl_opts_simulate = {
            'format': "bestaudio",
            'default_search': 'ytsearch',
            'noplaylist': True,
            "nocheckcertificate": True,
            "outtmpl": f"{Spotify_Downloader.download_directory}/{filename}",
            "quiet": True,
            "addmetadata": True,
            "prefer_ffmpeg": False,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "postprocessors": [{'key': 'FFmpegExtractAudio', 'preferredcodec': music_quality['format'], 'preferredquality': music_quality['quality']}],
            'simulate': True  # Simulate the download to get information without downloading
        }

        # Use yt-dlp to simulate the download and get the file size
        with YoutubeDL(ydl_opts_simulate) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            file_size = info_dict.get('filesize', None)
            if file_size and file_size > Spotify_Downloader.MAXIMUM_DOWNLOAD_SIZE_MB *  1024 *  1024:  # Check if file size is more than EXPECTED
                await event.respond("Err: File size is more than 50 MB.\nSkipping download.")
                await db.set_file_processing_flag(user_id,0)
                return False  # Skip the download

        await download_message.edit("Downloading . .")
        
        # If the file size is less than or equal to  50 MB, proceed with the actual download
        ydl_opts_download = {
            'format': "bestaudio",
            'default_search': 'ytsearch',
            'noplaylist': True,
            "nocheckcertificate": True,
            "outtmpl": f"{Spotify_Downloader.download_directory}/{filename}",
            "quiet": True,
            "addmetadata": True,
            "prefer_ffmpeg": False,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "postprocessors": [{'key': 'FFmpegExtractAudio', 'preferredcodec': music_quality['format'], 'preferredquality': music_quality['quality']}]
        }        
        
        try:
            # Run youtube-dl with the specified options and the video URL
            with YoutubeDL(ydl_opts_download) as ydl:
                ydl.download([video_url])
        except Exception as ERR:
            await event.respond(f"Something Went Wrong Processing Your Query.")
            await db.set_file_processing_flag(user_id,0)
            return False
        
        return True,download_message
        
    @staticmethod
    async def download_spotify_file_and_send(client,event) -> bool:
           
        user_id = event.sender_id
        music_quality, donwloading_core = await db.get_user_settings(event.sender_id)
        spotdl = True if donwloading_core == "SpotDL" else False
        
        if await db.get_file_processing_flag(user_id) == True:
            await event.respond("Sorry,There is already a file being processed for you.")
            return True
        
        spotify_link_info = await db.get_user_spotify_link_info(user_id)
        
        await db.set_file_processing_flag(user_id,1)
        
        if spotify_link_info['youtube_link'] == None and spotdl == False :
            await db.set_file_processing_flag(user_id,0)
            return False
        
        artist_names = spotify_link_info['artist_name'].split(', ')
          
        # Generate all possible combinations of artist names
        for r in range(1, len(artist_names) +  1):
            for combination in combinations(artist_names, r):

                filename = f"{', '.join(combination)} - {spotify_link_info['track_name']}".replace("/", "")
                _filename = filename
                filename = filename + f"-{music_quality['quality']}" if spotdl == False else filename

                dir = f"{Spotify_Downloader.download_directory}/{filename}"
                file_path = f"{dir}.{music_quality['format']}"
                is_local = os.path.isfile(file_path)

                if is_local == True:
                    break
            if is_local == True:
                break
        
        icon_name = f"{spotify_link_info['track_name']} - {spotify_link_info['artist_name']}.jpeg".replace("/"," ")
        icon_path = os.path.join(Spotify_Downloader.download_icon_directory, icon_name)
        
        if not is_local:
            filename = f"{spotify_link_info['artist_name']} - {spotify_link_info['track_name']}".replace("/","")
            _filename = filename
            filename = filename + f"-{music_quality['quality']}" if spotdl == False else filename
            
            dir = f"{Spotify_Downloader.download_directory}/{filename}"
            file_path = f"{dir}.{music_quality['format']}"
        
        await db.add_or_increment_song(_filename)
        
        file_info = {
            "file_name": filename,
            "file_path": file_path,
            "icon_path": icon_path,
            "is_local": is_local,
            "video_url": spotify_link_info['youtube_link']
        }  
        
        # Check if the file already exists
        if is_local:
            send_file_result = await Spotify_Downloader.send_localfile(client,event,file_info,spotify_link_info)
            return send_file_result
        
        elif is_local == False and spotdl == False:
            result,download_message = await Spotify_Downloader.download_YoutubeDL(event,file_info,music_quality)
            
            if os.path.isfile(file_path) and result == True:
                
                download_message = await download_message.edit("Downloading . . . .")
                flac_process_result, mp3_process_result = False, False
                
                if file_path.endswith('.flac'):
                    flac_process_result = await process_flac_music(event,file_info,spotify_link_info,download_message)
                    download_message = await download_message.edit("Downloading . . . . .")
                
                elif file_path.endswith('.mp3'):
                    mp3_process_result = await process_mp3_music(event,file_info,spotify_link_info,download_message)
                    download_message = await download_message.edit("Downloading . . . . .")

                await download_message.delete()
                
                send_file_result = await Spotify_Downloader.send_localfile(client,event,file_info,spotify_link_info)
                return True if (mp3_process_result or flac_process_result) and send_file_result else False
            else:
                return False
            
        elif is_local == False and spotdl == True:         
            result, initial_message = await Spotify_Downloader.download_SpotDL(event, music_quality, spotify_link_info)
            if result == False:
                result, initial_message = await Spotify_Downloader.download_SpotDL(event, music_quality, spotify_link_info, initial_message, audio_option="soundcloud")
                if result == False:
                    result, _ = await Spotify_Downloader.download_SpotDL(event, music_quality, spotify_link_info, initial_message, audio_option="youtube")
            if result == True and initial_message == True:
                if music_quality['format'] == "mp3":
                    await process_mp3_music(event,file_info,spotify_link_info)
                else:
                    await process_flac_music(event,file_info,spotify_link_info)
                return await Spotify_Downloader.send_localfile(client,event,file_info,spotify_link_info) if result else False
            else:
                return False
            
    @staticmethod
    async def search_spotify_based_on_user_input(event, query, limit=50):
        results = Spotify_Downloader.spotify_account.search(q=query, limit=limit)
        song_pages = {}
        page_idx = 1

        for i, t in enumerate(results['tracks']['items']):
            artists = ', '.join([a['name'] for a in t['artists']])
            spotify_link = t['external_urls']['spotify']
            song_details = {
                'track_name': t['name'],
                'artist': artists,
                'release_year': t['album']['release_date'][:4],
                'spotify_link': spotify_link
            }

            if i % 10 == 0:
                song_pages[page_idx] = []
                page_idx += 1

            song_pages[page_idx - 1].append(song_details)

        await db.set_user_song_dict(event.sender_id, song_pages)

    @staticmethod
    async def send_30s_preview(client,event):
        user_id = event.sender_id
        spotify_link_info = await db.get_user_spotify_link_info(user_id)
        if spotify_link_info['type'] == "track":
            try:
                preview_url = spotify_link_info['preview_url']
                if preview_url:
                    await client.send_file(event.chat_id, preview_url, voice=True)
                else:
                    await event.respond("Sorry, the preview URL for this track is not available.")
            except Exception:
                await event.respond("An error occurred while sending the preview.")
        else:
            await event.respond("Sorry, I can only send previews for tracks, not albums or artists.")
    
    @staticmethod
    async def send_artists_info(event):
        user_id = event.sender_id
        artist_details = []
        spotify_link_info = await db.get_user_spotify_link_info(user_id)

        def format_number(number):
            if number >= 1000000000:
                return f"{number // 1000000000}.{(number % 1000000000) // 100000000}B"
            elif number >= 1000000:
                return f"{number // 1000000}.{(number % 1000000) // 100000}M"
            elif number >= 1000:
                return f"{number // 1000}.{(number % 1000) // 100}K"
            else:
                return str(number)
        
        for artist_id in spotify_link_info['artist_ids']:
            artist = Spotify_Downloader.spotify_account.artist(artist_id)
            artist_details.append({
                'name': artist['name'],
                'followers': format_number(artist['followers']['total']),
                'genres': artist['genres'],
                'popularity': artist['popularity'],
                'image_url': artist['images'][0]['url'] if artist['images'] else None,
                'external_url': artist['external_urls']['spotify']
            })

        # Create a professional artist info message with more details and formatting
        message = "🎤 <b>Artists Information</b> :\n\n"
        for artist in artist_details:
            message += f"🌟 <b>Artist Name:</b> {artist['name']}\n"
            message += f"👥 <b>Followers:</b> {artist['followers']}\n"
            message += f"🎵 <b>Genres:</b> {', '.join(artist['genres'])}\n"
            message += f"📈 <b>Popularity:</b> {artist['popularity']}\n"
            if artist['image_url']:
                message += f"\n🖼️ <b>Image:</b> <a href='{artist['image_url']}'>Image Url</a>\n"
            message += f"🔗 <b>Spotify URL:</b> <a href='{artist['external_url']}'>Spotify Link</a>\n\n"
            message += "───────────\n\n"

        # Create buttons with URLs
        artist_buttons = [
            [Button.url(f"🎧 {artist['name']}", artist['external_url'])]
            for artist in artist_details
        ]
        artist_buttons.append([Button.inline("Remove",data='cancel')])
        
        await event.respond(message, parse_mode='html', buttons=artist_buttons)

    @staticmethod
    async def send_music_lyrics(event):
        MAX_MESSAGE_LENGTH = 4096  # Telegram's maximum message length
        SECTION_HEADER_PATTERN = r'\[.+?\]'  # Pattern to match section headers
        
        user_id = event.sender_id
        spotify_link_info = await db.get_user_spotify_link_info(user_id)
        waiting_message = await event.respond("Searching For Lyrics in Genius ....")
        song = Spotify_Downloader.genius.search_song(f""" "{spotify_link_info['track_name']}"+"{spotify_link_info['artist_name']}" """)
        if song:
            await waiting_message.delete()
            lyrics = song.lyrics
            
            print(lyrics)
            if not lyrics:
                error_message = "Sorry, I couldn't find the lyrics for this track."
                return await event.respond(error_message)
            
            # Remove 'Embed' and the first line of the lyrics
            lyrics = song.lyrics.strip().split('\n', 1)[-1]
            lyrics = lyrics.replace('Embed', '').strip()
        
            metadata = f"**Song:** {spotify_link_info['track_name']}\n**Artist:** {spotify_link_info['artist_name']}\n\n"

            # Split the lyrics into multiple messages if necessary
            lyrics_chunks = []
            current_chunk = ""
            section_lines = []
            for line in lyrics.split('\n'):
                if re.match(SECTION_HEADER_PATTERN, line) or not section_lines:
                    if section_lines:
                        section_text = '\n'.join(section_lines)
                        if len(current_chunk) + len(section_text) + 2 <= MAX_MESSAGE_LENGTH:
                            current_chunk += section_text + "\n"
                        else:
                            lyrics_chunks.append(f"```{current_chunk.strip()}```")
                            current_chunk = section_text + "\n"
                    section_lines = [line]
                else:
                    section_lines.append(line)
            
            # Add the last section to the chunks
            if section_lines:
                section_text = '\n'.join(section_lines)
                if len(current_chunk) + len(section_text) + 2 <= MAX_MESSAGE_LENGTH:
                    current_chunk += section_text + "\n"
                else:
                    lyrics_chunks.append(f"```{current_chunk.strip()}```")
                    current_chunk = section_text + "\n"
            if current_chunk:
                lyrics_chunks.append(f"```{current_chunk.strip()}```")

            for i, chunk in enumerate(lyrics_chunks, start=1):
                page_header = f"Page {i}/{len(lyrics_chunks)}\n"
                if chunk == "``````":
                    error_message = "Sorry, I couldn't find the lyrics for this track."
                    return await event.respond(error_message)
                message = metadata + chunk + page_header
                await event.respond(message, buttons=[Button.inline("Remove", data='cancel')])
        else:   
            error_message = "Sorry, I couldn't find the lyrics for this track."
            return await event.respond(error_message)
        
    @staticmethod
    async def send_music_icon(client, event):
        try:
            user_id = event.sender_id
            spotify_link_info = await db.get_user_spotify_link_info(user_id)

            if spotify_link_info:
                track_name = spotify_link_info['track_name']
                artist_name = spotify_link_info['artist_name']
                icon_name = f"{track_name} - {artist_name}.jpeg".replace("/", " ")
                icon_path = os.path.join(Spotify_Downloader.download_icon_directory, icon_name)

                if os.path.isfile(icon_path):
                    async with client.action(event.chat_id, 'document'):
                        await client.send_file(
                            event.chat_id,
                            icon_path,
                            caption=f"{track_name} - {artist_name}",
                            force_document=True
                        )
                else:
                    await event.reply("Sorry, the music icon is currently unavailable.")
            else:
                await event.reply("No Spotify link information found. Please make sure you have provided a valid Spotify link.")
        except Exception:
            await event.reply("An error occurred while processing your request. Please try again later.")
