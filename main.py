import os,asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from plugins.Spotify import Spotify_Downloader
from database import db
from broadcast import BroadcastManager

try:
    load_dotenv('config.env')
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    ADMIN_USER_IDS = [int(id) for id in os.getenv('ADMIN_USER_IDS').split(',')]
except:
    print("Failed to Load .env variables")

#------------------------------------------------------------------------------------------
#Call the initialize method to set up

Spotify_Downloader.initialize()
db.initialize_database()

#------------------------------------------------------------------------------------------
global spotify_link_info, search_result, song_dict, waiting_message
global admin_broadcast, admin_message_to_send, cancel_broadcast, send_to_specified_flag

admin_message_to_send = None
admin_broadcast = False
cancel_broadcast = False
send_to_specified_flag = False

messages = {} # Dictionary to store message IDs

search_result = None

song_dict = None
waiting_message = None
spotify_link_info = None

default_music_quality = {"format": "flac",
                        "quality":  693
                        }

default_downloading_core = "YoutubeDL"

db.set_defualt_values(default_downloading_core,default_music_quality)
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

core_selection_message = """You Can Select the bots Core:

SpotDL: 
- More accurate but takes a little more time to process.
- Has more quality as flac Quality
- Doesnt have mp3-320

YoutubeDL: 
- Less accurate but Faster.
- Has mp3-320 Quality

"""
#------------------------------------------------------------------------------------------
#### Buttons:
main_menu_buttons = [
    [Button.inline("Instructions", b"instructions"),Button.inline("Settings", b"setting")],
    [Button.inline("Contact Creator", b"contact_creator")]
    ]

back_button = Button.inline("<< Back To Main Menu", b"back")

setting_button = [
    [Button.inline("Core", b"setting/core")],
    [Button.inline("Quality", b"setting/quality")],
    [Button.inline("Subscription", b"setting/subscription")],
    [back_button]
    ]

back_button_to_setting = Button.inline("<< Back", b"setting/back")

quality_setting_buttons = [
    [Button.inline("flac", b"setting/quality/flac")],
    [Button.inline("mp3-320", b"setting/quality/mp3/320")],
    [Button.inline("mp3-128", b"setting/quality/mp3/128")],
    [back_button, back_button_to_setting],
]

core_setting_buttons = [
    [Button.inline("YoutubeDL", b"setting/core/youtubedl")],
    [Button.inline("SpotDL", b"setting/core/spotdl")],
    [back_button, back_button_to_setting],
]

subscription_setting_buttons = [
    [Button.inline("Subscribe",data=b"setting/subscription/add")],
    [Button.inline("Cancel Subscription",data=b"setting/subscription/cancel")],
    [back_button, back_button_to_setting]
]

cancel_broadcast_button = [Button.inline("Cancel BroadCast",data=b"admin/cancel_broadcast")]

admins_buttons  =  [
            [Button.inline("Broadcast", b"admin/broadcast")],
            [Button.inline("Stats", b"admin/stats")],
            [Button.inline("Cancel",b"CANCEL")]
]

broadcast_options_buttons = [
    [Button.inline("Broadcast To All Members", b"admin/broadcast/all")],
    [Button.inline("Broadcast To Subscribers Only", b"admin/broadcast/subs")],
    [Button.inline("Broadcast To Specified Users Only", b"admin/broadcast/specified")],
    [Button.inline("Cancel",b"CANCEL")]
]
#------------------------------------------------------------------------------------------------
# Helper function to edit the message

async def send_message_and_store_id(chat_id, text, buttons=None):
    # Send the message and get the message ID
    message = await client.send_message(chat_id, text, buttons=buttons)
    message_id = message.id
    
    # Store the message ID with the chat_id as the key
    messages[str(chat_id)] = message_id
    
async def edit_message(chat_id, message_text, buttons=None):
    # Check if the chat_id exists in the messages dictionary
    if str(chat_id) in messages:
        message_id = messages[str(chat_id)]
        # Edit the message
        await client.edit_message(chat_id, message_id, message_text, buttons=buttons)
    else:
        # If the chat_id is not in the messages dictionary, send a new message
        await send_message_and_store_id(chat_id, message_text, buttons=buttons)

