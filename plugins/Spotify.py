from dotenv import load_dotenv
import os, spotipy, requests
from spotipy.oauth2 import SpotifyClientCredentials
from PIL import Image
from io import BytesIO
from yt_dlp import YoutubeDL
from mutagen.flac import FLAC ,Picture
from mutagen.id3 import PictureType
from mutagen import File

class Spotify_Downloader():

    @classmethod
    def _load_dotenv_and_create_folders(cls):
        try:
            load_dotenv('config.env')
            cls.SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
            cls.SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
            cls.YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
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
        cls.spotify_account = spotipy.Spotify(client_credentials_manager=
                SpotifyClientCredentials(client_id=cls.SPOTIFY_CLIENT_ID,
                                         client_secret=cls.SPOTIFY_CLIENT_SECRET))
             
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
            link_info["type"] = "track"
            link_info["track_name"] = track_info['name']
            link_info["artist_name"] = track_info['artists'][0]['name']
            link_info["artist_url"] = track_info['artists'][0]['external_urls']['spotify']
            link_info["album_name"] = track_info['album']['name']
            link_info["album_url"] = track_info['album']['external_urls']['spotify']
            link_info["release_year"] = track_info['album']['release_date'].split('-')[0]
            link_info["image_url"] = track_info['album']['images'][0]['url']
            link_info["track_id"] = track_info['id']
            link_info["isrc"] = track_info['external_ids']['isrc']
            link_info["track_url"] = spotify_url
            
        return link_info

    
    @staticmethod       
    def extract_yt_video_info(spotify_link_info) -> tuple:

        query = f""""{spotify_link_info['track_name']}" "{spotify_link_info["album_name"]}" "{spotify_link_info["release_year"]}" """
        
        ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'ytsearch': query,
        'skip_download': True,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            try:
                search_results = ydl.extract_info(f'ytsearch:{query}', download=False)
                video_title = search_results['entries'][0]['title']
                video_ext = search_results['entries'][0]['ext']
                video_url = search_results['entries'][0]['webpage_url']
                video_id = search_results['entries'][0]['id']
            except:
                video_title = None
                video_ext = None
                video_url = None
                video_id = None
            
        filename = f"{spotify_link_info['track_name']} - {spotify_link_info['artist_name']}"
        
        return video_id,video_url,video_title,video_ext,filename
        
        
    @staticmethod  
    async def download_and_send_spotify_info(client,event,link_info:dict) -> tuple :
         
        if link_info["type"] == "track":
            video_id,video_url,video_title,video_ext,filename = Spotify_Downloader.extract_yt_video_info(link_info)
            is_local = os.path.isfile(f"{Spotify_Downloader.download_directory}/{filename}.flac")
        else:
            pass
        
        icon_name = f"{link_info['track_name']} - {link_info['artist_name']}.jpeg"
        icon_path = os.path.join(Spotify_Downloader.download_icon_directory, icon_name) 
        
        if not os.path.isfile(icon_path):
            response = requests.get(link_info["image_url"])
            img = Image.open(BytesIO(response.content))
            img.save(icon_path)
        
        try :    
            await client.send_file(event.chat_id,icon_path,
            caption = f"""
🎧  Title : [{link_info["track_name"]}]({link_info["track_url"]})
🎤  Artist : [{link_info["artist_name"]}]({link_info["artist_url"]})
💽  Album : [{link_info["album_name"]}]({link_info["album_url"]})
🗓  Release Year: {link_info["release_year"]}
❗️ Is Local: {is_local}
🌐 ISRC: {link_info["isrc"]}

Image URL: [Click here]({link_info["image_url"]})
Track id: {link_info["track_id"]}
""")
            return True, is_local,video_id, video_url, video_title, video_ext, filename
        except:
            return False, False, video_id, video_url, video_title, video_ext, filename
        

    @staticmethod
    async def download_spotify_file_and_send(client,event,info_tuple,spotify_link_info) -> bool:

        is_local = info_tuple[1]
        video_id = info_tuple[2]
        video_url = info_tuple[3]
        video_title = info_tuple[4]
        video_ext = info_tuple[5]
        filename = info_tuple[6]
        
        icon_name = f"{spotify_link_info['track_name']} - {spotify_link_info['artist_name']}.jpeg"
        icon_path = os.path.join(Spotify_Downloader.download_icon_directory, icon_name)
        
        file_path = f"{Spotify_Downloader.download_directory}/{filename}.flac"
        
        # Check if the file already exists
        if is_local:

            is_local_message = await event.respond(f"Found in DataBase. Result in Sending Faster :)")
            
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
                        thumb=icon_path
                    )
            
            await is_local_message.delete()
            return True
        
        else:
            
            video_id,video_url,video_title,video_ext,filename = Spotify_Downloader.extract_yt_video_info(spotify_link_info)
            # Define the options for yt-dlp
            ydl_opts = {
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
                "postprocessors": [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'flac', 'preferredquality': '693'}],
            }

            try:
                # Run youtube-dl with the specified options and the video URL
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
            except Exception as ERR:
                await event.respond(f"Something Went Wrong,{str(ERR)}")
                return False

            if os.path.isfile(file_path):

                audio = FLAC(file_path)

                # Set the standard FLAC metadata fields
                audio['TITLE'] = spotify_link_info["track_name"]
                audio['ARTIST'] = spotify_link_info["artist_name"]
                audio['ALBUM'] = spotify_link_info["album_name"]
                audio['DATE'] = spotify_link_info['release_year']
                audio['ORIGINALYEAR'] = spotify_link_info['release_year']
                audio['YEAR_OF_RELEASE'] = spotify_link_info['release_year']
                audio['ISRC'] = spotify_link_info['isrc']
                audio.save()
                
                
                audi = File(file_path)
                
                image = Picture()
                with open(icon_path, 'rb') as image_file:
                    image.data = image_file.read()
                    
                image.type = 3
                image.mime = 'image/png'  # Or 'image/png' depending on your image type
                image.width = 500  # Replace with your image's width
                image.height = 500  # Replace with your image's height
                image.depth = 24  # Color depth, change if necessary

                audi.clear_pictures()
                audi.add_picture(image)
                audi.save()
                
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
                        thumb=icon_path
                    )
                    
                return True
            else:
                return False

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
