import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from plugins.Spotify import Spotify_Downloader

try:
    load_dotenv('config.env')
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
except:
    print("Failed to Load .env variables")

#------------------------------------------------------------------------------------------
messages = {} # Dictionary to store message IDs

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

#------------------------------------------------------------------------------------------
#### Buttons:
main_menu_buttons = [
    [Button.inline("Instructions", b"instructions")],
    [Button.inline("Contact Creator", b"contact_creator")]
    ]

back_button = [Button.inline("<< Back", b"back")]

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
        
    @client.on(events.NewMessage)
    async def handle_message(event):
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
            
    client.run_until_disconnected()
                    
                    
#### Needs Optiization
# 1. in is_Local -> use rust or C , or a better algoritm
# 2. in finding the spotify link -> create a class named spotify, inside this class should be a proper filter for spotify link
# 3. object oriented