# Helper function to change music quality
async def change_music_quality(chat_id, format, quality):
    music_quality = {'format': format, 'quality': quality}
    db.change_music_quality(chat_id, music_quality)
    user_settings = db.get_user_settings(chat_id)
    music_quality = user_settings[0]
    await edit_message(chat_id, f"Quality successfully changed. \nFormat: {music_quality['format']}\nQuality: {music_quality['quality']}", buttons=quality_setting_buttons)

# Helper function to change downloading core
async def change_downloading_core(chat_id, core):
    db.change_downloading_core(chat_id, core)
    user_settings = db.get_user_settings(chat_id)
    downloading_core = user_settings[1]
    await edit_message(chat_id, f"Core successfully changed. \nCore: {downloading_core}", buttons=core_setting_buttons)

async def cancel_subscription(event,quite:bool = False):
    if db.is_user_subscribed(event.sender_id):
        db.remove_subscribed_user(event.sender_id)
        if not quite:
            await edit_message(event.chat_id, "You have successfully unsubscribed.", buttons=subscription_setting_buttons)
        else:
            await event.respond("You have successfully unsubscribed. You Can Subscribe Any Time in Settings. :)")
        
async def add_subscription(event):
    if not db.is_user_subscribed(event.sender_id):
        db.add_subscribed_user(event.sender_id)
        await edit_message(event.chat_id, "You have successfully subscribed.", buttons=subscription_setting_buttons)

async def set_cancel_broadcast(event):
    setattr(event, 'cancel_broadcast', True)

async def set_admin_broadcast(cancel_broadcast_var):
    global cancel_broadcast
    cancel_broadcast = not cancel_broadcast_var
   
async def handle_broadcast(e,send_to_all:bool = False, send_to_subs:bool = False, send_to_specified:bool = False):
        global admin_broadcast, admin_message_to_send, cancel_broadcast, send_to_specified_flag
        
        if e.sender_id not in ADMIN_USER_IDS:
            return
        
        if send_to_specified:
            send_to_specified_flag = True
            
        cancel_broadcast = False
        admin_broadcast = True
        if send_to_all:
            await BroadcastManager.add_all_users_to_temp()
            
        elif send_to_specified:
            await BroadcastManager.remove_all_users_from_temp()
            time = 60 
            time_to_send = await e.respond("Please enter the user_ids (comma-separated) within the next 60 seconds.",buttons=cancel_broadcast_button)

            for remaining_time in range(time-1, 0, -1):
                # Edit the message to show the new time
                await time_to_send.edit(f"You've Got {remaining_time} seconds to send the user ids:")
                if cancel_broadcast:
                    await time_to_send.edit("BroadCast Cancelled by User.", buttons = None)
                    send_to_specified_flag = False
                    admin_message_to_send = None
                    cancel_broadcast = False
                    admin_broadcast = False
                    return
                elif admin_message_to_send != None:
                    break
                await asyncio.sleep(1)
            send_to_specified_flag = False  
            try:
                parts = admin_message_to_send.message.replace(" ","").split(",")
                user_ids = [int(part) for part in parts] 
                for user_id in user_ids:
                    await BroadcastManager.add_user_to_temp(user_id)
            except:
                await time_to_send.edit("Invalid command format. Use user_id1,user_id2,...")
                admin_message_to_send = None
                cancel_broadcast = False
                admin_broadcast = False
                return
            admin_message_to_send = None
            
        time = 60 
        time_to_send = await e.respond(f"You've Got {time} seconds to send your message",buttons=cancel_broadcast_button)

        for remaining_time in range(time-1, 0, -1):
            # Edit the message to show the new time
            await time_to_send.edit(f"You've Got {remaining_time} seconds to send your message")
            if cancel_broadcast:
                await time_to_send.edit("BroadCast Cancelled by User.", buttons = None)
                break
            elif admin_message_to_send != None:
                break
            await asyncio.sleep(1)
            
        
        if admin_message_to_send == None and cancel_broadcast != True:
            await e.respond("There is nothing to send")
            admin_broadcast = False
            admin_message_to_send = None
            await BroadcastManager.remove_all_users_from_temp()
            return
        
        cancel_subscription_button = Button.inline("Cancel Subscription", b"setting/subscription/cancel/quite")
        try:
            if not cancel_broadcast and send_to_specified:
                await BroadcastManager.broadcast_message_to_temp_members(client, admin_message_to_send)
                await e.respond("Broadcast initiated.")
            elif not cancel_broadcast and send_to_subs:
                await BroadcastManager.broadcast_message_to_sub_members(client, admin_message_to_send,cancel_subscription_button)
                await e.respond("Broadcast initiated.")
            elif not cancel_broadcast and send_to_all:
                await BroadcastManager.broadcast_message_to_temp_members(client, admin_message_to_send)
                await e.respond("Broadcast initiated.")
        except Exception as e:
            await e.respond(f"Broadcast Failed: {str(e)}")
            admin_broadcast = False
            admin_message_to_send = None
            await BroadcastManager.remove_all_users_from_temp()
                
        await BroadcastManager.remove_all_users_from_temp()
        admin_broadcast = False
        admin_message_to_send = None 
        
