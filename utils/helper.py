import asyncio, re
from mutagen import File
from mutagen.flac import FLAC ,Picture
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TORY, TYER, TXXX, APIC
from utils.database import db

async def process_flac_music(event,file_info,spotify_link_info,download_message = None) -> bool:

    user_id = event.sender_id
    
    file_path = file_info['file_path']
    icon_path = file_info['icon_path']
    try:
        PreProcessAudio = FLAC(file_path)

        artist_names = spotify_link_info["artist_name"].split(', ')
        artist_names_formatted = ', '.join(artist_names)

        if isinstance(spotify_link_info["track_name"], str) and isinstance(artist_names_formatted, str):
            PreProcessAudio['TITLE'] = spotify_link_info["track_name"] + " - " + artist_names_formatted
        PreProcessAudio['ARTIST'] = "@Spotify_YT_Downloader_BOT"
        PreProcessAudio['ALBUM'] = spotify_link_info["album_name"]
        PreProcessAudio['DATE'] = spotify_link_info['release_year']
        PreProcessAudio['ORIGINALYEAR'] = spotify_link_info['release_year']
        PreProcessAudio['YEAR_OF_RELEASE'] = spotify_link_info['release_year']
        PreProcessAudio['ISRC'] = spotify_link_info['isrc']
        PreProcessAudio.save()
        
        audio = File(file_path)
        
        await asyncio.sleep(0.3)
        download_message = await download_message.edit("Downloading . . .") if download_message != None else None
        
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
    except Exception as e:
        print(f"Failed to process: {str(e)}")
        await db.set_file_processing_flag(user_id,0)
        return False
    
    
async def process_mp3_music(event,file_info,spotify_link_info,download_message = None) -> bool:
    
    user_id = event.sender_id
    file_path = file_info['file_path']
    icon_path = file_info['icon_path']
    
    try:
        # Switch to ID3 mode to add frames
        PreProcessAudio = ID3(file_path)
        
        artist_names = spotify_link_info["artist_name"].split(', ')
        artist_names_formatted = ', '.join(artist_names)

        if isinstance(spotify_link_info["track_name"], str) and isinstance(artist_names_formatted, str):
            PreProcessAudio.add(TIT2(encoding=3, text=spotify_link_info["track_name"] + " - " + artist_names_formatted))                 
        PreProcessAudio.add(TPE1(encoding=3, text="@Spotify_YT_Downloader_BOT"))
        PreProcessAudio.add(TALB(encoding=3, text=spotify_link_info["album_name"]))
        PreProcessAudio.add(TDRC(encoding=3, text=spotify_link_info['release_year']))
        PreProcessAudio.add(TORY(encoding=3, text=spotify_link_info['release_year']))
        PreProcessAudio.add(TYER(encoding=3, text=spotify_link_info['release_year']))
        PreProcessAudio.add(TXXX(encoding=3, desc='ISRC', text=spotify_link_info['isrc']))
        # Save the metadata
        PreProcessAudio.save()
        
        await asyncio.sleep(0.3)
        download_message = await download_message.edit("Downloading . . .") if download_message != None else None
        
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
    except Exception as e:
        print(f"Failed to process: {str(e)}")
        await db.set_file_processing_flag(user_id,0)
        return False
    
def sanitize_query(query):
    # Remove non-alphanumeric characters and spaces
    sanitized_query = re.sub(r'\W+', ' ', query)
    # Trim leading and trailing spaces
    sanitized_query = sanitized_query.strip()
    return sanitized_query