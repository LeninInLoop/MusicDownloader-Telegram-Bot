from run import Button
from utils import requests, asyncio, re, os, load_dotenv, combinations
from utils import db, process_flac_music, process_mp3_music
from utils import Image, BytesIO, YoutubeDL, lyricsgenius
from utils import SpotifyClientCredentials, spotipy

class SpotifyDownloader():

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
            track = SpotifyDownloader.spotify_account.track(spotify_url)
            return 'track'
        except Exception as e:
            pass

        try:
            album = SpotifyDownloader.spotify_account.album(spotify_url)
            return 'album'
        except Exception as e:
            pass

        try:
            artist = SpotifyDownloader.spotify_account.artist(spotify_url)
            return 'artist'
        except Exception as e:
            pass

        try:
            playlist = SpotifyDownloader.spotify_account.playlist(spotify_url)
            return 'playlist'
        except Exception as e:
            pass
        
        return 'none'

    @staticmethod
    def compile_track_info(track_info):
        """Compile and return track information from a Spotify track object."""
        artists = track_info['artists']
        album = track_info['album']
        return {
            'type': track_info['type'],
            'track_name': track_info['name'],
            'artist_name': ', '.join(artist['name'] for artist in artists),
            'artist_ids': [artist['id'] for artist in artists],
            'artist_url': artists[0]['external_urls']['spotify'],
            'album_name': album['name'],
            'album_url': album['external_urls']['spotify'],
            'release_year': album['release_date'].split('-')[0],
            'image_url': album['images'][0]['url'],
            'track_id': track_info['id'],
            'isrc': track_info['external_ids'].get('isrc'),
            'track_url': track_info['external_urls']['spotify'],
            'youtube_link': None,  # This could be enhanced separately if needed
            'preview_url': track_info.get('preview_url'),
            'duration_ms': track_info['duration_ms']
        }
        
    @staticmethod
    async def extract_data_from_spotify_link(event, spotify_url):
        user_id = event.sender_id

        # Identify the type of Spotify link to handle the data extraction accordingly
        link_type = SpotifyDownloader.identify_spotify_link_type(spotify_url)

        try:
            if link_type == "track":
                # Extract track information and construct the link_info dictionary
                track_info = SpotifyDownloader.spotify_account.track(spotify_url)
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
                    'youtube_link': None,  # Placeholder, will be resolved below
                    'preview_url': track_info.get('preview_url'),
                    'duration_ms': track_info['duration_ms']
                }

                # Attempt to enhance track info with additional external data (e.g., YouTube link)
                link_info['youtube_link'] = await SpotifyDownloader.extract_yt_video_info(link_info)

            elif link_type == "playlist":
                # Extract playlist information and compile playlist tracks into a dictionary
                playlist_info = SpotifyDownloader.spotify_account.playlist(spotify_url)
                playlist_tracks_info = SpotifyDownloader.spotify_account.playlist_tracks(spotify_url)['items']
                
                playlist_info_dict = {
                    'type': 'playlist',
                    'playlist_name': playlist_info['name'],
                    'playlist_id': playlist_info['id'],
                    'playlist_url': playlist_info['external_urls']['spotify'],
                    'playlist_owner': playlist_info['owner']['display_name'],
                    'playlist_image_url': playlist_info['images'][0]['url'] if playlist_info['images'] else None,
                    'playlist_followers': playlist_info['followers']['total'],
                    'playlist_public': playlist_info['public'],
                    'playlist_tracks_total': playlist_info['tracks']['total'],
                    'playlist_tracks': {i + 1: SpotifyDownloader.compile_track_info(track['track'])
                                        for i, track in enumerate(playlist_tracks_info)}
                }
                link_info = playlist_info_dict

            else:
                # Handle unsupported Spotify link types
                link_info = {}
                print(f"Unsupported Spotify link type provided: {spotify_url}")

            # Store the extracted information in the database
            await db.set_user_spotify_link_info(user_id, link_info)

        except Exception as e:
            # Log and handle any errors encountered during information extraction
            print(f"Error extracting Spotify information: {e}")
            await event.respond("An error occurred while processing the Spotify link. Please try again.")
            return False

        return True

        
    @staticmethod
    async def extract_yt_video_info(spotify_link_info) -> str:
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
                    if duration_diff <= 35:
                        break
                    else:
                        video_url = None
            except Exception:
                video_url = None

        return video_url
    
    @staticmethod
    async def download_and_send_spotify_info(client, event) -> bool:
        user_id = event.sender_id

        # Initialize user's Spotify info if not already present
        SpotifyDownloader.Spotify_info.setdefault(user_id, None)

        # Retrieve user's Spotify link info from the database
        link_info = await db.get_user_spotify_link_info(user_id)

        # Dismiss any previous Spotify info buttons, if applicable
        previous_info = SpotifyDownloader.Spotify_info.get(user_id)
        if previous_info is not None:
            try:
                await previous_info.edit(buttons=None)
            except Exception as e:
                print(f"Failed to edit previous message for user {user_id}: {e}")

        # Ensure the user's data is up to date
        if not await db.get_user_updated_flag(user_id):
            await event.respond(
                "Our bot has been updated. Please restart the bot with the /start command."
            )
            return True

        # Determine and handle the type of Spotify link (track or playlist)
        if link_info['type'] == "track":
            return await SpotifyDownloader.send_track_info(client, event, link_info)
        elif link_info['type'] == "playlist":
            return await SpotifyDownloader.send_playlist_info(client, event, link_info)
        else:
            await event.respond("Unsupported Spotify link type. Please try another link.")
            return False
            
    # @staticmethod  
    # async def download_and_send_spotify_info(client, event) -> bool :

    #     user_id = event.sender_id
    #     if not user_id in SpotifyDownloader.Spotify_info:
    #         SpotifyDownloader.Spotify_info[user_id] = None
        
    #     link_info = await db.get_user_spotify_link_info(user_id)
    #     if SpotifyDownloader.Spotify_info[user_id] != None:
    #         try:
    #             await SpotifyDownloader.Spotify_info[user_id].edit(buttons=None)
    #         except:
    #             pass
            
    #     if not await db.get_user_updated_flag(user_id) :
    #         await event.respond("We Have Updated The Bot, Please start Over using the /start command.")
    #         return True
        
    #     if link_info['type'] == "track":
    #         return await SpotifyDownloader.send_track_info(client,event,link_info)
            
    #     elif link_info['type'] == "playlist":
    #         return await SpotifyDownloader.send_playlist_info(client,event,link_info)

    @staticmethod
    async def fetch_and_save_playlist_image(playlist_id, playlist_image_url):
        icon_name = f"{playlist_id}.jpeg"
        icon_path = os.path.join(SpotifyDownloader.download_icon_directory, icon_name)
        try:
            response = requests.get(playlist_image_url)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                img.save(icon_path)
                return icon_path
        except Exception as e:
            print(f"Error downloading or saving playlist image: {e}")
        return None
    
    @staticmethod
    async def send_playlist_info(client, event, link_info):
        playlist_image_url = link_info.get('playlist_image_url')
        playlist_name = link_info.get('playlist_name', 'Unavailable')
        playlist_id = link_info.get('playlist_id', 'Unavailable')
        playlist_url = link_info.get('playlist_url', 'Unavailable')
        playlist_owner = link_info.get('playlist_owner', 'Unavailable')
        total_tracks = link_info.get('playlist_tracks_total', 0)
        collaborative = 'Yes' if link_info.get('collaborative', False) else 'No'
        public = 'Yes' if link_info.get('playlist_public', False) else 'No'
        followers = link_info.get('playlist_followers', 'Unavailable')

        # Construct the playlist information text
        playlist_info = (
            f"🎧 **Playlist: {playlist_name}** 🎶\n\n"
            f"---\n\n"
            f"**Details:**\n\n"

            f"    - 👤 Owner: {playlist_owner}\n"
            f"    - 👥 Followers: {followers}\n"
            
            f"    - 🎵 Total Tracks: {total_tracks}\n"
            f"    - 🤝 Collaborative: {collaborative}\n"
            f"    - 🌐 Public: {public}\n"

            f"    - 🎧 Playlist URL: [Listen On Spotify]({playlist_url})\n"
            f"---\n\n"
            f"**Enjoy the music!** 🎶"
        )

        # Buttons for interactivity
        buttons = [
            [Button.inline("Download Top 10", data=b"@playlist_download_10")],
            [Button.inline("Search Tracks inside", data=b"@playlist_search")],
            [Button.inline("Cancel", data=b"cancel")]
        ]

        # Handle the playlist image if exists
        if playlist_image_url:
            icon_path = await SpotifyDownloader.fetch_and_save_playlist_image(playlist_id, playlist_image_url)
            if icon_path:
                sent_message = await client.send_file(
                    event.chat_id,
                    icon_path,
                    caption=playlist_info,
                    parse_mode='Markdown',
                    buttons=buttons,
                )
            else:
                sent_message = await event.respond(playlist_info, parse_mode='Markdown', buttons=buttons)
        else:
            sent_message = await event.respond(playlist_info, parse_mode='Markdown', buttons=buttons)

        # Store the sent message information
        SpotifyDownloader.Spotify_info[event.sender_id] = sent_message
        return True
                
    @staticmethod
    async def send_track_info(client, event, link_info):
        user_id = event.sender_id
        music_quality, downloading_core = await db.get_user_settings(user_id)
        
        if downloading_core == "Auto":
            spotdl = True if (link_info.get('youtube_link') is None) else False
        else:
            spotdl = downloading_core == "SpotDL"
        
        def build_file_path(artist, track_name, quality_info, format, make_dir=False):
            filename = f"{artist} - {track_name}".replace("/", "")
            if not spotdl:
                filename += f"-{quality_info['quality']}"
            directory = os.path.join(SpotifyDownloader.download_directory, filename)
            if make_dir and not os.path.exists(directory):
                os.makedirs(directory)
            return f"{directory}.{quality_info['format']}"
        
        def is_track_local(artist_names, track_name):
            for r in range(1, len(artist_names) + 1):
                for combination in combinations(artist_names, r):
                    file_path = build_file_path(", ".join(combination), track_name, music_quality, music_quality['format'])
                    if os.path.isfile(file_path):
                        return True, file_path
            return False, None
        
        artist_names = link_info['artist_name'].split(', ')
        is_local, file_path = is_track_local(artist_names, link_info['track_name'])
        
        icon_name = f"{link_info['track_name']} - {link_info['artist_name']}.jpeg".replace("/", " ")
        icon_path = os.path.join(SpotifyDownloader.download_icon_directory, icon_name)
        
        if not os.path.isfile(icon_path):
            try:
                response = requests.get(link_info["image_url"])
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    img.save(icon_path)
            except Exception as e:
                print(f"Failed to download or save track image: {e}")
        
        SpotifyInfoButtons = [
            [Button.inline("Download 30s Preview", data=b"@music_info_preview")],
            [Button.inline("Download Track", data=b"@music")],
            [Button.inline("Download Icon", data=b"@music_icon")],
            [Button.inline("Artist Info", data=b"@music_artist_info")],
            [Button.inline("Lyrics", data=b"@music_lyrics")],
            [Button.url("Listen On Spotify", url=link_info["track_url"]),
            Button.url("Listen On Youtube", url=link_info['youtube_link']) if link_info['youtube_link'] else Button.inline("Listen On Youtube", data=b"@unavailable_feature")],
            [Button.inline("Cancel", data=b"cancel")]
        ]

        caption = (
            f"**🎧 Title:** [{link_info['track_name']}]({link_info['track_url']})\n"
            f"**🎤 Artist:** [{link_info['artist_name']}]({link_info['artist_url']})\n"
            f"**💽 Album:** [{link_info['album_name']}]({link_info['album_url']})\n"
            f"**🗓 Release Year:** {link_info['release_year']}\n"
            f"**❗️ Is Local:** {is_local}\n"
            f"**🌐 ISRC:** {link_info['isrc']}\n"
            f"**🔄 Downloaded:** {await db.get_song_downloads(file_path)} times\n\n"
            f"**Image URL:** [Click here]({link_info['image_url']})\n"
            f"**Track id:** {link_info['track_id']}\n"
        )

        try:
            SpotifyDownloader.Spotify_info[user_id] = await client.send_file(
                event.chat_id,
                icon_path,
                caption=caption,
                parse_mode='Markdown',
                buttons=SpotifyInfoButtons
            )
            return True
        except Exception as Err:
            print(f"Failed to send track info: {Err}")
            return False
            
            
    @staticmethod
    async def send_local_file(client, event, file_info, spotify_link_info, playlist:bool = False) -> bool:
        user_id = event.sender_id

        # Unpack file_info for clarity
        was_local = file_info['is_local']
        file_path = file_info['file_path']
        icon_path = file_info['icon_path']
        video_url = file_info['video_url']

        # Notify the user about local availability for faster processing, if applicable
        local_availability_message = None
        if was_local and not playlist:
            local_availability_message = await event.respond("This track is available locally. Preparing it for you now...")

        # Provide feedback to the user during the upload process
        if not playlist:
            upload_status_message = await event.reply("Now uploading... Please hold on.")

        try:
            # Indicate ongoing file upload to enhance user experience
            async with client.action(event.chat_id, 'document'):
                await client.send_file(
                    event.chat_id,
                    file_path,
                    caption=(
                        f"🎵 **{spotify_link_info['track_name']}** by **{spotify_link_info['artist_name']}**\n\n"
                        f"▶️  [Listen on Spotify]({spotify_link_info['track_url']})\n"
                        f"🎥  [Watch on YouTube]({video_url})"
                    ),
                    supports_streaming=True,
                    force_document=False,
                    thumb=icon_path
                )

        except Exception as e:
            # Handle exceptions and provide feedback
            await db.set_file_processing_flag(user_id, 0)  # Reset file processing flag
            await event.respond(f"Unfortunately, uploading failed.\nReason: {e}")
            return False  # Returning False signifies the operation didn't complete successfully

        # Clean up feedback messages
        if local_availability_message:
            await local_availability_message.delete()
        
        if not playlist:
            await upload_status_message.delete()

        # Reset file processing flag after completion
        await db.set_file_processing_flag(user_id, 0)
        
        # Indicate successful upload operation
        return True
    