# Mapping button actions to functions
button_actions = {
    b"instructions": lambda e: edit_message(e.chat_id, instruction_message, buttons=back_button),
    b"contact_creator": lambda e: edit_message(e.chat_id, contact_creator_message, buttons=back_button),
    b"back": lambda e: edit_message(e.chat_id, f"Hey {e.sender.first_name}!👋\n {start_message}", buttons=main_menu_buttons),
    b"setting": lambda e: edit_message(e.chat_id, "Settings :", buttons=setting_button),
    b"setting/back": lambda e: edit_message(e.chat_id, "Settings :", buttons=setting_button),
    b"setting/quality": lambda e: edit_message(e.chat_id, f"Your Quality Setting:\nFormat: {db.get_user_settings(e.sender_id)[0]['format']}\nQuality: {db.get_user_settings(e.sender_id)[0]['quality']}\n\nQualities Available :", buttons=quality_setting_buttons),
    b"setting/quality/mp3/320": lambda e: change_music_quality(e.chat_id, "mp3",   320),
    b"setting/quality/mp3/128": lambda e: change_music_quality(e.chat_id, "mp3",   128),
    b"setting/quality/flac": lambda e: change_music_quality(e.chat_id, "flac",   693),
    b"setting/core": lambda e: edit_message(e.chat_id, core_selection_message+f"\nCore: {db.get_user_settings(e.sender_id)[1]}", buttons=core_setting_buttons),
    b"setting/core/spotdl": lambda e: change_downloading_core(e.chat_id, "SpotDL"),
    b"setting/core/youtubedl": lambda e: change_downloading_core(e.chat_id, "YoutubeDL"),
    b"setting/subscription": lambda e: edit_message(e.chat_id,f"Join our community and stay updated with the latest news and features of our bot. Be the first to experience new enhancements and improvements!\nYour Subscription Status: {db.is_user_subscribed(e.sender_id)}",buttons=subscription_setting_buttons),
    b"setting/subscription/cancel": lambda e: asyncio.create_task(cancel_subscription(e)),
    b"setting/subscription/cancel/quite": lambda e: asyncio.create_task(cancel_subscription(e,quite=True)),
    b"setting/subscription/add": lambda e: asyncio.create_task(add_subscription(e)),
    b"CANCEL": lambda e: e.delete(),
    b"admin/cancel_broadcast": lambda e: set_admin_broadcast(False),
    b"admin/stats": lambda e: e.respond(f"Number of Users: {db.count_all_user_ids()}"),
    b"admin/broadcast": lambda e: edit_message(e.chat_id, "BroadCast Options: ", buttons=broadcast_options_buttons),
    b"admin/broadcast/all": lambda e: handle_broadcast(e,send_to_all=True),
    b"admin/broadcast/subs": lambda e: handle_broadcast(e,send_to_subs=True),
    b"admin/broadcast/specified": lambda e: handle_broadcast(e,send_to_specified=True),
    # Add other actions here
}
        
