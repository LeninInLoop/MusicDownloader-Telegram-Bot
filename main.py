import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from plugins.Spotify import Spotify_Downloader
import asyncio

try:
    load_dotenv('config.env')
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
except:
    print("Failed to Load .env variables")

#------------------------------------------------------------------------------------------
#Call the initialize method to set up the Spotify Downloader

Spotify_Downloader.initialize()

#------------------------------------------------------------------------------------------
global spotify_link_info, info_tuple, search_result, song_dict, waiting_message
global music_quality

messages = {} # Dictionary to store message IDs

search_result = "None"

song_dict = None
waiting_message = None
spotify_link_info = None

music_quality = {"format": "mp3",
                "quality": 320
                }

#------------------------------------------------------------------------------------------
#### Start Messages:
start_message = """
I'm a dedicated Spotify Downloader, ready to turn your favorite tunes into downloadable tracks. 🎶🎵

Just a heads up, this service is meant for personal use only. Let's keep those downloaded tracks under wraps, shall we? 😉

So, buckle up and let's rock this music journey together! 🎧
"""

instruction_message = """
To begin using this service, please follow these steps:

1. Share the link to the Spotify song you wish to download.🔗
2. Await the confirmation message indicating that the download process has commenced.📣
3. Upon completion of the download, I will promptly send you the downloaded file.💾

UPDATE: You now have the option to search the Spotify database
by providing the song's title, lyrics, or any other pertinent details.
This feature significantly enhances the search functionality,
offering a more extensive and user-friendly experience.
"""

contact_creator_message = """Should you have any inquiries or require feedback, please do not hesitate to contact me. 🌐
>> @AdibNikjou"""

search_result_message = """🎵 The following are the top 10 search results that correspond to your query:
"""
#------------------------------------------------------------------------------------------
#### Buttons:
main_menu_buttons = [
    [Button.inline("Instructions", b"instructions"),Button.inline("Settings", b"setting")],
    [Button.inline("Contact Creator", b"contact_creator")]
    ]

back_button = Button.inline("<< Back To Main Menu", b"back")

setting_button = [
    [Button.inline("Quality", b"setting/quality")],
    [back_button]
    ]

back_button_to_setting = Button.inline("<< Back", b"setting/back")

quality_setting_buttons = [
    [Button.inline("flac", b"setting/quality/flac")],
    [Button.inline("mp3-320", b"setting/quality/mp3/320")],
    [Button.inline("mp3-128", b"setting/quality/mp3/128")],
    [back_button, back_button_to_setting],
]
#------------------------------------------------------------------------------------------------

with TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN) as client:

    @client.on(events.NewMessage(pattern='/start'))
    async def start(event):
        sender_name = event.sender.first_name
        
        message = await event.respond(f"""Hey {sender_name}!👋 \n{start_message}""", buttons=main_menu_buttons)
        messages[str(event.chat_id)] = message # Store the message ID

    @client.on(events.CallbackQuery)
    async def callback_query_handler(event):
        global waiting_message, spotify_link_info, info_tuple, music_quality
        
        if event.data == b"instructions":
            await client.edit_message(messages[str(event.chat_id)], instruction_message, buttons=back_button)
        elif event.data == b"contact_creator":
            await client.edit_message(messages[str(event.chat_id)], contact_creator_message, buttons=back_button )
        elif event.data == b"back":
            sender_name = event.sender.first_name
            await client.edit_message(messages[str(event.chat_id)],f"""Hey {sender_name}!👋\n {start_message}""",buttons=main_menu_buttons)
            
        elif event.data == b"setting" or event.data == b"setting/back":
            await client.edit_message(messages[str(event.chat_id)], "Settings :", buttons=setting_button)
            
        elif event.data == b"setting/quality":
            await client.edit_message(messages[str(event.chat_id)],
                    f"Your Quality Setting:\nFormat: {music_quality['format']}\nQuality: {music_quality['quality']}\n\nQualities Available :",
                    buttons=quality_setting_buttons)
            
        elif event.data == b"setting/quality/mp3/320":
            music_quality['format'] = "mp3"
            music_quality['quality'] = 320
            await client.edit_message(messages[str(event.chat_id)],
                    f"Quality successfuly changed. \nFormat: {music_quality['format']}\nQuality: {music_quality['quality']}",
                    buttons=quality_setting_buttons)

        elif event.data == b"setting/quality/mp3/128":
            music_quality['format'] = "mp3"
            music_quality['quality'] = 128
            await client.edit_message(messages[str(event.chat_id)],
                    f"Quality successfuly changed. \nFormat: {music_quality['format']}\nQuality: {music_quality['quality']}",
                    buttons=quality_setting_buttons)

        elif event.data == b"setting/quality/flac":
            music_quality["format"] = "flac"
            music_quality['quality'] = 693
            await client.edit_message(messages[str(event.chat_id)],
                    f"Quality successfuly changed. \nFormat: {music_quality['format']}\nQuality: {music_quality['quality']}",
                    buttons=quality_setting_buttons)

        elif event.data == b"CANCEL":
            await event.delete()
           
        elif event.data == b"@music_info_preview":
            pass
        
        elif event.data.startswith(b"@music"):
            send_file_result = await Spotify_Downloader.download_spotify_file_and_send(client,event,music_quality,spotify_link_info)
            
            if not send_file_result:
                await event.respond(f"Sorry, there was an error downloading the song")
                
            await waiting_message.delete()
            
            try:        
                if search_result != "None":
                    await search_result.delete()
                    search_result = "None"
            except:
                pass
            
        elif event.data == b"@music_info":
            pass
        elif event.data == b"@artist_info":
            pass
        elif event.data == b"@music_info_spotify":
            pass
        elif event.data == b"@music_info_youtube":
            pass 
            
        elif event.data.isdigit():
            spotify_link_to_download = None
            
            # The callback_data_str is just the index, so convert it to an integer
            song_index = int(event.data.decode('utf-8'))

            spotify_link_to_download = song_dict[song_index]['spotify_link']
            
            if spotify_link_to_download != None:
                
                waiting_message = await event.respond('⏳')
                
                spotify_link_info = Spotify_Downloader.extract_data_from_spotify_link(spotify_link_to_download)            
                send_info_result = await Spotify_Downloader.download_and_send_spotify_info(client,event,music_quality,spotify_link_info)
                
                if not send_info_result: #if getting info of the link failed
                    return await event.respond("Sorry, There was a problem processing your link, try again later.")

    @client.on(events.NewMessage)
    async def handle_message(event):
        global search_result, song_dict, info_tuple, spotify_link_info, waiting_message, music_quality
        
        # Check if the message is a Spotify URL
        if 'open.spotify.com' in event.message.text: 
            
            waiting_message = await event.respond('⏳')
                
            spotify_link_info = Spotify_Downloader.extract_data_from_spotify_link(str(event.message.text))            
            info_tuple = await Spotify_Downloader.download_and_send_spotify_info(client,event,music_quality,spotify_link_info)
            
            if not info_tuple[0]: #if getting info of the link failed
                return await event.respond("Sorry, There was a problem processing your request.")
            if not all(info_tuple):
                await waiting_message.delete()

        else:
            
            # Ignore messages that match the /start pattern
            if event.message.text.startswith('/start'):
                return
          
            if search_result != "None":
                await search_result.delete()
                search_result = "None"
                
            waiting_message_search = await event.respond('⏳')

            button_list = []
            song_dict = Spotify_Downloader.search_spotify_based_on_user_input(event.message.text)
            
            # Create a list of buttons for each song
            for idx, details in song_dict.items():
                button_text = f"🎧 {details['track_name']} - {details['artist']} 🎧 ({details['release_year']})"
                callback_query = f"{str(idx)}"
                button_list.append([Button.inline(button_text,data=callback_query)])
            
            try:
                cancel_button = [Button.inline("Cancel", b"CANCEL")]
                button_list.append(cancel_button)
                
                # Send the search result message with the buttons
                search_result = await event.respond(search_result_message, buttons=button_list)
                
            except Exception as Err:
                await event.respond(f"Sorry There Was an Error Processing Your Request: {str(Err)}")
                
            await asyncio.sleep(2)
            await waiting_message_search.delete()

    client.run_until_disconnected()
                    
#### Needs Optiization
# 1. in is_Local -> use rust or C , or a better algoritm
# 2. in finding the spotify link -> create a class named spotify, inside this class should be a proper filter for spotify link
# 3. object oriented
