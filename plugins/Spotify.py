from dotenv import load_dotenv
import os, spotipy, requests, asyncio, re
from spotipy.oauth2 import SpotifyClientCredentials
from PIL import Image
from io import BytesIO
from yt_dlp import YoutubeDL
from mutagen.flac import FLAC ,Picture
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TORY, TYER, TXXX, APIC
from mutagen import File
from telethon.tl.custom import Button
from database import db

class Spotify_Downloader():

    @classmethod
    def _load_dotenv_and_create_folders(cls):
        try:
            load_dotenv('config.env')
            cls.SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
            cls.SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
        except FileNotFoundError:
            print("Failed to Load .env variables")
        
        # Create a directory for the download
        cls.download_directory = "music_repository"
        if not os.path.isdir(cls.download_directory):
            os.makedirs(cls.download_directory, exist_ok=True)
            
        cls.download_icon_directory = "icon_repository"
        if not os.path.isdir(cls.download_icon_directory):
            os.makedirs(cls.download_icon_directory, exist_ok=True)

    @classmethod
    def initialize(cls):
        cls._load_dotenv_and_create_folders()
        cls.MAXIMUM_DOWNLOAD_SIZE_MB = 50
        cls.Spotify_info = None
        cls.is_file_processing = False
        cls.spotify_account = spotipy.Spotify(client_credentials_manager=
                SpotifyClientCredentials(client_id=cls.SPOTIFY_CLIENT_ID,
                                         client_secret=cls.SPOTIFY_CLIENT_SECRET))
             
    @staticmethod
    def is_spotify_link(url):
        pattern = r'https?://open\.spotify\.com/.*'
        return re.match(pattern, url) is not None
    
    @staticmethod
    def sanitize_query(query):
        # Remove non-alphanumeric characters and spaces
        sanitized_query = re.sub(r'\W+', ' ', query)
        # Trim leading and trailing spaces
        sanitized_query = sanitized_query.strip()
        return sanitized_query
    
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
    def extract_data_from_spotify_link(spotify_url) -> dict:
        
        link_info = {}
        if Spotify_Downloader.identify_spotify_link_type(spotify_url) == "track":
            
            track_info = Spotify_Downloader.spotify_account.track(spotify_url)
            
            link_info = {
                'type': "track",
                'track_name': track_info['name'],
                'artist_name': ', '.join([artist['name'] for artist in track_info['artists']]),
                'artist_url': track_info['artists'][0]['external_urls']['spotify'],
                'album_name': track_info['album']['name'],
                'album_url': track_info['album']['external_urls']['spotify'],
                'release_year': track_info['album']['release_date'].split('-')[0],
                'image_url': track_info['album']['images'][0]['url'],
                'track_id': track_info['id'],
                'isrc': track_info['external_ids']['isrc'],
                'track_url': spotify_url,
                'youtube_link': track_info.get('external_urls', {}).get('youtube', None)
            }
            
        else:
            link_info = {
                'type': None,
                'track_name': None,
                'artist_name': None,
                'artist_url': None,
                'album_name': None,
                'album_url': None,
                'release_year': None,
                'image_url': None,
                'track_id': None,
                'isrc': None,
                'track_url': None,
                'youtube_link': None
            }
            
        return link_info
        
    @staticmethod       
    def extract_yt_video_info(spotify_link_info) -> tuple:
        
        if spotify_link_info == None:
            return None
        
        # If a YouTube link is found, extract the video ID and other details
        if spotify_link_info["youtube_link"]:
            video_url = spotify_link_info["youtube_link"]
            
        else:
            query = f""""{spotify_link_info['track_name']}" "{spotify_link_info['artist_name']}" "{spotify_link_info['album_name']}" {spotify_link_info['release_year']}"""
            
            ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'ytsearch': query,
            'skip_download': True
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                try:
                    search_results = ydl.extract_info(f'ytsearch:{query}', download=False)
                    video_url = search_results['entries'][0]['webpage_url']
                except:
                    Spotify_Downloader.is_file_processing = False
                    video_url = None

        return video_url
        
        
    @staticmethod  
    async def download_and_send_spotify_info(client, event, link_info:dict = None) -> bool :

        if Spotify_Downloader.Spotify_info != None:
            await Spotify_Downloader.Spotify_info.edit(buttons=None)
            
        music_quality, donwloading_core = db.get_user_settings(event.sender_id)
        spotdl = True if donwloading_core == "SpotDL" else False
        
        if not link_info["type"] == "track":
            await event.respond("The Provided Link is not a track.")
            return False
             
        filename = f"{link_info['artist_name']} - {link_info['track_name']}".replace("/","")
        filename = filename + f"-{music_quality['quality']}" if spotdl == False else filename
        
        icon_name = f"{link_info['track_name']} - {link_info['artist_name']}.jpeg".replace("/"," ")
        icon_path = os.path.join(Spotify_Downloader.download_icon_directory, icon_name)
        
        is_local = os.path.isfile(f"{Spotify_Downloader.download_directory}/{filename}.{music_quality['format']}")
 
        if not os.path.isfile(icon_path):
            response = requests.get(link_info["image_url"])
            img = Image.open(BytesIO(response.content))
            img.save(icon_path)
        
        SpotifyInfoButtons = [
            [Button.inline("Download  30s Preview", data=b"@music_info_preview")],
            [Button.inline("Download Track", data=b"@music")],
            [Button.inline("Music Info", data=b"@music_info")],
            [Button.inline("Artist Info", data=b"@artist_info")],
            [Button.inline("Listen On Spotify", data=b"@music_info_spotify"),
             Button.inline("Listen On Youtube", data=b"@music_info_youtube")],
            [Button.inline("Cancel", data=b"CANCEL")]
        ]

        try :    
            Spotify_Downloader.Spotify_info = await client.send_file(event.chat_id,icon_path,
            caption = f"""
🎧  Title : [{link_info["track_name"]}]({link_info["track_url"]})
🎤  Artist : [{link_info["artist_name"]}]({link_info["artist_url"]})
💽  Album : [{link_info["album_name"]}]({link_info["album_url"]})
🗓  Release Year: {link_info["release_year"]}
❗️ Is Local: {is_local}
🌐 ISRC: {link_info["isrc"]}

Image URL: [Click here]({link_info["image_url"]})
Track id: {link_info["track_id"]}
""",buttons=SpotifyInfoButtons)
            
            return True
        except:
            return False
        
    @staticmethod
    async def send_localfile(client,event,file_info,spotify_link_info) -> bool:

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
-->[Listen On Youtube Music]({video_url})
            """,
                        supports_streaming=True,  # This flag enables streaming for compatible formats
                        force_document=False,  # This flag sends the file as a document or not
                        thumb=icon_path,
                        allow_cache=True
                    )
        except:
            await event.respond("SomeThing Went Wrong. Try Using YoutubeDL.")
            
        await is_local_message.delete() if was_Local else None
        await upload_message.delete()
        
        Spotify_Downloader.is_file_processing = False
        return True
    
    
    @staticmethod
    async def download_SpotDL(event,music_quality,spotify_link_info) -> bool:

            command = f'python3 -m spotdl --format {music_quality["format"]} --audio piped --output "{Spotify_Downloader.download_directory}" "{spotify_link_info["track_url"]}"'

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
                Spotify_Downloader.is_file_processing = False
                return False
            
            # Send an initial message to the user with a progress bar
            initial_message = await event.reply("Downloading...\n")
            
            # Function to send updates to the user
            async def send_updates(process, message):
                
                while True:
                    # Read a line from stdout
                    line = await process.stdout.readline()
                    
                    if not line:
                        await message.delete()
                        break
                    line = line.decode().strip()
                    
                    # Check if the line is not empty before editing
                    if line:
                        await message.edit(f"Downloading...\n{line}")
            
            # Start sending updates and wait for it to complete
            await send_updates(process, initial_message)
            
            # Wait for the process to finish
            await process.wait()
            
            return True
    
    @staticmethod
    async def download_YoutubeDL(event,file_info,music_quality):
        
        video_url = file_info['video_url']
        filename = file_info['file_name']
        
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
                Spotify_Downloader.is_file_processing = False
                return False  # Skip the download

        download_message = await event.respond("Downloading .")
        
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
            Spotify_Downloader.is_file_processing = False
            return False
        
        return True,download_message
    
    @staticmethod
    async def process_flac_music(file_info,spotify_link_info,download_message) -> bool:

        file_path = file_info['file_path']
        icon_path = file_info['icon_path']
        try:
            PreProcessAudio = FLAC(file_path)

            # Set the standard FLAC metadata fields
            PreProcessAudio['TITLE'] = spotify_link_info["track_name"]
            PreProcessAudio['ARTIST'] = spotify_link_info["artist_name"]
            PreProcessAudio['ALBUM'] = spotify_link_info["album_name"]
            PreProcessAudio['DATE'] = spotify_link_info['release_year']
            PreProcessAudio['ORIGINALYEAR'] = spotify_link_info['release_year']
            PreProcessAudio['YEAR_OF_RELEASE'] = spotify_link_info['release_year']
            PreProcessAudio['ISRC'] = spotify_link_info['isrc']
            PreProcessAudio.save()
            
            audio = File(file_path)
            
            await asyncio.sleep(0.3)
            download_message = await download_message.edit("Downloading . . .")
            
            image = Picture()
            with open(icon_path, 'rb') as image_file:
                image.data = image_file.read()
                
            image.type = 3
            image.mime = 'image/jpeg'  # Or 'image/png' depending on your image type
            image.width = 500  # Replace with your image's width
            image.height = 500  # Replace with your image's height
            image.depth = 24  # Color depth, change if necessary

            audio.clear_pictures()
            audio.add_picture(image)
            audio.save()
            
            return True
        except:
            print("Failed to process")
            Spotify_Downloader.is_file_processing = False
            return False

    @staticmethod
    async def process_mp3_music(file_info,spotify_link_info,download_message) -> bool:
        
        file_path = file_info['file_path']
        icon_path = file_info['icon_path']
        
        try:
            # Switch to ID3 mode to add frames
            PreProcessAudio = ID3(file_path)
            
            # Set the standard MP3 metadata fields
            PreProcessAudio.add(TIT2(encoding=3, text=spotify_link_info["track_name"]))
            PreProcessAudio.add(TPE1(encoding=3, text=spotify_link_info["artist_name"]))
            PreProcessAudio.add(TALB(encoding=3, text=spotify_link_info["album_name"]))
            PreProcessAudio.add(TDRC(encoding=3, text=spotify_link_info['release_year']))
            PreProcessAudio.add(TORY(encoding=3, text=spotify_link_info['release_year']))
            PreProcessAudio.add(TYER(encoding=3, text=spotify_link_info['release_year']))
            PreProcessAudio.add(TXXX(encoding=3, desc='ISRC', text=spotify_link_info['isrc']))
            # Save the metadata
            PreProcessAudio.save()
            
            await asyncio.sleep(0.3)
            download_message = await download_message.edit("Downloading . . .")
            
            # Load the MP3 file
            audio = ID3(file_path)
            
            # Add the image to the MP3 file
            with open(icon_path, 'rb') as image_file:
                audio.add(
                    APIC(
                        encoding=3,  #   3 is for utf-8
                        mime='image/jpeg',  # or 'image/png' if your image is a PNG
                        type=3,  #   3 is for the cover image
                        desc=u'Cover',
                        data=image_file.read()
                    )
                )

            # Save the metadata
            audio.save()
            return True
        except:
            print("Failed to process")
            Spotify_Downloader.is_file_processing = False
            return False
            
    @staticmethod
    async def download_spotify_file_and_send(client,event,spotify_link_info) -> bool:
           
        music_quality, donwloading_core = db.get_user_settings(event.sender_id)
        spotdl = True if donwloading_core == "SpotDL" else False
        
        if Spotify_Downloader.is_file_processing == True:
            await event.respond("Sorry,There is already a file being processed for you.")
            return True
        
        Spotify_Downloader.is_file_processing = True
    
        video_url = Spotify_Downloader.extract_yt_video_info(spotify_link_info)
        
        if video_url == None:
            Spotify_Downloader.is_file_processing = False
            return True
             
        filename = f"{spotify_link_info['artist_name']} - {spotify_link_info['track_name']}".replace("/","")
        filename = filename + f"-{music_quality['quality']}" if spotdl == False else filename
        
        icon_name = f"{spotify_link_info['track_name']} - {spotify_link_info['artist_name']}.jpeg".replace("/"," ")
        icon_path = os.path.join(Spotify_Downloader.download_icon_directory, icon_name)
        
        dir = f"{Spotify_Downloader.download_directory}/{filename}"
        file_path = f"{dir}.{music_quality['format']}"
        is_local = os.path.isfile(f"{file_path}")

        file_info = {
            "file_name": filename,
            "file_path": file_path,
            "icon_path": icon_path,
            "is_local": is_local,
            "video_url": video_url
        }  
        
        # Check if the file already exists
        if is_local:
            send_file_result = await Spotify_Downloader.send_localfile(client,event,file_info,spotify_link_info)
            return send_file_result
        
        elif is_local == False and spotdl == False:
            result,download_message = await Spotify_Downloader.download_YoutubeDL(event,file_info,music_quality)
            
            if os.path.isfile(file_path) and result == True:
                
                await asyncio.sleep(0.3)
                download_message = await download_message.edit("Downloading . .")
                flac_process_result, mp3_process_result = False, False
                
                if file_path.endswith('.flac'):
                    flac_process_result = await Spotify_Downloader.process_flac_music(file_info,spotify_link_info,download_message)
                    
                    await asyncio.sleep(0.3)
                    download_message = await download_message.edit("Downloading . . . .")
                
                elif file_path.endswith('.mp3'):
                    mp3_process_result = await Spotify_Downloader.process_mp3_music(file_info,spotify_link_info,download_message)
                    
                    await asyncio.sleep(0.3)
                    download_message = await download_message.edit("Downloading . . . .")

                await download_message.delete()
                
                send_file_result = await Spotify_Downloader.send_localfile(client,event,file_info,spotify_link_info)
                return True if (mp3_process_result or flac_process_result) and send_file_result else False
            else:
                return False
            
        elif is_local == False and spotdl == True:         
            result = await Spotify_Downloader.download_SpotDL(event,music_quality,spotify_link_info)
            return await Spotify_Downloader.send_localfile(client,event,file_info,spotify_link_info) if result else False
            
    @staticmethod
    def search_spotify_based_on_user_input(query, limit=10):
        
        results = Spotify_Downloader.spotify_account.search(q=query, limit=limit)
        song_dict = {}
        
        for i, t in enumerate(results['tracks']['items']):
            artists = ', '.join([a['name'] for a in t['artists']])
            # Extract the Spotify URL from the external_urls field
            spotify_link = t['external_urls']['spotify']
            song_dict[i] = {
                'track_name': t['name'],  
                'artist': artists,
                'release_year': t['album']['release_date'][:4],
                'spotify_link': spotify_link  # Include the Spotify link in the dictionary
            }
        return song_dict

