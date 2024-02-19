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

messages = {} # Dictionary to store message IDs
search_result = "None"
song_dict = None

#------------------------------------------------------------------------------------------
#### Start Messages:
start_message = """
I'm a dedicated Spotify Downloader bot, ready to turn your favorite tunes into downloadable tracks. 🎶🎵

Just a heads up, this service is meant for personal use only. Let's keep those downloaded tracks under wraps, shall we? 😉

So, buckle up and let's rock this music journey together! 🎧
"""

instruction_message = """To get started, simply follow these steps:

1. Share the link to the Spotify song, album, or playlist you wish to download.🔗
2. Wait for the confirmation message that the download has begun.📣
3. Once the download is complete, I'll send you the downloaded file.💾"""

contact_creator_message = """Feel free to reach out to me anytime you have questions or feedback! 🌐
>> @AdibNikjou"""

search_result_message ="""🎵 Here are the top 10 search results that match your search query:
"""
#------------------------------------------------------------------------------------------
#### Buttons:
main_menu_buttons = [
    [Button.inline("Instructions", b"instructions")],
    [Button.inline("Contact Creator", b"contact_creator")]
    ]

back_button = [Button.inline("<< Back", b"back")]

cancel_button = [Button.inline("", b"CANCEL")]
#------------------------------------------------------------------------------------------------

with TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN) as client:

    @client.on(events.NewMessage(pattern='/start'))
    async def start(event):
        sender_name = event.sender.first_name
        
        message = await event.respond(f"""Hey {sender_name}!👋 \n{start_message}""", buttons=main_menu_buttons)
        messages[str(event.chat_id)] = message # Store the message ID

    @client.on(events.CallbackQuery)
    async def callback_query_handler(event):
        if event.data == b"instructions":
            await client.edit_message(messages[str(event.chat_id)], instruction_message, buttons=back_button)
        elif event.data == b"contact_creator":
            await client.edit_message(messages[str(event.chat_id)], contact_creator_message, buttons=back_button )
        elif event.data == b"back":
            sender_name = event.sender.first_name
            await client.edit_message(messages[str(event.chat_id)],f"""Hey {sender_name}!👋\n {start_message}""",buttons=main_menu_buttons)
        
        else: 
            spotify_link_to_download = None
            
            # The callback_data_str is just the index, so convert it to an integer
            song_index = int(event.data.decode('utf-8'))

            spotify_link_to_download = song_dict[song_index]['spotify_link']
            
            if spotify_link_to_download != None:
                
                waiting_message = await event.respond('⏳')
                
                spotify_link_info = Spotify_Downloader.extract_data_from_spotify_link(spotify_link_to_download)            
                info_tuple = await Spotify_Downloader.download_and_send_spotify_info(client,event,spotify_link_info)
                
                if not info_tuple[0]: #if getting info of the link failed
                    return await event.respond("Sorry, There was a problem processing your link, try again later.")

                send_file_result = await Spotify_Downloader.download_spotify_file_and_send(client,event,info_tuple,spotify_link_info)
                
                if not send_file_result:
                    await event.respond(f"Sorry, there was an error downloading the song")
                
                await waiting_message.delete() 
                    
            if search_result != "None":
                await search_result.delete()
                search_result = "None"
        
    @client.on(events.NewMessage)
    async def handle_message(event):
        global search_result, song_dict
        
        # Check if the message is a Spotify URL
        if 'open.spotify.com' in event.message.text: 
            
            waiting_message = await event.respond('⏳')
                
            spotify_link_info = Spotify_Downloader.extract_data_from_spotify_link(str(event.message.text))            
            info_tuple = await Spotify_Downloader.download_and_send_spotify_info(client,event,spotify_link_info)
            
            if not info_tuple[0]: #if getting info of the link failed
                return await event.respond("Sorry, There was a problem processing your link, try again later.")

            send_file_result = await Spotify_Downloader.download_spotify_file_and_send(client,event,info_tuple,spotify_link_info)
            if not send_file_result:
                await event.respond(f"Sorry, there was an error downloading the song")
            await waiting_message.delete()
        
        else:
            
            # Ignore messages that match the /start pattern
            if event.message.text.startswith('/start'):
                return
          
            if search_result != "None":
                await search_result.delete()
                search_result = "None"
                
            waiting_message = await event.respond('⏳')

            button_list = []
            song_dict = Spotify_Downloader.search_spotify_based_on_user_input(event.message.text)
            
            # Create a list of buttons for each song
            for idx, details in song_dict.items():
                button_text = f"{details['track_name']} - {details['artist']} ({details['release_year']})"
                callback_query = f"{str(idx)}"
                button_list.append([Button.inline(button_text,data=callback_query)])
                
            try:
                # Send the search result message with the buttons
                search_result = await event.respond(search_result_message, buttons=button_list)
                
            except Exception as Err:
                await event.respond(f"Sorry There Was an Error Processing Your Request: {str(Err)}")
                
            await asyncio.sleep(2)
            await waiting_message.delete()

    client.run_until_disconnected()
                    
#### Needs Optiization
# 1. in is_Local -> use rust or C , or a better algoritm
# 2. in finding the spotify link -> create a class named spotify, inside this class should be a proper filter for spotify link
# 3. object oriented