#------------------------------------------------------------------------------------------------
with TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN) as client:

    @client.on(events.NewMessage(pattern='/start'))
    async def start(event):
        sender_name = event.sender.first_name
        user_id = event.sender_id
        
        user_settings = db.get_user_settings(user_id)
        if user_settings[0] == None and user_settings[1] == None:
            db.save_user_settings(user_id, db.default_music_quality, db.default_downloading_core)

        message = await event.respond(f"""Hey {sender_name}!👋 \n{start_message}""", buttons=main_menu_buttons)
        messages[str(event.chat_id)] = message # Store the message ID
        
    @client.on(events.NewMessage(pattern='/broadcast'))
    async def handle_broadcast_command(event):
        global admin_broadcast, admin_message_to_send, cancel_broadcast
        
        if event.sender_id not in ADMIN_USER_IDS:
            return
        
        cancel_broadcast = False
        admin_broadcast = True
        if event.message.text.startswith('/broadcast_to_all'):
            await BroadcastManager.add_all_users_to_temp()
            
        elif event.message.text.startswith('/broadcast'):
            command_parts = event.message.text.split(' ',  1)

            if len(command_parts) == 1:
                pass
            elif len(command_parts) <  2 or not command_parts[1].startswith('(') or not command_parts[1].endswith(')'):
                await event.respond("Invalid command format. Use /broadcast (user_id1,user_id2,...)")
                admin_broadcast = False
                admin_message_to_send = None
                return

            if len(command_parts) != 1:
                await BroadcastManager.remove_all_users_from_temp()
                user_ids_str = command_parts[1][1:-1]  # Remove the parentheses
                specified_user_ids = [int(user_id) for user_id in user_ids_str.split(',')]
                for user_id in specified_user_ids:
                    await BroadcastManager.add_user_to_temp(user_id)
        
        time = 60 
        time_to_send = await event.respond(f"You've Got {time} seconds to send your message",buttons=cancel_broadcast_button)

        for remaining_time in range(time-1, 0, -1):
            # Edit the message to show the new time
            await time_to_send.edit(f"You've Got {remaining_time} seconds to send your message")
            if cancel_broadcast:
                await time_to_send.edit("BroadCast Cancelled by User.", buttons = None)
                break
            elif admin_message_to_send != None:
                break
            await asyncio.sleep(1)
        
        # Check if the message is "/broadcast_to_all"
        if admin_message_to_send == None and cancel_broadcast != True:
            await event.respond("There is nothing to send")
            admin_broadcast = False
            admin_message_to_send = None
            await BroadcastManager.remove_all_users_from_temp()
            return
        
        cancel_subscription_button = Button.inline("Cancel Subscription", b"setting/subscription/cancel/quite")
        try:
            if not cancel_broadcast and len(command_parts) != 1:
                await BroadcastManager.broadcast_message_to_temp_members(client, admin_message_to_send)
                await event.respond("Broadcast initiated.")
            elif not cancel_broadcast and len(command_parts) == 1:
                await BroadcastManager.broadcast_message_to_sub_members(client, admin_message_to_send,cancel_subscription_button)
                await event.respond("Broadcast initiated.")
        except:
            try:
                if not cancel_broadcast:
                    await BroadcastManager.broadcast_message_to_temp_members(client, admin_message_to_send)
                    await event.respond("Broadcast initiated.")
            except Exception as e:
                await event.respond(f"Broadcast Failed: {str(e)}")
                admin_broadcast = False
                admin_message_to_send = None
                await BroadcastManager.remove_all_users_from_temp()
                
        await BroadcastManager.remove_all_users_from_temp()
        admin_broadcast = False
        admin_message_to_send = None

    @client.on(events.NewMessage(pattern='/settings'))
    async def handle_settings_command(event):
        await send_message_and_store_id(event.chat_id,"Settings :", buttons=setting_button)
    
    @client.on(events.NewMessage(pattern='/subscription'))
    async def handle_subscription_command(event):
        await send_message_and_store_id(event.chat_id,f"Join our community and stay updated with the latest news and features of our bot. Be the first to experience new enhancements and improvements!\nYour Subscription Status: {db.is_user_subscribed(event.sender_id)}",buttons=subscription_setting_buttons)

    @client.on(events.NewMessage(pattern='/help'))
    async def handle_help_command(event):
        await send_message_and_store_id(instruction_message, buttons=main_menu_buttons)

    @client.on(events.NewMessage(pattern='/quality'))
    async def handle_quality_command(event):
        await send_message_and_store_id(event.chat_id, f"Your Quality Setting:\nFormat: {db.get_user_settings(event.sender_id)[0]['format']}\nQuality: {db.get_user_settings(event.sender_id)[0]['quality']}\n\nQualities Available :", buttons=quality_setting_buttons)

    @client.on(events.NewMessage(pattern='/core'))
    async def handle_core_command(event):
        await send_message_and_store_id(event.chat_id, core_selection_message+f"\nCore: {db.get_user_settings(event.sender_id)[1]}", buttons=core_setting_buttons)

    @client.on(events.NewMessage(pattern='/admin'))
    async def handle_admin_command(event):
        if event.sender_id not in ADMIN_USER_IDS:
            return
        await send_message_and_store_id(event.chat_id,"Admin commands:", buttons=admins_buttons)
    
    @client.on(events.NewMessage(pattern='/stats'))
    async def handle_stats_command(event):
        if event.sender_id not in ADMIN_USER_IDS:
            return
    
        number_of_users = db.count_all_user_ids()
        await event.respond(f"Number of Users: {number_of_users}")
    
    @client.on(events.CallbackQuery)
    async def callback_query_handler(event):
        global waiting_message, spotify_link_info, search_result, cancel_broadcast
        
        action = button_actions.get(event.data)
        if action:  # Check if action is not None
            await action(event) 
          
        elif event.data.startswith(b"@music"):
            send_file_result = await Spotify_Downloader.download_spotify_file_and_send(client,event,spotify_link_info)
            if not send_file_result:
                await event.respond(f"Sorry, there was an error downloading the song")
            await waiting_message.delete() if waiting_message != None else None
       
            # if search_result != None: // Removes the search list after sending the track
            #     await search_result.delete()
            #     search_result = None

        elif event.data.isdigit():
            
            spotify_link_to_download = None
            song_index = int(event.data.decode('utf-8'))

            spotify_link_to_download = song_dict[song_index]['spotify_link']
            
            if spotify_link_to_download != None:
                
                waiting_message = await event.respond('⏳')
                
                spotify_link_info = Spotify_Downloader.extract_data_from_spotify_link(spotify_link_to_download)            
                send_info_result = await Spotify_Downloader.download_and_send_spotify_info(client,event,spotify_link_info)
                
                if not send_info_result: #if getting info of the link failed
                    return await event.respond("Sorry, There was a problem processing your link, try again later.")

    @client.on(events.NewMessage)
    async def handle_message(event):
        global search_result, song_dict, spotify_link_info, waiting_message, admin_broadcast
        global admin_message_to_send, send_to_specified_flag
        
        # Check if the message is a Spotify URL
        if Spotify_Downloader.is_spotify_link(event.message.text): 
            
            user_id = event.sender_id 
            music_quality, downloading_core = db.get_user_settings(user_id)
            if music_quality == None or downloading_core == None :
                await event.respond("We Have Updated The Bot, Please start Over using the /start command.")
                return
           
            waiting_message = await event.respond('⏳')
                
            spotify_link_info = Spotify_Downloader.extract_data_from_spotify_link(str(event.message.text))            
            info_tuple = await Spotify_Downloader.download_and_send_spotify_info(client,event,spotify_link_info)
            
            if not info_tuple: #if getting info of the link failed
                await waiting_message.delete()
                return await event.respond("Sorry, There was a problem processing your request.")

        else:
            
            user_id = event.sender_id 
            music_quality, downloading_core = db.get_user_settings(user_id)
            if music_quality == None or downloading_core == None :
                await event.respond("We Have Updated The Bot, Please start Over using the /start command.")
                return
            
            if event.message.text.startswith('/'):
                return

            if admin_broadcast and send_to_specified_flag:
                admin_message_to_send = event.message
                return
            elif admin_broadcast:
                admin_message_to_send = event.message
                return
            
            if search_result != None:
                await search_result.delete()
                search_result = None
                
            waiting_message_search = await event.respond('⏳')

            sanitized_query = Spotify_Downloader.sanitize_query(event.message.text)
            if not sanitized_query:
                await event.respond("Your input was not valid. Please try again with a valid search term.")
                return

            song_dict = Spotify_Downloader.search_spotify_based_on_user_input(sanitized_query)

            if all(not value for value in song_dict.values()):
                await waiting_message_search.delete()
                await event.respond("Sorry,I couldnt Find any music that matches your Search query.")
                return
            
            button_list = [
                [Button.inline(f"🎧 {details['track_name']} - {details['artist']} 🎧 ({details['release_year']})", data=str(idx))]
                for idx, details in song_dict.items()
            ]

            button_list.append([Button.inline("Cancel", b"CANCEL")])

            try:
                search_result = await event.respond(search_result_message, buttons=button_list)
            except Exception as Err:
                await event.respond(f"Sorry There Was an Error Processing Your Request: {str(Err)}")

            await asyncio.sleep(1.5)
            await waiting_message_search.delete()

    client.run_until_disconnected()
                    
#### Needs Optiization
# 1. in is_Local -> use rust or C , or a better algoritm
# 2. in finding the spotify link -> create a class named spotify, inside this class should be a proper filter for spotify link
# 3. object oriented