#     @staticmethod
#     async def send_local_file(client,event,file_info,spotify_link_info) -> bool:

#         user_id = event.sender_id
        
#         was_Local = file_info['is_local']
#         file_path = file_info['file_path']
#         icon_path = file_info['icon_path']
#         video_url = file_info['video_url']
        
#         is_local_message = await event.respond("Found in DataBase. Result in Sending Faster :)") if was_Local else None

#         upload_message = await event.reply("Uploading")

#         try:
#             async with client.action(event.chat_id, 'document'):
#                     await client.send_file(
#                         event.chat_id,
#                         file_path,
#                         caption=f"""
# 💽 {spotify_link_info["track_name"]} - {spotify_link_info["artist_name"]}

# -->[Listen On Spotify]({spotify_link_info["track_url"]})
# -->[Listen On Youtube]({video_url})
#             """,
#                         supports_streaming=True,  # This flag enables streaming for compatible formats
#                         force_document=False,  # This flag sends the file as a document or not
#                         thumb=icon_path
#                     )
                    
#         except Exception as e:
#             await db.set_file_processing_flag(user_id,0)
#             await event.respond(f"Failed To Upload.\nReason:{str(e)}")
            
#         await is_local_message.delete() if was_Local else None
#         await upload_message.delete()
        
#         await db.set_file_processing_flag(user_id,0)
#         return True
    
    @staticmethod
    async def download_SpotDL(event, music_quality, spotify_link_info, quite:bool = False, initial_message=None, audio_option: str = "piped") -> bool:
        user_id = event.sender_id
        command = f'python3 -m spotdl --client-id {SpotifyDownloader.SPOTIFY_CLIENT_ID} --client-secret {SpotifyDownloader.SPOTIFY_CLIENT_SECRET} --format {music_quality["format"]} --audio {audio_option} --output "{SpotifyDownloader.download_directory}" --threads {15} "{spotify_link_info["track_url"]}"'
        
        try:
            # Start the subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL
            )
        except Exception as e:
            await event.respond(f"Failed to download. Error: {e}")
            await db.set_file_processing_flag(user_id,0)
            return False

        if initial_message is None and not quite:
            # Send an initial message to the user with a progress bar
            initial_message = await event.reply("SpotDL: Downloading...\nApproach: Piped")
        elif quite:
            initial_message = None
            
        # Function to send updates to the user
        async def send_updates(process, message):
            while True:
                # Read a line from stdout
                line = await process.stdout.readline()
                line = line.decode().strip()

                if not quite:
                    if audio_option == "piped":
                        await message.edit(f"SpotDL: Downloading...\nApproach: Piped\n\n{line}")
                    elif audio_option == "soundcloud":
                        await message.edit(f"SpotDL: Downloading...\nApproach: SoundCloud\n\n{line}")
                    else:
                        await message.edit(f"SpotDL: Downloading...\nApproach: YouTube\n\n{line}")
                
                # Check for errors
                if any(err in line for err in ("LookupError", "FFmpegError", "JSONDecodeError", "ReadTimeout", "KeyError", "Forbidden")):
                    if audio_option == "piped":
                        if not quite:
                            await message.edit(f"SpotDL: Downloading...\nApproach: Piped Failed, Using SoundCloud Approach.\n\n{line}")
                        return False  # Indicate that an error occurred
                    elif audio_option == "soundcloud":
                        if not quite:
                            await message.edit(f"SpotDL: Downloading...\nApproach: SoundCloud Failed, Using Youtube Approach.\n\n{line}")
                        return False
                    else:
                        if not quite:
                            await message.edit(f"SpotDL: Downloading...\nApproach: All Approaches Failed.\n\n{line}")
                        return False
                elif not line:
                    return True

        success = await send_updates(process, initial_message)       
        if not success and audio_option == "piped":
            if not quite:
                await initial_message.edit(f"SpotDL: Downloading...\nApproach: Piped Failed, Using SoundCloud Approach.")       
            return False, initial_message
        elif not success and audio_option == "soundcloud":
            if not quite:
                await initial_message.edit(f"SpotDL: Downloading...\nApproach: SoundCloud Failed, Using Youtube Approach.")       
            return False, initial_message
        elif not success and audio_option == "youtube":
            return False, False
        # Wait for the process to finish
        await process.wait()
        await initial_message.delete() if initial_message else None
        return True, True

    @staticmethod
    async def download_YoutubeDL(event, file_info, music_quality, playlist:bool = False):
        user_id = event.sender_id
        video_url = file_info['video_url']
        filename = file_info['file_name']

        download_message = None
        if not playlist:
            download_message = await event.respond("Downloading .")

        async def get_file_size(video_url):
            ydl_opts = {
                'format': "bestaudio",
                'default_search': 'ytsearch',
                'noplaylist': True,
                "nocheckcertificate": True,
                "quiet": True,
                "geo_bypass": True,
                "nocheckcertificate": True,
                'get_filesize': True  # Retrieve the file size without downloading
            }

            with YoutubeDL(ydl_opts) as ydl:
                info_dict = await asyncio.to_thread(ydl.extract_info, video_url, download=False)
                file_size = info_dict.get('filesize', None)
                return file_size

        async def download_audio(video_url, filename, music_quality):
            ydl_opts = {
                'format': "bestaudio",
                'default_search': 'ytsearch',
                'noplaylist': True,
                "nocheckcertificate": True,
                "outtmpl": f"{SpotifyDownloader.download_directory}/{filename}",
                "quiet": True,
                "addmetadata": True,
                "prefer_ffmpeg": False,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "postprocessors": [{'key': 'FFmpegExtractAudio', 'preferredcodec': music_quality['format'], 'preferredquality': music_quality['quality']}]
            }

            with YoutubeDL(ydl_opts) as ydl:
                await asyncio.to_thread(ydl.extract_info, video_url, download=True)

        async def download_handler():
            file_size_task = asyncio.create_task(get_file_size(video_url))
            file_size = await file_size_task

            if file_size and file_size > SpotifyDownloader.MAXIMUM_DOWNLOAD_SIZE_MB * 1024 * 1024:
                await event.respond("Err: File size is more than 50 MB.\nSkipping download.")
                await db.set_file_processing_flag(user_id, 0)
                return False, None  # Skip the download

            if not playlist:
                await download_message.edit("Downloading . .")

            download_task = asyncio.create_task(download_audio(video_url, filename, music_quality))
            try:
                await download_task
                return True, download_message
            except Exception as ERR:
                await event.respond(f"Something Went Wrong Processing Your Query.")
                await db.set_file_processing_flag(user_id, 0)
                return False, download_message

        return await download_handler()

    @staticmethod
    async def download_spotify_file_and_send(client,event) -> bool:
           
        user_id = event.sender_id

        if await db.get_file_processing_flag(user_id) == True:
            await event.respond("Sorry,There is already a file being processed for you.")
            return True
        
        spotify_link_info = await db.get_user_spotify_link_info(user_id)
        
        await db.set_file_processing_flag(user_id,1)
        
        if spotify_link_info['type'] == "track":
            return await SpotifyDownloader.download_track(client,event,spotify_link_info)
        elif spotify_link_info['type'] == "playlist":
            print(spotify_link_info)
         
    @staticmethod
    async def download_track(client, event, spotify_link_info):
        user_id = event.sender_id
        music_quality, downloading_core = await db.get_user_settings(user_id)
        
        if downloading_core == "Auto":
            spotdl = True if (spotify_link_info.get('youtube_link') is None) else False
        else:
            spotdl = downloading_core == "SpotDL"

        if (spotify_link_info.get('youtube_link',None) is None) and not spotdl:
            await db.set_file_processing_flag(user_id, 0)
            return False

        file_path, filename, is_local = SpotifyDownloader._determine_file_path(spotify_link_info, music_quality, spotdl)


        await db.add_or_increment_song(spotify_link_info['track_name'])

        file_info = {
            "file_name": filename,
            "file_path": file_path,
            "icon_path": SpotifyDownloader._get_icon_path(spotify_link_info),
            "is_local": is_local,
            "video_url": spotify_link_info.get('youtube_link')
        }

        if is_local:
            return await SpotifyDownloader.send_local_file(client, event, file_info, spotify_link_info)
        else:
            return await SpotifyDownloader._handle_download(client, event, spotify_link_info, music_quality, file_info, spotdl)

    @staticmethod
    async def _handle_download(client, event, spotify_link_info, music_quality, file_info, spotdl):
        file_path = file_info["file_path"]
        if spotdl == False:
            result,download_message = await SpotifyDownloader.download_YoutubeDL(event,file_info,music_quality)
            
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
                
                send_file_result = await SpotifyDownloader.send_local_file(client,event,file_info,spotify_link_info)
                return True if (mp3_process_result or flac_process_result) and send_file_result else False
            else:
                return False
            
        elif spotdl == True:         
            result, initial_message = await SpotifyDownloader.download_SpotDL(event, music_quality, spotify_link_info)
            if result == False:
                result, initial_message = await SpotifyDownloader.download_SpotDL(event, music_quality, spotify_link_info, False, initial_message, audio_option="soundcloud")
                if result == False:
                    result, _ = await SpotifyDownloader.download_SpotDL(event, music_quality, spotify_link_info, False, initial_message, audio_option="youtube")
            if result == True and initial_message == True:
                if music_quality['format'] == "mp3":
                    await process_mp3_music(event,file_info,spotify_link_info)
                else:
                    await process_flac_music(event,file_info,spotify_link_info)
                return await SpotifyDownloader.send_local_file(client,event,file_info,spotify_link_info) if result else False
            else:
                return False
            
    @staticmethod
    def _get_icon_path(spotify_link_info):
        icon_name = f"{spotify_link_info['track_name']} - {spotify_link_info['artist_name']}.jpeg".replace("/", " ")
        return os.path.join(SpotifyDownloader.download_icon_directory, icon_name)

    @staticmethod
    def _determine_file_path(spotify_link_info, music_quality, spotdl):
        artist_names = spotify_link_info['artist_name'].split(', ')
        for r in range(1, len(artist_names) + 1):
            for combination in combinations(artist_names, r):
                filename = f"{', '.join(combination)} - {spotify_link_info['track_name']}".replace("/", "")
                filename += f"-{music_quality['quality']}" if not spotdl else ""
                file_path = os.path.join(SpotifyDownloader.download_directory, f"{filename}.{music_quality['format']}")
                if os.path.isfile(file_path):
                    return file_path, filename, True
        filename = f"{spotify_link_info['artist_name']} - {spotify_link_info['track_name']}".replace("/", "")
        filename += f"-{music_quality['quality']}" if not spotdl else ""
        return os.path.join(SpotifyDownloader.download_directory, f"{filename}.{music_quality['format']}"), filename, False
   
    # @staticmethod
    # async def download_track(client,event,spotify_link_info):

    #     user_id = event.sender_id
        
    #     music_quality, donwloading_core = await db.get_user_settings(event.sender_id)
    #     spotdl = True if donwloading_core == "SpotDL" else False
        
    #     if spotify_link_info['youtube_link'] == None and spotdl == False :
    #         await db.set_file_processing_flag(user_id,0)
    #         return False
        
    #     artist_names = spotify_link_info['artist_name'].split(', ')
        
    #     # Generate all possible combinations of artist names
    #     for r in range(1, len(artist_names) +  1):
    #         for combination in combinations(artist_names, r):

    #             filename = f"{', '.join(combination)} - {spotify_link_info['track_name']}".replace("/", "")
    #             _filename = filename
    #             filename = filename + f"-{music_quality['quality']}" if spotdl == False else filename

    #             dir = f"{SpotifyDownloader.download_directory}/{filename}"
    #             file_path = f"{dir}.{music_quality['format']}"
    #             is_local = os.path.isfile(file_path)

    #             if is_local == True:
    #                 break
    #         if is_local == True:
    #             break
        
    #     icon_name = f"{spotify_link_info['track_name']} - {spotify_link_info['artist_name']}.jpeg".replace("/"," ")
    #     icon_path = os.path.join(SpotifyDownloader.download_icon_directory, icon_name)
        
    #     if not is_local:
    #         filename = f"{spotify_link_info['artist_name']} - {spotify_link_info['track_name']}".replace("/","")
    #         _filename = filename
    #         filename = filename + f"-{music_quality['quality']}" if spotdl == False else filename
            
    #         dir = f"{SpotifyDownloader.download_directory}/{filename}"
    #         file_path = f"{dir}.{music_quality['format']}"
        
    #     await db.add_or_increment_song(_filename)
        
    #     file_info = {
    #         "file_name": filename,
    #         "file_path": file_path,
    #         "icon_path": icon_path,
    #         "is_local": is_local,
    #         "video_url": spotify_link_info['youtube_link']
    #     }  
        
    #     # Check if the file already exists
    #     if is_local:
    #         send_file_result = await SpotifyDownloader.send_local_file(client,event,file_info,spotify_link_info)
    #         return send_file_result
        
    #     elif is_local == False and spotdl == False:
    #         result,download_message = await SpotifyDownloader.download_YoutubeDL(event,file_info,music_quality)
            
    #         if os.path.isfile(file_path) and result == True:
                
    #             download_message = await download_message.edit("Downloading . . . .")
    #             flac_process_result, mp3_process_result = False, False
                
    #             if file_path.endswith('.flac'):
    #                 flac_process_result = await process_flac_music(event,file_info,spotify_link_info,download_message)
    #                 download_message = await download_message.edit("Downloading . . . . .")
                
    #             elif file_path.endswith('.mp3'):
    #                 mp3_process_result = await process_mp3_music(event,file_info,spotify_link_info,download_message)
    #                 download_message = await download_message.edit("Downloading . . . . .")

    #             await download_message.delete()
                
    #             send_file_result = await SpotifyDownloader.send_local_file(client,event,file_info,spotify_link_info)
    #             return True if (mp3_process_result or flac_process_result) and send_file_result else False
    #         else:
    #             return False
            
    #     elif is_local == False and spotdl == True:         
    #         result, initial_message = await SpotifyDownloader.download_SpotDL(event, music_quality, spotify_link_info)
    #         if result == False:
    #             result, initial_message = await SpotifyDownloader.download_SpotDL(event, music_quality, spotify_link_info, initial_message, audio_option="soundcloud")
    #             if result == False:
    #                 result, _ = await SpotifyDownloader.download_SpotDL(event, music_quality, spotify_link_info, initial_message, audio_option="youtube")
    #         if result == True and initial_message == True:
    #             if music_quality['format'] == "mp3":
    #                 await process_mp3_music(event,file_info,spotify_link_info)
    #             else:
    #                 await process_flac_music(event,file_info,spotify_link_info)
    #             return await SpotifyDownloader.send_local_file(client,event,file_info,spotify_link_info) if result else False
    #         else:
    #             return False
       
    @staticmethod
    async def download_playlist(client, event):
        user_id = event.sender_id

        message = "Downloading playlist tracks...\n\n"
        init_message = await event.respond(message)

        music_quality, downloading_core = await db.get_user_settings(user_id)

        total_link_info = await db.get_user_spotify_link_info(user_id)
        link_info = total_link_info['playlist_tracks']

        await db.set_file_processing_flag(user_id, 1)

        if downloading_core == "Auto":
            file_info_list = []
            track_messages = []

            for i in range(10):
                track_name = link_info[str(i+1)]['track_name']
                artist_name = link_info[str(i+1)]['artist_name']
                track_messages.append(f"⏳ {track_name} - {artist_name} :\n\t\t(Downloading)\n---------------------------------\n")

            message += ''.join(track_messages)
            await init_message.edit(message)
            message = ''

            async def extract_video_url(i):
                video_url = await SpotifyDownloader.extract_yt_video_info(link_info[str(i+1)])
                link_info[str(i+1)]['youtube_link'] = video_url
                return video_url
    
            async def download_icon(i):
                track_name = link_info[str(i+1)]['track_name']
                artist_name = link_info[str(i+1)]['artist_name']

                icon_name = f"{track_name} - {artist_name}.jpeg".replace("/", " ")
                icon_path = os.path.join(SpotifyDownloader.download_icon_directory, icon_name)

                if not os.path.isfile(icon_path):
                    try:
                        response = requests.get(link_info[str(i+1)]["image_url"])
                        if response.status_code == 200:
                            img = Image.open(BytesIO(response.content))
                            img.save(icon_path)
                    except Exception as e:
                        print(f"Failed to download or save track image: {e}")

                return icon_path

            async def process_track(i, icon_path, video_url):

                track_name = link_info[str(i+1)]['track_name']
                artist_name = link_info[str(i+1)]['artist_name']

                if video_url:
                    file_path, filename, is_local = SpotifyDownloader._determine_file_path(link_info[str(i+1)], music_quality, spotdl=False)
                else:
                    file_path, filename, is_local = SpotifyDownloader._determine_file_path(link_info[str(i+1)], music_quality, spotdl=True)

                file_info = {
                    "file_name": filename,
                    "file_path": file_path,
                    "icon_path": icon_path,
                    "is_local": is_local,
                    "video_url": video_url
                }

                file_info_list.append(file_info)
                print(file_info_list)
                await db.add_or_increment_song(track_name)
                if not is_local:
                    if video_url:
                        result, _ = await SpotifyDownloader.download_YoutubeDL(event, file_info, music_quality, playlist=True)
                        if os.path.isfile(file_path) and result:
                            if file_path.endswith('.flac'):
                                await process_flac_music(event, file_info, spotify_link_info=link_info[str(i+1)])
                            elif file_path.endswith('.mp3'):
                                await process_mp3_music(event, file_info, spotify_link_info=link_info[str(i+1)])
                            return f"✅ {track_name} - {artist_name} : \n\t\t(Downloaded)\n---------------------------------\n"
                        else:
                            return f"❌ {track_name} - {artist_name} :\n\t\t(Download Failed)\n---------------------------------\n"
                    else:
                        result, initial_message = await SpotifyDownloader.download_SpotDL(event, music_quality, link_info[str(i+1)], True)
                        if result == False:
                            result, initial_message = await SpotifyDownloader.download_SpotDL(event, music_quality, link_info[str(i+1)], True, initial_message, audio_option="soundcloud")
                            if result == False:
                                result, _ = await SpotifyDownloader.download_SpotDL(event, music_quality, link_info[str(i+1)], True, initial_message, audio_option="youtube")
                        if result == True and initial_message == True:
                            if music_quality['format'] == "mp3":
                                await process_mp3_music(event, file_info, link_info[str(i+1)])
                            else:
                                await process_flac_music(event, file_info, link_info[str(i+1)])
                            return f"✅ {track_name} - {artist_name} : \n\t\t(Downloaded)\n---------------------------------\n"
                        else:
                            return f"❌ {track_name} - {artist_name} :\n\t\t(Download Failed)\n---------------------------------\n"
                else:
                    return f"✅ {track_name} - {artist_name} :\n\t\t(Found in DB)\n---------------------------------\n"

        video_urls = await asyncio.gather(*[extract_video_url(i) for i in range(10)])
        print(video_urls)
        icon_paths = await asyncio.gather(*[download_icon(i) for i in range(10)])
        print(icon_paths)
        track_messages = await asyncio.gather(*[process_track(i, icon_paths[i], video_urls[i]) for i in range(10)])
        message += ''.join(track_messages)
        message += "\nDownload process completed. Starting the upload process..."
        await init_message.edit(message)

        upload_status_message = await event.reply("Uploading tracks... Please wait.")

        async def upload_track(j):
            await SpotifyDownloader.send_local_file(client, event, file_info_list[j], link_info[str(j+1)], playlist=True)

        await asyncio.gather(*[upload_track(j) for j in range(10)])

        await init_message.delete()
        await upload_status_message.delete()
        await event.respond("Top-10 Has finished. :)\nThank You for using @Spotify_YT_Downloader_Bot\n\nOur bot is OpenSource:\nGITHUB: [GITHUB LINK](https://github.com/AdibNikjou/telegram_spotify_downloader)")
    
    # @staticmethod
    # async def download_playlist(client, event):
    #     user_id = event.sender_id
        
    #     message = "Downloading playlist tracks...\n\n"
    #     init_message = await event.respond(message)
        
    #     music_quality, downloading_core = await db.get_user_settings(user_id)

    #     total_link_info = await db.get_user_spotify_link_info(user_id)
    #     link_info = total_link_info['playlist_tracks']
        
    #     await db.set_file_processing_flag(user_id, 1)
        
    #     if downloading_core == "Auto":
    #         file_info_list = []
    #         track_messages = []
            
    #         for i in range(10):
    #             track_name = link_info[str(i+1)]['track_name']
    #             artist_name = link_info[str(i+1)]['artist_name']
    #             track_messages.append(f"⏳ {track_name} - {artist_name} :\n\t\t(Downloading)\n---------------------------------\n")
            
    #         message += ''.join(track_messages)
    #         await init_message.edit(message)
    #         message = ''
            
    #         async def process_track(i):
    #             video_url = await SpotifyDownloader.extract_yt_video_info(link_info[str(i+1)])
    #             link_info[str(i+1)]['youtube_link'] = video_url
                
    #             track_name = link_info[str(i+1)]['track_name']
    #             artist_name = link_info[str(i+1)]['artist_name']
                
    #             icon_name = f"{track_name} - {artist_name}.jpeg".replace("/", " ")
    #             icon_path = os.path.join(SpotifyDownloader.download_icon_directory, icon_name)
                
    #             if not os.path.isfile(icon_path):
    #                 try:
    #                     response = requests.get(link_info[str(i+1)]["image_url"])
    #                     if response.status_code == 200:
    #                         img = Image.open(BytesIO(response.content))
    #                         img.save(icon_path)
    #                 except Exception as e:
    #                     print(f"Failed to download or save track image: {e}")
                        
    #             if link_info[str(i+1)]['youtube_link']:

    #                 file_path, filename, is_local = SpotifyDownloader._determine_file_path(link_info[str(i+1)], music_quality, spotdl)

    #                 file_info = {
    #                     "file_name": filename,
    #                     "file_path": file_path,
    #                     "icon_path": icon_path,
    #                     "is_local": is_local,
    #                     "video_url": link_info[str(i+1)].get('youtube_link')
    #                 }

    #                 file_info_list.append(file_info)
                    
    #                 await db.add_or_increment_song(track_name)
    #                 if not is_local:
    #                     result, _ = await SpotifyDownloader.download_YoutubeDL(event, file_info, music_quality, playlist=True)
    #                     if os.path.isfile(file_path) and result:
    #                         if file_path.endswith('.flac'):
    #                             await process_flac_music(event, file_info, spotify_link_info=link_info[str(i+1)])
    #                         elif file_path.endswith('.mp3'):
    #                             await process_mp3_music(event, file_info, spotify_link_info=link_info[str(i+1)])
    #                         return f"✅ {track_name} - {artist_name} : \n\t\t(Downloaded)\n---------------------------------\n"
    #                     else:
    #                         return f"❌ {track_name} - {artist_name} :\n\t\t(Download Failed)\n---------------------------------\n"
    #                 else:
    #                     return f"✅ {track_name} - {artist_name} :\n\t\t(Found in DB)\n---------------------------------\n"
    #             else:
                    
    #                 file_path, filename, is_local = SpotifyDownloader._determine_file_path(link_info[str(i+1)], music_quality, spotdl=True)

    #                 file_info = {
    #                     "file_name": filename,
    #                     "file_path": file_path,
    #                     "icon_path": icon_path,
    #                     "is_local": is_local,
    #                     "video_url": link_info[str(i+1)].get('youtube_link')
    #                 }

    #                 file_info_list.append(file_info)
                    
    #                 await db.add_or_increment_song(track_name)
    #                 if not is_local:
    #                     result, initial_message = await SpotifyDownloader.download_SpotDL(event, music_quality, link_info[str(i+1)], True)
    #                     if result == False:
    #                         result, initial_message = await SpotifyDownloader.download_SpotDL(event, music_quality, link_info[str(i+1)], True, initial_message, audio_option="soundcloud")
    #                         if result == False:
    #                             result, _ = await SpotifyDownloader.download_SpotDL(event, music_quality, link_info[str(i+1)], True, initial_message, audio_option="youtube")
    #                     if result == True and initial_message == True:
    #                         if music_quality['format'] == "mp3":
    #                             await process_mp3_music(event,file_info,link_info[str(i+1)])
    #                         else:
    #                             await process_flac_music(event,file_info,link_info[str(i+1)])
    #                         return f"✅ {track_name} - {artist_name} : \n\t\t(Downloaded)\n---------------------------------\n"
    #                     else:
    #                         return f"❌ {track_name} - {artist_name} :\n\t\t(Download Failed)\n---------------------------------\n"
    #                 else:
    #                     return f"✅ {track_name} - {artist_name} :\n\t\t(Found in DB)\n---------------------------------\n"
                    
    #     track_messages = await asyncio.gather(*[process_track(i) for i in range(10)])
    #     message += ''.join(track_messages)
    #     message += "\nDownload process completed. Starting the upload process..."
    #     await init_message.edit(message)
        
    #     upload_status_message = await event.reply("Uploading tracks... Please wait.")
        
    #     async def upload_track(j):
    #         await SpotifyDownloader.send_local_file(client, event, file_info_list[j], link_info[str(j+1)], playlist=True)
        
    #     await asyncio.gather(*[upload_track(j) for j in range(10)])
        
    #     await init_message.delete()
    #     await upload_status_message.delete()
    #     await event.respond("Top-10 Has finished. :)\nThank You for using @Spotify_YT_Downloader_Bot\n\nOuR Bot is OpenSource ;D\nGITHUB: [GITHUB LINK](https://github.com/AdibNikjou/telegram_spotify_downloader)")
                
    @staticmethod
    async def search_spotify_based_on_user_input(event, query, limit=50):
        results = SpotifyDownloader.spotify_account.search(q=query, limit=limit)
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
            artist = SpotifyDownloader.spotify_account.artist(artist_id)
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
        song = SpotifyDownloader.genius.search_song(f""" "{spotify_link_info['track_name']}"+"{spotify_link_info['artist_name']}" """)
        if song:
            await waiting_message.delete()
            lyrics = song.lyrics

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
                icon_path = os.path.join(SpotifyDownloader.download_icon_directory, icon_name)

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
        except Exception:
            await event.reply("An error occurred while processing your request. Please try again later.")
