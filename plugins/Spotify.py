from dotenv import load_dotenv
import os, subprocess, io
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import requests
from PIL import Image
from io import BytesIO
from yt_dlp import YoutubeDL
from mutagen.flac import FLAC 

class Spotify_Downloader():

    try:
        load_dotenv('config.env')
        SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
        SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
        YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    except:
        print("Failed to Load .env variables")
    
    # Create Spotify to get track info
    spotify_account = spotipy.Spotify(client_credentials_manager=
            SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

    # Create a directory for the download
    download_directory = "spotify_downloads"
    if not os.path.isdir(download_directory):
        os.makedirs(download_directory, exist_ok=True)
        
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
        
            search_query = f"{spotify_link_info['track_name']} {spotify_link_info['album_name']} {spotify_link_info['release_year']}"
            search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q={search_query}&key={Spotify_Downloader.YOUTUBE_API_KEY}"
            response = requests.get(search_url).json()
            
            # Extract the video ID of the first search result
            video_id = response['items'][0]['id']['videoId']

            # Replace with your actual video URL
            video_url = f'https://www.youtube.com/watch?v={video_id}'
            
            ytb_opts = {"quiet": True}
            
            with YoutubeDL(ytb_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=False)
                # filename = ydl.prepare_filename(info_dict)
                video_title = info_dict.get('title', None)
                video_ext = info_dict.get('ext', None)
                
            filename = f"{spotify_link_info['track_name']} - {spotify_link_info['artist_name']}"
            
            return video_id,video_url,video_title,video_ext,filename
        
        
    @staticmethod  
    async def download_and_send_spotify_info(client,event,link_info:dict) -> tuple :
        download_icon_directory = "icon_repository"
        
        if link_info["type"] == "track":
            video_id,video_url,video_title,video_ext,filename = Spotify_Downloader.extract_yt_video_info(link_info)
            is_local = os.path.isfile(f"{Spotify_Downloader.download_directory}/{filename}.flac")
        else:
            pass
        
        if not os.path.isdir(download_icon_directory):
            os.makedirs(download_icon_directory, exist_ok=True)
            
        if not os.path.isfile(os.path.join(download_icon_directory, f"{video_id}.jpg")):
            response = requests.get(link_info["image_url"])
            img = Image.open(BytesIO(response.content))
            img.save(os.path.join(download_icon_directory, f"{video_id}.jpg"))
        
        try :    
            await client.send_file(event.chat_id,
            os.path.join(download_icon_directory, f"{video_id}.jpg"),
            caption = f"""
🎧  Title : [{link_info["track_name"]}]({link_info["track_url"]})
🎤  Artist : [{link_info["artist_name"]}]({link_info["artist_url"]})
💽  Album : [{link_info["album_name"]}]({link_info["album_url"]})
🗓  Release Year: {link_info["release_year"]}
❗️ Is Local: {is_local}
🌐 ISRC: {link_info["isrc"]}

Image URL: [Click here]({link_info["image_url"]})
Track id: {link_info["track_id"]}
""",parse_mode='Markdown')
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
        
        # Check if the file already exists
        if is_local:

            is_local_message = await event.respond(f"Found in DataBase. Result in Sending Faster :)")
            
            file_path = f"{Spotify_Downloader.download_directory}/{filename}.flac"
            
            async with client.action(event.chat_id, 'document'):
                await client.send_file(event.chat_id, file_path,   
                        caption = f"""
💽 {spotify_link_info["track_name"]} - {spotify_link_info["artist_name"]}

-->[Listen On Spotify]({spotify_link_info["track_url"]})
-->[Listen On Youtube Music]({video_url})
        """,force_document=False,voice_note=True)
            
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

            file_path = f"{Spotify_Downloader.download_directory}/{filename}.flac"
            
            if os.path.isfile(file_path):
                
                audio = FLAC(file_path)
                audio["TITLE"] = spotify_link_info["track_name"]
                audio["ORIGINALYEAR"] = spotify_link_info['release_year']
                audio["YEAR_OF_RELEASE"] = spotify_link_info['release_year']
                audio["WEBSITE"] = "https://t.me/spotify_yt_downloader_bot"
                audio["GEEK_SCORE"] = "9"
                audio["ARTIST"] = spotify_link_info["artist_name"]                                                                    
                audio["ALBUM"] = spotify_link_info["album_name"]
                audio["DATE"] = spotify_link_info['release_year']
                audio["ISRC"] = spotify_link_info['isrc']
                audio.save()
                
                async with client.action(event.chat_id, 'document'):
                    await client.send_file(event.chat_id, file_path,
                        caption = f"""
💽 {spotify_link_info["track_name"]} - {spotify_link_info["artist_name"]}

-->[Listen On Spotify]({spotify_link_info["track_url"]})
-->[Listen On Youtube Music]({video_url})
        """,force_document=False,voice_note=True)
                    
                return True
            else:
                return False

