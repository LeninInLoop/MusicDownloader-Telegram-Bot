import os,asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from plugins.Spotify import Spotify_Downloader
from database import db
from broadcast import BroadcastManager
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.errors import ChatAdminRequiredError

class Bot:

    @staticmethod
    def initialize():
        Bot.load_env_variables()
        Bot.initialize_globals()
        Bot.initialize_spotify_downloader()
        Bot.initialize_database()
        Bot.initialize_messages()
        Bot.initialize_buttons()
        Bot.initialize_action_queries()
        
    @classmethod
    def load_env_variables(cls):
        try:
            load_dotenv('config.env')
            cls.BOT_TOKEN = os.getenv('BOT_TOKEN')
            cls.API_ID = os.getenv("API_ID")
            cls.API_HASH = os.getenv("API_HASH")
            cls.ADMIN_USER_IDS = [int(id) for id in os.getenv('ADMIN_USER_IDS').split(',')]
        except:
            print("Failed to Load .env variables")

    @classmethod
    def initialize_globals(cls):
        # Initialize global variables here
        cls.channel_usernames = ["Spotify_yt_downloader"]
        cls.Client = None
        cls.admin_message_to_send = None
        cls.admin_broadcast = False
        cls.cancel_broadcast = False
        cls.send_to_specified_flag = False
        cls.messages = {}
        cls.search_result = None
        cls.song_dict = None
        cls.waiting_message = None
        cls.spotify_link_info = None
        
    @staticmethod
    def initialize_spotify_downloader():
        Spotify_Downloader.initialize()

    @staticmethod
    def initialize_database():
        db.initialize_database()

    @classmethod
    def initialize_messages(cls):
        # Initialize messages here
        cls.start_message = """
I'm a dedicated Spotify Downloader, ready to turn your favorite tunes into downloadable tracks. 🎶🎵

Just a heads up, this service is meant for personal use only. Let's keep those downloaded tracks under wraps, shall we? 😉

So, buckle up and let's rock this music journey together! 🎧
"""

        cls.instruction_message = """
To begin using this service, please follow these steps:

1. Share the link to the Spotify song you wish to download.🔗
2. Await the confirmation message indicating that the download process has commenced.📣
3. Upon completion of the download, I will promptly send you the downloaded file.💾

UPDATE: You now have the option to search the Spotify database
by providing the song's title, lyrics, or any other pertinent details.
This feature significantly enhances the search functionality,
offering a more extensive and user-friendly experience.
"""

        cls.contact_creator_message = """Should you have any inquiries or require feedback, please do not hesitate to contact me. 🌐
>> @AdibNikjou"""

        cls.search_result_message = """🎵 The following are the top 10 search results that correspond to your query:
"""

        cls.core_selection_message = """You Can Select the bots Core:

SpotDL: 
- More accurate but takes a little more time to process.
- Has more quality as flac Quality
- Doesnt have mp3-320

YoutubeDL: 
- Less accurate but Faster.
- Has mp3-320 Quality

"""
        cls.JOIN_CHANNEL_MESSAGE = """It seems you are not a member of our channels yet.
Please join our channels to continue."""

    @classmethod
    def initialize_buttons(cls):
        # Initialize buttons here
        cls.main_menu_buttons = [
            [Button.inline("Instructions", b"instructions"),Button.inline("Settings", b"setting")],
            [Button.inline("Contact Creator", b"contact_creator")]
            ]

        cls.back_button = Button.inline("<< Back To Main Menu", b"back")

        cls.setting_button = [
            [Button.inline("Core", b"setting/core")],
            [Button.inline("Quality", b"setting/quality")],
            [Button.inline("Subscription", b"setting/subscription")],
            [cls.back_button]
            ]

        cls.back_button_to_setting = Button.inline("<< Back", b"setting/back")

        cls.quality_setting_buttons = [
            [Button.inline("flac", b"setting/quality/flac")],
            [Button.inline("mp3-320", b"setting/quality/mp3/320")],
            [Button.inline("mp3-128", b"setting/quality/mp3/128")],
            [cls.back_button, cls.back_button_to_setting],
        ]

        cls.core_setting_buttons = [
            [Button.inline("YoutubeDL", b"setting/core/youtubedl")],
            [Button.inline("SpotDL", b"setting/core/spotdl")],
            [cls.back_button, cls.back_button_to_setting],
        ]

        cls.subscription_setting_buttons = [
            [Button.inline("Subscribe",data=b"setting/subscription/add")],
            [Button.inline("Cancel Subscription",data=b"setting/subscription/cancel")],
            [cls.back_button, cls.back_button_to_setting]
        ]

        cls.cancel_broadcast_button = [Button.inline("Cancel BroadCast",data=b"admin/cancel_broadcast")]

        cls.admins_buttons  =  [
                    [Button.inline("Broadcast", b"admin/broadcast")],
                    [Button.inline("Stats", b"admin/stats")],
                    [Button.inline("Cancel",b"CANCEL")]
        ]

        cls.broadcast_options_buttons = [
            [Button.inline("Broadcast To All Members", b"admin/broadcast/all")],
            [Button.inline("Broadcast To Subscribers Only", b"admin/broadcast/subs")],
            [Button.inline("Broadcast To Specified Users Only", b"admin/broadcast/specified")],
            [Button.inline("Cancel",b"CANCEL")]
        ]

    @classmethod
    def initialize_action_queries(cls):
        # Mapping button actions to functions
        cls.button_actions = {
            b"instructions": lambda e: Bot.edit_message(e.chat_id, Bot.instruction_message, buttons=Bot.back_button),
            b"contact_creator": lambda e: Bot.edit_message(e.chat_id, Bot.contact_creator_message, buttons=Bot.back_button),
            b"back": lambda e: Bot.edit_message(e.chat_id, f"Hey {e.sender.first_name}!👋\n {Bot.start_message}", buttons=Bot.main_menu_buttons),
            b"setting": lambda e: Bot.edit_message(e.chat_id, "Settings :", buttons=Bot.setting_button),
            b"setting/back": lambda e: Bot.edit_message(e.chat_id, "Settings :", buttons=Bot.setting_button),
            b"setting/quality": lambda e: Bot.edit_message(e.chat_id, f"Your Quality Setting:\nFormat: {db.get_user_settings(e.sender_id)[0]['format']}\nQuality: {db.get_user_settings(e.sender_id)[0]['quality']}\n\nQualities Available :", buttons=Bot.quality_setting_buttons),
            b"setting/quality/mp3/320": lambda e: Bot.change_music_quality(e.chat_id, "mp3",   320),
            b"setting/quality/mp3/128": lambda e: Bot.change_music_quality(e.chat_id, "mp3",   128),
            b"setting/quality/flac": lambda e: Bot.change_music_quality(e.chat_id, "flac",   693),
            b"setting/core": lambda e: Bot.edit_message(e.chat_id, Bot.core_selection_message+f"\nCore: {db.get_user_settings(e.sender_id)[1]}", buttons=Bot.core_setting_buttons),
            b"setting/core/spotdl": lambda e: Bot.change_downloading_core(e.chat_id, "SpotDL"),
            b"setting/core/youtubedl": lambda e: Bot.change_downloading_core(e.chat_id, "YoutubeDL"),
            b"setting/subscription": lambda e: Bot.edit_message(e.chat_id,f"Join our community and stay updated with the latest news and features of our bot. Be the first to experience new enhancements and improvements!\nYour Subscription Status: {db.is_user_subscribed(e.sender_id)}",buttons=Bot.subscription_setting_buttons),
            b"setting/subscription/cancel": lambda e: asyncio.create_task(Bot.cancel_subscription(e)),
            b"setting/subscription/cancel/quite": lambda e: asyncio.create_task(Bot.cancel_subscription(e,quite=True)),
            b"setting/subscription/add": lambda e: asyncio.create_task(Bot.add_subscription(e)),
            b"CANCEL": lambda e: e.delete(),
            b"admin/cancel_broadcast": lambda e: Bot.set_admin_broadcast(False),
            b"admin/stats": lambda e: e.respond(f"Number of Users: {db.count_all_user_ids()}"),
            b"admin/broadcast": lambda e: Bot.edit_message(e.chat_id, "BroadCast Options: ", buttons=Bot.broadcast_options_buttons),
            b"admin/broadcast/all": lambda e: Bot.handle_broadcast(e,send_to_all=True),
            b"admin/broadcast/subs": lambda e: Bot.handle_broadcast(e,send_to_subs=True),
            b"admin/broadcast/specified": lambda e: Bot.handle_broadcast(e,send_to_specified=True),
            # Add other actions here
        }

    @staticmethod
    async def send_message_and_store_id(chat_id, text, buttons=None):
        message = await Bot.Client.send_message(chat_id, text, buttons=buttons)
        message_id = message.id
        Bot.messages[str(chat_id)] = message_id # Store the message ID with the chat_id as the key

    @staticmethod
    async def edit_message(chat_id, message_text, buttons=None):
        if str(chat_id) in Bot.messages:
            message_id = Bot.messages[str(chat_id)]
            await Bot.Client.edit_message(chat_id, message_id, message_text, buttons=buttons)
        else:
            await Bot.send_message_and_store_id(chat_id, message_text, buttons=buttons)

    @staticmethod
    async def change_music_quality(chat_id, format, quality):
        music_quality = {'format': format, 'quality': quality}
        db.change_music_quality(chat_id, music_quality)
        user_settings = db.get_user_settings(chat_id)
        music_quality = user_settings[0]
        await Bot.edit_message(chat_id, f"Quality successfully changed. \nFormat: {music_quality['format']}\nQuality: {music_quality['quality']}", buttons=Bot.quality_setting_buttons)

    @staticmethod
    async def change_downloading_core(chat_id, core):
        db.change_downloading_core(chat_id, core)
        user_settings = db.get_user_settings(chat_id)
        downloading_core = user_settings[1]
        await Bot.edit_message(chat_id, f"Core successfully changed. \nCore: {downloading_core}", buttons=Bot.core_setting_buttons)

    @staticmethod
    async def cancel_subscription(event, quite: bool = False):
        if db.is_user_subscribed(event.sender_id):
            db.remove_subscribed_user(event.sender_id)
            if not quite:
                await Bot.edit_message(event.chat_id, "You have successfully unsubscribed.", buttons=Bot.subscription_setting_buttons)
            else:
                await event.respond("You have successfully unsubscribed. You Can Subscribe Any Time in Settings. :)")

    @staticmethod
    async def add_subscription(event):
        if not db.is_user_subscribed(event.sender_id):
            db.add_subscribed_user(event.sender_id)
            await Bot.edit_message(event.chat_id, "You have successfully subscribed.", buttons=Bot.subscription_setting_buttons)

    @staticmethod
    async def set_admin_broadcast(broadcast: bool):
        Bot.cancel_broadcast = not broadcast

    @staticmethod
    def join_channel_button(channel_username):
        """
        Returns a Button object that, when clicked, directs users to join the specified channel.
        """
        return Button.url("Join Channel", f"https://t.me/{channel_username}")
    

    @staticmethod
    async def is_user_in_channel(user_id, channel_usernames=None):
        if channel_usernames is None:
            channel_usernames = Bot.channel_usernames
        channels_user_is_not_in = []

        for channel_username in channel_usernames:
            channel = await Bot.Client.get_entity(channel_username)
            offset =  0  
            while True:
                try:
                    participants = await Bot.Client(GetParticipantsRequest(
                        channel,
                        ChannelParticipantsSearch(''),  # Search query, empty for all participants
                        offset=offset,  # Providing the offset
                        limit=100,  # Adjust the limit as needed
                        hash=0
                    ))
                except ChatAdminRequiredError:
                    print(f"ChatAdminRequiredError: Bot does not have admin privileges in {channel_username}.")
                    break
                
                if not participants.users:
                    break  # No more participants to fetch
                if not any(participant.id == user_id for participant in participants.users):
                    channels_user_is_not_in.append(channel_username)
                    break  # User found, no need to check other channels
                
                offset += len(participants.users)  # Increment offset for the next batch
        return channels_user_is_not_in

    @staticmethod
    async def respond_based_on_channel_membership(event, message_if_in_channels:str = None, buttons:str = None, channels_user_is_not_in:list = None):
        sender_name = event.sender.first_name
        user_id = event.sender_id
        buttons_if_in_channesl = buttons
        
        channels_user_is_not_in = await Bot.is_user_in_channel(user_id) if channels_user_is_not_in == None else channels_user_is_not_in
        
        if channels_user_is_not_in:
            join_channel_buttons = [Bot.join_channel_button(channel) for channel in channels_user_is_not_in]
            await Bot.send_message_and_store_id(event.chat_id ,f"""Hey {sender_name}!👋 \n{Bot.JOIN_CHANNEL_MESSAGE}""", buttons=join_channel_buttons)
        elif message_if_in_channels != None:
            await Bot.send_message_and_store_id(event.chat_id,f"""{message_if_in_channels}""", buttons=buttons_if_in_channesl)
        
    @staticmethod
    async def handle_broadcast(e, send_to_all: bool = False, send_to_subs: bool = False, send_to_specified: bool = False):
        
        if e.sender_id not in Bot.ADMIN_USER_IDS:
            return
        
        if send_to_specified:
            Bot.send_to_specified_flag = True
            
        Bot.cancel_broadcast = False
        Bot.admin_broadcast = True
        if send_to_all:
            await BroadcastManager.add_all_users_to_temp()
            
        elif send_to_specified:
            await BroadcastManager.remove_all_users_from_temp()
            time = 60 
            time_to_send = await e.respond("Please enter the user_ids (comma-separated) within the next 60 seconds.",buttons=Bot.cancel_broadcast_button)

            for remaining_time in range(time-1, 0, -1):
                # Edit the message to show the new time
                await time_to_send.edit(f"You've Got {remaining_time} seconds to send the user ids seperated with:")
                if Bot.cancel_broadcast:
                    await time_to_send.edit("BroadCast Cancelled by User.", buttons = None)
                    Bot.send_to_specified_flag = False
                    Bot.admin_message_to_send = None
                    Bot.cancel_broadcast = False
                    Bot.admin_broadcast = False
                    return
                elif Bot.admin_message_to_send != None:
                    break
                await asyncio.sleep(1)
            Bot.send_to_specified_flag = False  
            try:
                parts = Bot.admin_message_to_send.message.replace(" ","").split(",")
                user_ids = [int(part) for part in parts] 
                for user_id in user_ids:
                    await BroadcastManager.add_user_to_temp(user_id)
            except:
                await time_to_send.edit("Invalid command format. Use user_id1,user_id2,...")
                Bot.admin_message_to_send = None
                Bot.cancel_broadcast = False
                Bot.admin_broadcast = False
                return
            Bot.admin_message_to_send = None
            
        time = 60 
        time_to_send = await e.respond(f"You've Got {time} seconds to send your message",buttons=Bot.cancel_broadcast_button)

        for remaining_time in range(time-1, 0, -1):
            # Edit the message to show the new time
            await time_to_send.edit(f"You've Got {remaining_time} seconds to send your message")
            if Bot.cancel_broadcast:
                await time_to_send.edit("BroadCast Cancelled by User.", buttons = None)
                break
            elif Bot.admin_message_to_send != None:
                break
            await asyncio.sleep(1)
            
        if Bot.admin_message_to_send == None and Bot.cancel_broadcast != True:
            await e.respond("There is nothing to send")
            Bot.admin_broadcast = False
            Bot.admin_message_to_send = None
            await BroadcastManager.remove_all_users_from_temp()
            return
        
        cancel_subscription_button = Button.inline("Cancel Subscription", b"setting/subscription/cancel/quite")
        try:
            if not Bot.cancel_broadcast and send_to_specified:
                await BroadcastManager.broadcast_message_to_temp_members(Bot.Client, Bot.admin_message_to_send)
                await e.respond("Broadcast initiated.")
            elif not Bot.cancel_broadcast and send_to_subs:
                await BroadcastManager.broadcast_message_to_sub_members(Bot.Client, Bot.admin_message_to_send,cancel_subscription_button)
                await e.respond("Broadcast initiated.")
            elif not Bot.cancel_broadcast and send_to_all:
                await BroadcastManager.broadcast_message_to_temp_members(Bot.Client, Bot.admin_message_to_send)
                await e.respond("Broadcast initiated.")
        except Exception as e:
            await e.respond(f"Broadcast Failed: {str(e)}")
            Bot.admin_broadcast = False
            Bot.admin_message_to_send = None
            await BroadcastManager.remove_all_users_from_temp()
                
        await BroadcastManager.remove_all_users_from_temp()
        Bot.admin_broadcast = False
        Bot.admin_message_to_send = None 

    @staticmethod
    async def start(event):
        sender_name = event.sender.first_name
        user_id = event.sender_id
        
        user_settings = db.get_user_settings(user_id)
        if user_settings[0] == None and user_settings[1] == None:
            db.save_user_settings(user_id, db.default_music_quality, db.default_downloading_core)
        await Bot.respond_based_on_channel_membership(event,f"""Hey {sender_name}!👋 \n{Bot.start_message}""", buttons=Bot.main_menu_buttons)
        
    @staticmethod
    async def handle_broadcast_command(event):
        # ... implementation of the handle_broadcast_command method ...
        if event.sender_id not in Bot.ADMIN_USER_IDS:
                    return
                
        Bot.cancel_broadcast = False
        Bot.admin_broadcast = True
        if event.message.text.startswith('/broadcast_to_all'):
            await BroadcastManager.add_all_users_to_temp()
            
        elif event.message.text.startswith('/broadcast'):
            command_parts = event.message.text.split(' ',  1)

            if len(command_parts) == 1:
                pass
            elif len(command_parts) <  2 or not command_parts[1].startswith('(') or not command_parts[1].endswith(')'):
                await event.respond("Invalid command format. Use /broadcast (user_id1,user_id2,...)")
                Bot.admin_broadcast = False
                Bot.admin_message_to_send = None
                return

            if len(command_parts) != 1:
                await BroadcastManager.remove_all_users_from_temp()
                user_ids_str = command_parts[1][1:-1]  # Remove the parentheses
                specified_user_ids = [int(user_id) for user_id in user_ids_str.split(',')]
                for user_id in specified_user_ids:
                    await BroadcastManager.add_user_to_temp(user_id)
        
        time = 60 
        time_to_send = await event.respond(f"You've Got {time} seconds to send your message",buttons=Bot.cancel_broadcast_button)

        for remaining_time in range(time-1, 0, -1):
            # Edit the message to show the new time
            await time_to_send.edit(f"You've Got {remaining_time} seconds to send your message")
            if Bot.cancel_broadcast:
                await time_to_send.edit("BroadCast Cancelled by User.", buttons = None)
                break
            elif Bot.admin_message_to_send != None:
                break
            await asyncio.sleep(1)
        
        # Check if the message is "/broadcast_to_all"
        if Bot.admin_message_to_send == None and Bot.cancel_broadcast != True:
            await event.respond("There is nothing to send")
            Bot.admin_broadcast = False
            Bot.admin_message_to_send = None
            await BroadcastManager.remove_all_users_from_temp()
            return
        
        cancel_subscription_button = Button.inline("Cancel Subscription", b"setting/subscription/cancel/quite")
        try:
            if not Bot.cancel_broadcast and len(command_parts) != 1:
                await BroadcastManager.broadcast_message_to_temp_members(Bot.Client, Bot.admin_message_to_send)
                await event.respond("Broadcast initiated.")
            elif not Bot.cancel_broadcast and len(command_parts) == 1:
                await BroadcastManager.broadcast_message_to_sub_members(Bot.Client, Bot.admin_message_to_send, cancel_subscription_button)
                await event.respond("Broadcast initiated.")
        except:
            try:
                if not Bot.cancel_broadcast:
                    await BroadcastManager.broadcast_message_to_temp_members(Bot.Client, Bot.admin_message_to_send)
                    await event.respond("Broadcast initiated.")
            except Exception as e:
                await event.respond(f"Broadcast Failed: {str(e)}")
                Bot.admin_broadcast = False
                Bot.admin_message_to_send = None
                await BroadcastManager.remove_all_users_from_temp()
                
        await BroadcastManager.remove_all_users_from_temp()
        Bot.admin_broadcast = False
        Bot.admin_message_to_send = None

    @staticmethod
    async def handle_settings_command(event):
        await Bot.respond_based_on_channel_membership(event,"Settings :", buttons=Bot.setting_button)
        
    @staticmethod
    async def handle_subscription_command(event):
        await Bot.respond_based_on_channel_membership(event,f"Join our community and stay updated with the latest news and features of our bot. Be the first to experience new enhancements and improvements!\nYour Subscription Status: {db.is_user_subscribed(event.sender_id)}"
                            ,buttons=Bot.subscription_setting_buttons)

    @staticmethod
    async def handle_help_command(event):
        await Bot.respond_based_on_channel_membership(event,Bot.instruction_message, buttons=Bot.main_menu_buttons)

    @staticmethod
    async def handle_quality_command(event):
        await Bot.respond_based_on_channel_membership(event, f"Your Quality Setting:\nFormat: {db.get_user_settings(event.sender_id)[0]['format']}\nQuality: {db.get_user_settings(event.sender_id)[0]['quality']}\n\nQualities Available :",
                            buttons=Bot.quality_setting_buttons)
        
    @staticmethod
    async def handle_core_command(event):
        await Bot.respond_based_on_channel_membership(event, Bot.core_selection_message+f"\nCore: {db.get_user_settings(event.sender_id)[1]}",
                            buttons=Bot.core_setting_buttons)
        
    @staticmethod
    async def handle_admin_command(event):
        if event.sender_id not in Bot.ADMIN_USER_IDS:
            return
        await Bot.send_message_and_store_id(event.chat_id,"Admin commands:", buttons=Bot.admins_buttons)

    @staticmethod
    async def handle_stats_command(event):
        if event.sender_id not in Bot.ADMIN_USER_IDS:
            return
        number_of_users = db.count_all_user_ids()
        await event.respond(f"Number of Users: {number_of_users}")

    @staticmethod
    async def callback_query_handler(event):
        action = Bot.button_actions.get(event.data)
        if action:
            await action(event) 
          
        elif event.data.startswith(b"@music"):
            send_file_result = await Spotify_Downloader.download_spotify_file_and_send(Bot.Client,event,Bot.spotify_link_info)
            if not send_file_result:
                Spotify_Downloader.is_file_processing = False
                await event.respond(f"Sorry, there was an error downloading the song.Try Using a Different Core.\nYou Can Change Your Core in the Settings or Simply Use This command to See Available Cores: /core")
            await Bot.waiting_message.delete() if Bot.waiting_message != None else None
       
            # if search_result != None: // Removes the search list after sending the track
            #     await search_result.delete()
            #     search_result = None

        elif event.data.isdigit():
            
            spotify_link_to_download = None
            song_index = int(event.data.decode('utf-8'))

            spotify_link_to_download = Bot.song_dict[song_index]['spotify_link']
            
            if spotify_link_to_download != None:
                
                Bot.waiting_message = await event.respond('⏳')
                
                Bot.spotify_link_info = Spotify_Downloader.extract_data_from_spotify_link(spotify_link_to_download)            
                send_info_result = await Spotify_Downloader.download_and_send_spotify_info(Bot.Client,event,Bot.spotify_link_info)
                
                if not send_info_result: #if getting info of the link failed
                    return await event.respond("Sorry, There was a problem processing your link, try again later.")

    @staticmethod
    async def handle_message(event):

        channels_user_is_not_in = await Bot.is_user_in_channel(event.sender_id)
        if channels_user_is_not_in != []:
            return await Bot.respond_based_on_channel_membership(event,None,None,channels_user_is_not_in)
          
        if Spotify_Downloader.is_spotify_link(event.message.text): 
            user_id = event.sender_id 
            music_quality, downloading_core = db.get_user_settings(user_id)
            if music_quality == None or downloading_core == None :
                await event.respond("We Have Updated The Bot, Please start Over using the /start command.")
                return
           
            Bot.waiting_message = await event.respond('⏳')
            Bot.spotify_link_info = Spotify_Downloader.extract_data_from_spotify_link(str(event.message.text))            
            info_tuple = await Spotify_Downloader.download_and_send_spotify_info(Bot.Client,event,Bot.spotify_link_info)
            
            if not info_tuple: #if getting info of the link failed
                await Bot.waiting_message.delete()
                return await event.respond("Sorry, There was a problem processing your request.")

        else:
            
            user_id = event.sender_id 
            music_quality, downloading_core = db.get_user_settings(user_id)
            if music_quality == None or downloading_core == None :
                await event.respond("We Have Updated The Bot, Please start Over using the /start command.")
                return
            if event.message.text.startswith('/'):
                return
            
            if Bot.admin_broadcast and Bot.send_to_specified_flag:
                Bot.admin_message_to_send = event.message
                return
            elif Bot.admin_broadcast:
                Bot.admin_message_to_send = event.message
                return
            
            if Bot.search_result != None:
                await Bot.search_result.delete()
                Bot.search_result = None
                
            waiting_message_search = await event.respond('⏳')
            sanitized_query = Spotify_Downloader.sanitize_query(event.message.text)
            if not sanitized_query:
                await event.respond("Your input was not valid. Please try again with a valid search term.")
                return

            Bot.song_dict = Spotify_Downloader.search_spotify_based_on_user_input(sanitized_query)

            if all(not value for value in Bot.song_dict.values()):
                await waiting_message_search.delete()
                await event.respond("Sorry,I couldnt Find any music that matches your Search query.")
                return
            
            button_list = [
                [Button.inline(f"🎧 {details['track_name']} - {details['artist']} 🎧 ({details['release_year']})", data=str(idx))]
                for idx, details in Bot.song_dict.items()
            ]

            button_list.append([Button.inline("Cancel", b"CANCEL")])

            try:
                Bot.search_result = await event.respond(Bot.search_result_message, buttons=button_list)
            except Exception as Err:
                await event.respond(f"Sorry There Was an Error Processing Your Request: {str(Err)}")

            await asyncio.sleep(1.5)
            await waiting_message_search.delete()
        
    @staticmethod
    async def run():
        Bot.Client = await TelegramClient('bot', Bot.API_ID, Bot.API_HASH).start(bot_token=Bot.BOT_TOKEN)
        # Register event handlers
        Bot.Client.add_event_handler(Bot.start, events.NewMessage(pattern='/start'))
        Bot.Client.add_event_handler(Bot.handle_broadcast_command, events.NewMessage(pattern='/broadcast'))
        Bot.Client.add_event_handler(Bot.handle_settings_command, events.NewMessage(pattern='/settings'))
        Bot.Client.add_event_handler(Bot.handle_subscription_command, events.NewMessage(pattern='/subscription'))
        Bot.Client.add_event_handler(Bot.handle_help_command, events.NewMessage(pattern='/help'))
        Bot.Client.add_event_handler(Bot.handle_quality_command, events.NewMessage(pattern='/quality'))
        Bot.Client.add_event_handler(Bot.handle_core_command, events.NewMessage(pattern='/core'))
        Bot.Client.add_event_handler(Bot.handle_admin_command, events.NewMessage(pattern='/admin'))
        Bot.Client.add_event_handler(Bot.handle_stats_command, events.NewMessage(pattern='/stats'))
        Bot.Client.add_event_handler(Bot.callback_query_handler, events.CallbackQuery)
        Bot.Client.add_event_handler(Bot.handle_message, events.NewMessage)
            
        await Bot.Client.run_until_disconnected()   


Bot.initialize()
asyncio.run(Bot.run())
                    
#### Needs Optiization
# 1. in is_Local -> use rust or C , or a better algoritm
# 2. in finding the spotify link -> create a class named spotify, inside this class should be a proper filter for spotify link