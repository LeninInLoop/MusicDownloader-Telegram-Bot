from utils import os, asyncio, time, load_dotenv
from utils import BroadcastManager, db, sanitize_query, is_file_voice
from plugins import SpotifyDownloader, ShazamHelper, X, Insta
from run import TelegramClient, events, Button, GetParticipantsRequest, ChannelParticipantsSearch
from run import ChatAdminRequiredError, MessageMediaDocument
from run import Buttons, messages, BotState

class Bot:

    admin_message_to_send = {}
    admin_broadcast = {}
    cancel_broadcast = {}
    send_to_specified_flag = {}
    messages = {}
    search_result = {}
    waiting_message = {}
    
    @staticmethod
    async def initialize():
        Bot.load_env_variables()
        Bot.initialize_spotify_downloader()
        await Bot.initialize_database()
        Bot.initialize_shazam()
        Bot.initialize_X()
        Bot.initialize_instagram()
        Bot.initialize_messages()
        Bot.initialize_buttons()
        await Bot.initialize_action_queries()
        
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

    # @classmethod
    # def initialize_first_globals(cls):
    #     # Initialize global variables here
    #     cls.channel_usernames = ["Spotify_yt_downloader"]

    # @classmethod
    # def initialize_second_globals(cls, user_id):
    #     """
    #     Initializes a set of global variables for a specific user.
    #     """
    #     cls.admin_message_to_send[user_id] = None
    #     cls.admin_broadcast[user_id] = False
    #     cls.cancel_broadcast[user_id] = False
    #     cls.send_to_specified_flag[user_id] = False
    #     cls.messages[user_id] = {}
    #     cls.search_result[user_id] = None
    #     cls.waiting_message[user_id] = None
        
    @staticmethod
    def initialize_spotify_downloader():
        SpotifyDownloader.initialize()

    @staticmethod
    async def initialize_database():
        await db.initialize_database()
        await db.reset_all_file_processing_flags()

    @staticmethod 
    def initialize_shazam():
        ShazamHelper.initialize()
        
    @staticmethod
    def initialize_X():
        X.initialize()
        
    @staticmethod
    def initialize_instagram():
        Insta.initialize()
        
    @classmethod
    def initialize_messages(cls):
        # Initialize messages here
        cls.start_message = messages.start_message
        cls.instruction_message = messages.instruction_message
        cls.contact_creator_message = messages.contact_creator_message
        cls.search_result_message = messages.search_result_message
        cls.core_selection_message = messages.core_selection_message
        cls.JOIN_CHANNEL_MESSAGE = messages.JOIN_CHANNEL_MESSAGE

    @classmethod
    def initialize_buttons(cls):
        # Initialize buttons here
        cls.main_menu_buttons = Buttons.main_menu_buttons
        cls.back_button = Buttons.back_button
        cls.setting_button = Buttons.setting_button
        cls.back_button_to_setting = Buttons.back_button_to_setting
        cls.quality_setting_buttons = Buttons.quality_setting_buttons
        cls.core_setting_buttons = Buttons.core_setting_buttons
        cls.subscription_setting_buttons = Buttons.subscription_setting_buttons
        cls.cancel_broadcast_button = Buttons.cancel_broadcast_button
        cls.admins_buttons  =  Buttons.admins_buttons
        cls.broadcast_options_buttons = Buttons.broadcast_options_buttons

    @staticmethod
    async def edit_quality_setting_message(e):
        user_settings = await db.get_user_settings(e.sender_id)
        if user_settings:
            music_quality = user_settings[0]
            message = f"Your Quality Setting:\nFormat: {music_quality['format']}\nQuality: {music_quality['quality']}\n\nQualities Available :"
        else:
            message = "No quality settings found."
        await Bot.edit_message(e, message, buttons=Bot.quality_setting_buttons)
        
    @staticmethod
    async def edit_core_setting_message(e):
        user_settings = await db.get_user_settings(e.sender_id)
        if user_settings:
            downloading_core = user_settings[1]
            message = Bot.core_selection_message + f"\nCore: {downloading_core}"
        else:
            message = Bot.core_selection_message + "\nNo core setting found."
        await Bot.edit_message(e, message, buttons=Bot.core_setting_buttons)

    @staticmethod
    async def edit_subscription_status_message(e):
        is_subscribed = await db.is_user_subscribed(e.sender_id)
        message = f"Join our community and stay updated with the latest news and features of our bot. Be the first to experience new enhancements and improvements!\nYour Subscription Status: {is_subscribed}"
        await Bot.edit_message(e, message, buttons=Bot.subscription_setting_buttons)
        
    @staticmethod
    async def respond_with_user_count(event):
        number_of_users = await db.count_all_user_ids()
        number_of_subscribed = await db.count_subscribed_users()
        number_of_unsubscribed = number_of_users - number_of_subscribed
        await event.respond(f"""Number of Users: {number_of_users}
Number of Subscribed Users: {number_of_subscribed}
Number of Unsubscribed Users: {number_of_unsubscribed}""")
        
    @classmethod
    async def initialize_action_queries(cls):
        # Mapping button actions to functions
        cls.button_actions = {
            b"membership/continue": lambda e: Bot.handle_continue_in_membership_message(e),
            b"instructions": lambda e: Bot.edit_message(e, Bot.instruction_message, buttons=Bot.back_button),
            b"contact_creator": lambda e: Bot.edit_message(e, Bot.contact_creator_message, buttons=Bot.back_button),
            b"back": lambda e: Bot.edit_message(e, f"Hey {e.sender.first_name}!👋\n {Bot.start_message}", buttons=Bot.main_menu_buttons),
            b"setting": lambda e: Bot.edit_message(e, "Settings :", buttons=Bot.setting_button),
            b"setting/back": lambda e: Bot.edit_message(e, "Settings :", buttons=Bot.setting_button),
            b"setting/quality": lambda e: asyncio.create_task(Bot.edit_quality_setting_message(e)),
            b"setting/quality/mp3/320": lambda e: Bot.change_music_quality(e, "mp3",   320),
            b"setting/quality/mp3/128": lambda e: Bot.change_music_quality(e, "mp3",   128),
            b"setting/quality/flac": lambda e: Bot.change_music_quality(e, "flac",   693),
            b"setting/core": lambda e: asyncio.create_task(Bot.edit_core_setting_message(e)),
            b"setting/core/auto": lambda e: Bot.change_downloading_core(e, "Auto"),
            b"setting/core/spotdl": lambda e: Bot.change_downloading_core(e, "SpotDL"),
            b"setting/core/youtubedl": lambda e: Bot.change_downloading_core(e, "YoutubeDL"),
            b"setting/subscription": lambda e: asyncio.create_task(Bot.edit_subscription_status_message(e)),
            b"setting/subscription/cancel": lambda e: asyncio.create_task(Bot.cancel_subscription(e)),
            b"setting/subscription/cancel/quite": lambda e: asyncio.create_task(Bot.cancel_subscription(e,quite=True)),
            b"setting/subscription/add": lambda e: asyncio.create_task(Bot.add_subscription(e)),
            b"cancel": lambda e: e.delete(),
            b"admin/cancel_broadcast": lambda e: Bot.set_admin_broadcast(e,False),
            b"admin/stats": lambda e: asyncio.create_task(Bot.respond_with_user_count(e)),
            b"admin/broadcast": lambda e: Bot.edit_message(e, "BroadCast Options: ", buttons=Bot.broadcast_options_buttons),
            b"admin/broadcast/all": lambda e: Bot.handle_broadcast(e,send_to_all=True),
            b"admin/broadcast/subs": lambda e: Bot.handle_broadcast(e,send_to_subs=True),
            b"admin/broadcast/specified": lambda e: Bot.handle_broadcast(e,send_to_specified=True),
            b"next_page": lambda e: Bot.next_page(e),
            b"prev_page": lambda e: Bot.prev_page(e)
            # Add other actions here
        }

    @staticmethod
    async def send_message_and_store_id(event, text, buttons=None):
        chat_id = event.chat_id
        user_id = event.sender_id
        if BotState.get_messages(user_id):
            BotState.initialize_user_state(user_id)
        message = await Bot.Client.send_message(chat_id, text, buttons=buttons)
        BotState.set_messages(user_id,message)
        # message_id = message.id
        # Bot.messages[user_id][str(chat_id)] = message_id # Store the message ID with the chat_id as the key

    @staticmethod
    async def edit_message(event, message_text, buttons=None):
        chat_id = event.chat_id
        user_id = event.sender_id
        if BotState.get_messages(user_id) :
            BotState.initialize_user_state(user_id)
        message = BotState.get_messages(user_id)
        if message is not None:
            if message.id:
                BotState.set_messages(user_id,message)
                await Bot.Client.edit_message(chat_id, message.id, message_text, buttons=buttons)
        else:
            await Bot.send_message_and_store_id(event, message_text, buttons=buttons)

    @staticmethod
    async def handle_continue_in_membership_message(event):
        sender_name = event.sender.first_name
        user_id = event.sender_id
        channels_user_is_not_in = await Bot.is_user_in_channel(user_id)
        if channels_user_is_not_in != []:
            join_channel_buttons = [[Bot.join_channel_button(channel)] for channel in channels_user_is_not_in]
            join_channel_buttons.append([Button.inline("Continue",data='membership/continue')])
            await Bot.edit_message(event,f"""Hey {sender_name}!👋 \n{Bot.JOIN_CHANNEL_MESSAGE}""", buttons=join_channel_buttons)
        else:
            user_settings = await db.get_user_settings(user_id)
            if user_settings[0] == None and user_settings[1] == None:
                await db.save_user_settings(user_id, db.default_music_quality, db.default_downloading_core)
            await Bot.edit_message(event,f"""Hey {sender_name}!👋 \n{Bot.start_message}""", buttons=Bot.main_menu_buttons)
            
    @staticmethod
    async def change_music_quality(event, format, quality):
        user_id = event.sender_id
        music_quality = {'format': format, 'quality': quality}
        await db.change_music_quality(user_id, music_quality)
        user_settings = await db.get_user_settings(user_id)
        music_quality = user_settings[0]
        await Bot.edit_message(event, f"Quality successfully changed. \nFormat: {music_quality['format']}\nQuality: {music_quality['quality']}", buttons=Bot.quality_setting_buttons)

    @staticmethod
    async def change_downloading_core(event, core):
        user_id = event.sender_id
        await db.change_downloading_core(user_id, core)
        user_settings = await db.get_user_settings(user_id)
        downloading_core = user_settings[1]
        await Bot.edit_message(event, f"Core successfully changed. \nCore: {downloading_core}", buttons=Bot.core_setting_buttons)

    @staticmethod
    async def cancel_subscription(event, quite: bool = False):
        user_id = event.sender_id
        if await db.is_user_subscribed(user_id):
            await db.remove_subscribed_user(user_id)
            if not quite:
                await Bot.edit_message(event, "You have successfully unsubscribed.", buttons=Bot.subscription_setting_buttons)
            else:
                await event.respond("You have successfully unsubscribed.\nYou Can Subscribe Any Time Using /subscribe command. :)")

    @staticmethod
    async def add_subscription(event):
        user_id = event.sender_id
        if not await db.is_user_subscribed(user_id):
            await db.add_subscribed_user(user_id)
            await Bot.edit_message(event, "You have successfully subscribed.", buttons=Bot.subscription_setting_buttons)

    @staticmethod
    async def set_admin_broadcast(event,broadcast: bool):
        user_id = event.sender_id
        Bot.cancel_broadcast[user_id] = not broadcast

    @staticmethod
    def join_channel_button(channel_username):
        """
        Returns a Button object that, when clicked, directs users to join the specified channel.
        """
        return Button.url("Join Channel", f"https://t.me/{channel_username}")
    
    @staticmethod
    async def is_user_in_channel(user_id, channel_usernames=None):
        if channel_usernames is None:
            channel_usernames = BotState.channel_usernames
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
    async def respond_based_on_channel_membership(event, message_if_in_channels:str = None, _buttons:str = None, channels_user_is_not_in:list = None):
        sender_name = event.sender.first_name
        user_id = event.sender_id
        buttons_if_in_channesl = _buttons
        
        channels_user_is_not_in = await Bot.is_user_in_channel(user_id) if channels_user_is_not_in == None else channels_user_is_not_in
        
        if channels_user_is_not_in != []:
            join_channel_buttons = [[Bot.join_channel_button(channel)] for channel in channels_user_is_not_in]
            join_channel_buttons.append([Button.inline("Continue",data='membership/continue')])
            await Bot.send_message_and_store_id(event ,f"""Hey {sender_name}!👋 \n{Bot.JOIN_CHANNEL_MESSAGE}""", buttons=join_channel_buttons)
        elif message_if_in_channels != None:
            await Bot.send_message_and_store_id(event,f"""{message_if_in_channels}""", buttons=buttons_if_in_channesl)
        
    @staticmethod
    async def handle_broadcast(e, send_to_all: bool = False, send_to_subs: bool = False, send_to_specified: bool = False):
        
        user_id = e.sender_id
        if user_id not in Bot.ADMIN_USER_IDS:
            return
        
        if send_to_specified:
            BotState.set_send_to_specified_flag(user_id , True)
            
        BotState.set_cancel_broadcast(user_id, False)
        BotState.set_admin_broadcast(user_id, True)
        if send_to_all:
            await BroadcastManager.add_all_users_to_temp()
            
        elif send_to_specified:
            await BroadcastManager.remove_all_users_from_temp()
            time = 60 
            time_to_send = await e.respond("Please enter the user_ids (comma-separated) within the next 60 seconds.",buttons=Bot.cancel_broadcast_button)

            for remaining_time in range(time-1, 0, -1):
                # Edit the message to show the new time
                await time_to_send.edit(f"You've Got {remaining_time} seconds to send the user ids seperated with:")
                if BotState.get_cancel_broadcast(user_id):
                    await time_to_send.edit("BroadCast Cancelled by User.", buttons = None)
                    BotState.set_send_to_specified_flag(user_id, False)
                    BotState.set_admin_message_to_send(user_id, None)
                    BotState.set_cancel_broadcast(user_id, False)
                    BotState.set_admin_broadcast(user_id, False)
                    return
                elif BotState.get_admin_message_to_send(user_id) != None:
                    break
                await asyncio.sleep(1)
            BotState.set_send_to_specified_flag(user_id, False) 
            try:
                parts = BotState.get_admin_message_to_send(user_id)
                parts = parts.message.replace(" ","").split(",")
                user_ids = [int(part) for part in parts] 
                for user_id in user_ids:
                    await BroadcastManager.add_user_to_temp(user_id)
            except:
                await time_to_send.edit("Invalid command format. Use user_id1,user_id2,...")
                BotState.set_admin_message_to_send(user_id, None)
                BotState.set_cancel_broadcast(user_id, False)
                BotState.set_admin_broadcast(user_id, False)
                return
            BotState.set_admin_message_to_send(user_id, None)
            
        time = 60 
        time_to_send = await e.respond(f"You've Got {time} seconds to send your message",buttons=Bot.cancel_broadcast_button)

        for remaining_time in range(time-1, 0, -1):
            # Edit the message to show the new time
            await time_to_send.edit(f"You've Got {remaining_time} seconds to send your message")
            if BotState.get_cancel_broadcast(user_id):
                await time_to_send.edit("BroadCast Cancelled by User.", buttons = None)
                break
            elif BotState.get_admin_message_to_send(user_id) != None:
                break
            await asyncio.sleep(1)
            
        if BotState.get_admin_message_to_send(user_id) == None and BotState.get_cancel_broadcast(user_id) != True:
            await e.respond("There is nothing to send")
            BotState.set_admin_broadcast(user_id, False)
            BotState.set_admin_message_to_send(user_id, None)
            await BroadcastManager.remove_all_users_from_temp()
            return
        
        cancel_subscription_button = Button.inline("Cancel Subscription", b"setting/subscription/cancel/quite")
        try:
            if not BotState.get_cancel_broadcast(user_id) and send_to_specified:
                await BroadcastManager.broadcast_message_to_temp_members(Bot.Client, BotState.get_admin_message_to_send(user_id))
                await e.respond("Broadcast initiated.")
            elif not BotState.get_cancel_broadcast(user_id) and send_to_subs:
                await BroadcastManager.broadcast_message_to_sub_members(Bot.Client, BotState.get_admin_message_to_send(user_id),cancel_subscription_button)
                await e.respond("Broadcast initiated.")
            elif not BotState.get_cancel_broadcast(user_id) and send_to_all:
                await BroadcastManager.broadcast_message_to_temp_members(Bot.Client, BotState.get_admin_message_to_send(user_id))
                await e.respond("Broadcast initiated.")
        except Exception as e:
            await e.respond(f"Broadcast Failed: {str(e)}")
            BotState.set_admin_broadcast(user_id, False)
            BotState.set_admin_message_to_send(user_id, None)
            await BroadcastManager.remove_all_users_from_temp()
                
        await BroadcastManager.remove_all_users_from_temp()
        BotState.set_admin_broadcast(user_id, False)
        BotState.set_admin_message_to_send(user_id, None)

    @staticmethod
    async def update_bot_version_user_season(event):
        user_id = event.sender_id 
        music_quality, downloading_core = await db.get_user_settings(user_id)
        if music_quality == None or downloading_core == None:
            await event.respond("We Have Updated The Bot, Please start Over using the /start command.")
            await db.set_user_updated_flag(user_id,0)
        await db.set_user_updated_flag(user_id,1)
    
    @staticmethod
    async def process_audio_file(event, user_id):
        await Bot.update_bot_version_user_season(event)
        if not await db.get_user_updated_flag(user_id):
            return

        if not user_id in Bot.messages:
            BotState.initialize_user_state(user_id)

        channels_user_is_not_in = await Bot.is_user_in_channel(event.sender_id)
        if channels_user_is_not_in != []:
            return await Bot.respond_based_on_channel_membership(event, None, None, channels_user_is_not_in)

        if BotState.get_admin_broadcast(user_id) and BotState.get_send_to_specified_flag(user_id):
            BotState.set_admin_message_to_send(user_id,event.message)
            return
        elif BotState.get_admin_broadcast(user_id):
            BotState.set_admin_message_to_send(user_id,event.message)
            return

        if BotState.get_search_result(user_id) is not None:
            message = BotState.get_search_result(user_id)
            await message.delete()
            BotState.set_search_result(user_id,None)

        waiting_message_search = await event.respond('⏳')
        process_file_message = await event.respond("Processing Your File ...")

        voice = await is_file_voice(event)
        
        if voice == 0 :
            await event.respond("Sorry I Can only process Audio/Text.")
            await waiting_message_search.delete()
            await process_file_message.delete()
            return
        
        file_path = await event.message.download_media(file=f"{ShazamHelper.voice_repository_dir}")
        Shazam_recognized = await ShazamHelper.recognize(file_path)
        if not Shazam_recognized:
            await waiting_message_search.delete()
            await process_file_message.delete()
            await event.respond("Sorry I Couldnt find any song that matches your Voice.")
            return

        sanitized_query = await sanitize_query(Shazam_recognized)
        if not sanitized_query:
            await waiting_message_search.delete()
            await event.respond("Sorry I Couldnt find any song that matches your Voice.")
            return

        await SpotifyDownloader.search_spotify_based_on_user_input(event, sanitized_query)
        song_pages = await db.get_user_song_dict(user_id)
        if all(not value for value in song_pages.values()):
            await waiting_message_search.delete()
            await event.respond("Sorry, I couldnt Find any music that matches your Search query.")
            return

        await db.set_current_page(user_id,1)
        page = 1
        button_list = [
            [Button.inline(f"🎧 {details['track_name']} - {details['artist']} 🎧 ({details['release_year']})", data=str(idx))]
            for idx, details in enumerate(song_pages[str(page)])
        ]
        if len(song_pages) > 1:
            button_list.append([Button.inline("Previous Page", b"prev_page"), Button.inline("Next Page", b"next_page")])
        button_list.append([Button.inline("Cancel", b"cancel")])

        try:
            BotState.set_search_result(user_id,await event.respond(Bot.search_result_message, buttons=button_list))
        except Exception as Err:
            await event.respond(f"Sorry There Was an Error Processing Your Request: {str(Err)}")
        
        await asyncio.sleep(1.5)
        await waiting_message_search.delete()

    @staticmethod
    async def process_spotify_link(event, user_id):
        await Bot.update_bot_version_user_season(event)
        if not await db.get_user_updated_flag(user_id):
            return

        if BotState.get_messages(user_id) == {}:
            BotState.initialize_user_state(user_id)

        channels_user_is_not_in = await Bot.is_user_in_channel(event.sender_id)
        if channels_user_is_not_in != []:
            return await Bot.respond_based_on_channel_membership(event, None, None, channels_user_is_not_in)

        if BotState.get_admin_broadcast(user_id) and BotState.get_send_to_specified_flag(user_id):
            BotState.set_admin_message_to_send(user_id,event.message)
            return
        elif BotState.get_admin_broadcast(user_id):
            BotState.set_admin_message_to_send(user_id,event.message)
            return

        BotState.set_waiting_message(user_id,await event.respond('⏳'))
        await SpotifyDownloader.extract_data_from_spotify_link(event, str(event.message.text))
        info_tuple = await SpotifyDownloader.download_and_send_spotify_info(Bot.Client, event)

        if not info_tuple:  # if getting info of the link failed
            waiting_message = BotState.get_waiting_message(user_id)
            await waiting_message.delete()
            return await event.respond("Sorry, There was a problem processing your request.")

    @staticmethod
    async def process_text_query(event, user_id):
        await Bot.update_bot_version_user_season(event)
        if not await db.get_user_updated_flag(user_id):
            return

        if BotState.get_messages(user_id) == {}:
            BotState.initialize_user_state(user_id)

        channels_user_is_not_in = await Bot.is_user_in_channel(event.sender_id)
        if channels_user_is_not_in != []:
            return await Bot.respond_based_on_channel_membership(event, None, None, channels_user_is_not_in)

        if BotState.get_admin_broadcast(user_id) and BotState.get_send_to_specified_flag(user_id):
            BotState.set_admin_message_to_send(user_id,event.message)
            return
        elif BotState.get_admin_broadcast(user_id):
            BotState.set_admin_message_to_send(user_id,event.message)
            return

        if len(event.message.text) > 33:
            return await event.respond("Your Search Query is too long. :(")

        if BotState.get_search_result(user_id) is not None:
            search_result = BotState.get_search_result(user_id)
            await search_result.delete()
            BotState.set_search_result(user_id, None)

        waiting_message_search = await event.respond('⏳')
        sanitized_query = await sanitize_query(event.message.text)
        if not sanitized_query:
            await event.respond("Your input was not valid. Please try again with a valid search term.")
            return

        await SpotifyDownloader.search_spotify_based_on_user_input(event, sanitized_query)
        song_pages = await db.get_user_song_dict(user_id)
        if not song_pages:
            await waiting_message_search.delete()
            await event.respond("Sorry, I couldnt Find any music that matches your Search query.")
            return

        await db.set_current_page(user_id,1)
        page = 1
        button_list = [
            [Button.inline(f"🎧 {details['track_name']} - {details['artist']} 🎧 ({details['release_year']})", data=str(idx))]
            for idx, details in enumerate(song_pages[str(page)])
        ]
        if len(song_pages) > 1:
            button_list.append([Button.inline("Previous Page", b"prev_page"), Button.inline("Next Page", b"next_page")])
        button_list.append([Button.inline("Cancel", b"cancel")])

        try:
            BotState.set_search_result(user_id,await event.respond(Bot.search_result_message, buttons=button_list))
        except Exception as Err:
            await event.respond(f"Sorry There Was an Error Processing Your Request: {str(Err)}")

        await asyncio.sleep(1.5)
        await waiting_message_search.delete()

    @staticmethod
    async def prev_page(event):
        user_id = event.sender_id
        song_pages = await db.get_user_song_dict(user_id)
        total_pages = len(song_pages)

        current_page = await db.get_current_page(user_id)
        page = max(1, current_page - 1)
        await db.set_current_page(user_id,page) # Update the current page

        button_list = [
            [Button.inline(f"🎧 {details['track_name']} - {details['artist']} 🎧 ({details['release_year']})", data=str(idx))]
            for idx, details in enumerate(song_pages[str(page)])
        ]
        if total_pages > 1:
            button_list.append([Button.inline("Previous Page", b"prev_page"), Button.inline("Next Page", b"next_page")])
        button_list.append([Button.inline("Cancel", b"cancel")])

        try:
            search_result = BotState.get_search_result(user_id)
            await search_result.edit(buttons=button_list)
            BotState.set_search_result(user_id,search_result)
        except KeyError:
            page = await db.get_current_page(user_id)
            button_list = [
            [Button.inline(f"🎧 {details['track_name']} - {details['artist']} 🎧 ({details['release_year']})", data=str(idx))]
            for idx, details in enumerate(song_pages[str(page)])
            ]
            if len(song_pages) > 1:
                button_list.append([Button.inline("Previous Page", b"prev_page"), Button.inline("Next Page", b"next_page")])
            button_list.append([Button.inline("Cancel", b"cancel")])

            try:
                BotState.set_search_result(user_id,await event.respond(Bot.search_result_message, buttons=button_list))
            except Exception as Err:
                await event.respond(f"Sorry There Was an Error Processing Your Request: {str(Err)}")
        except:
            pass
            
    @staticmethod
    async def next_page(event):
        user_id = event.sender_id
        song_pages = await db.get_user_song_dict(user_id)
        total_pages = len(song_pages)

        current_page = await db.get_current_page(user_id)
        page = min(total_pages, current_page + 1)
        await db.set_current_page(user_id,page)  # Update the current page

        button_list = [
            [Button.inline(f"🎧 {details['track_name']} - {details['artist']} 🎧 ({details['release_year']})", data=str(idx))]
            for idx, details in enumerate(song_pages[str(page)])
        ]
        if total_pages > 1:
            button_list.append([Button.inline("Previous Page", b"prev_page"), Button.inline("Next Page", b"next_page")])
        button_list.append([Button.inline("Cancel", b"cancel")])

        try:
            search_result = BotState.get_search_result(user_id)
            await search_result.edit(buttons=button_list)
            BotState.set_search_result(user_id,search_result)
        except KeyError:
            page = await db.get_current_page(user_id)
            button_list = [
            [Button.inline(f"🎧 {details['track_name']} - {details['artist']} 🎧 ({details['release_year']})", data=str(idx))]
            for idx, details in enumerate(song_pages[str(page)])
            ]
            if len(song_pages) > 1:
                button_list.append([Button.inline("Previous Page", b"prev_page"), Button.inline("Next Page", b"next_page")])
            button_list.append([Button.inline("Cancel", b"cancel")])

            try:
                BotState.set_search_result(user_id,await event.respond(Bot.search_result_message, buttons=button_list))
            except Exception as Err:
                await event.respond(f"Sorry There Was an Error Processing Your Request: {str(Err)}")
        except:
            pass
        
    @staticmethod
    async def process_x_or_twitter_link(event):
        user_id = event.sender_id
        await Bot.update_bot_version_user_season(event)
        if not await db.get_user_updated_flag(user_id):
            return

        if BotState.get_messages(user_id) == {}:
            BotState.initialize_user_state(user_id)

        channels_user_is_not_in = await Bot.is_user_in_channel(user_id)
        if channels_user_is_not_in != []:
            return await Bot.respond_based_on_channel_membership(event, None, None, channels_user_is_not_in)

        if BotState.get_admin_broadcast(user_id) and BotState.get_send_to_specified_flag(user_id):
            BotState.set_admin_message_to_send(user_id,event.message)
            return
        elif BotState.get_admin_broadcast(user_id):
            BotState.set_admin_message_to_send(user_id,event.message)
            return
        
        x_link = X.find_and_send_x_or_twitter_link(event.message.text)
        if x_link:
            await db.set_tweet_url(user_id,x_link)
            screenshot_path = await X.take_screenshot_of_tweet(event,x_link)
            has_media = await X.has_media(x_link)
            return await X.send_screenshot(Bot.Client, event, screenshot_path, has_media)
        
    @staticmethod
    async def start(event):
        sender_name = event.sender.first_name
        user_id = event.sender_id
        
        user_settings = await db.get_user_settings(user_id)
        if user_settings[0] == None and user_settings[1] == None:
            await db.save_user_settings(user_id, db.default_music_quality, db.default_downloading_core)
        await Bot.respond_based_on_channel_membership(event,f"""Hey {sender_name}!👋 \n{Bot.start_message}""", _buttons=Bot.main_menu_buttons)
        
    @staticmethod
    async def handle_broadcast_command(event):
        # ... implementation of the handle_*_command methods ...
        
        user_id = event.sender_id
        if user_id not in Bot.ADMIN_USER_IDS:
                    return
                
        BotState.set_cancel_broadcast(user_id, False)
        BotState.set_admin_broadcast(user_id, True)
        if event.message.text.startswith('/broadcast_to_all'):
            await BroadcastManager.add_all_users_to_temp()
            
        elif event.message.text.startswith('/broadcast'):
            command_parts = event.message.text.split(' ',  1)

            if len(command_parts) == 1:
                pass
            elif len(command_parts) <  2 or not command_parts[1].startswith('(') or not command_parts[1].endswith(')'):
                await event.respond("Invalid command format. Use /broadcast (user_id1,user_id2,...)")
                BotState.set_admin_broadcast(user_id, False)
                BotState.set_admin_message_to_send(user_id, None)
                return

            if len(command_parts) != 1:
                await BroadcastManager.remove_all_users_from_temp()
                user_ids_str = command_parts[1][1:-1]  # Remove the parentheses
                specified_user_ids = [int(user_id) for user_id in user_ids_str.split(',')]
                for user_id in specified_user_ids:
                    await BroadcastManager.add_user_to_temp(user_id)
            BotState.set_admin_message_to_send(user_id, None)
        time = 60 
        time_to_send = await event.respond(f"You've Got {time} seconds to send your message",buttons=Bot.cancel_broadcast_button)

        for remaining_time in range(time-1, 0, -1):
            # Edit the message to show the new time
            await time_to_send.edit(f"You've Got {remaining_time} seconds to send your message")
            if BotState.get_cancel_broadcast(user_id):
                await time_to_send.edit("BroadCast Cancelled by User.", buttons = None)
                break
            elif BotState.get_admin_message_to_send(user_id) != None:
                break
            await asyncio.sleep(1)
        
        # Check if the message is "/broadcast_to_all"
        if BotState.get_admin_message_to_send(user_id) == None and BotState.get_cancel_broadcast(user_id) != True:
            await event.respond("There is nothing to send")
            BotState.set_admin_broadcast(user_id, True)
            BotState.set_admin_message_to_send(user_id, None)
            await BroadcastManager.remove_all_users_from_temp()
            return
        
        cancel_subscription_button = Button.inline("Cancel Subscription To News", b"setting/subscription/cancel/quite")
        try:
            if not BotState.get_cancel_broadcast(user_id) and len(command_parts) != 1:
                await BroadcastManager.broadcast_message_to_temp_members(Bot.Client, BotState.get_admin_message_to_send(user_id))
                await event.respond("Broadcast initiated.")
            elif not BotState.get_cancel_broadcast(user_id) and len(command_parts) == 1:
                await BroadcastManager.broadcast_message_to_sub_members(Bot.Client, BotState.get_admin_message_to_send(user_id), cancel_subscription_button)
                await event.respond("Broadcast initiated.")
        except:
            try:
                if not BotState.get_cancel_broadcast(user_id):
                    await BroadcastManager.broadcast_message_to_temp_members(Bot.Client, BotState.get_admin_message_to_send(user_id))
                    await event.respond("Broadcast initiated.")
            except Exception as e:
                await event.respond(f"Broadcast Failed: {str(e)}")
                BotState.set_admin_broadcast(user_id, False)
                BotState.set_admin_message_to_send(user_id, None)
                await BroadcastManager.remove_all_users_from_temp()
                
        await BroadcastManager.remove_all_users_from_temp()
        BotState.set_admin_broadcast(user_id, False)
        BotState.set_admin_message_to_send(user_id, None)

    @staticmethod
    async def handle_settings_command(event):
        await Bot.update_bot_version_user_season(event)
        if await db.get_user_updated_flag(event.sender_id):
            await Bot.respond_based_on_channel_membership(event,"Settings :", _buttons=Bot.setting_button)
        
    @staticmethod
    async def handle_subscribe_command(event):
    # Check if the user is already subscribed
        await Bot.update_bot_version_user_season(event)
        user_id = event.sender_id
        if await db.get_user_updated_flag(user_id):
            if await db.is_user_subscribed(user_id):
                await Bot.respond_based_on_channel_membership(event,"You are already subscribed.")
                return
            await db.add_subscribed_user(user_id)
            await Bot.respond_based_on_channel_membership(event,"You have successfully subscribed.")

    @staticmethod
    async def handle_unsubscribe_command(event):
    # Check if the user is subscribed
        await Bot.update_bot_version_user_season(event)
        user_id = event.sender_id
        if await db.get_user_updated_flag(user_id):
            if not await db.is_user_subscribed(user_id):
                await Bot.respond_based_on_channel_membership(event,"You are not currently subscribed.")
                return
            await db.remove_subscribed_user(user_id)
            await Bot.respond_based_on_channel_membership(event,"You have successfully unsubscribed.")
    
    @staticmethod
    async def handle_help_command(event):
        await Bot.update_bot_version_user_season(event)
        user_id = event.sender_id
        if await db.get_user_updated_flag(user_id):
            await Bot.respond_based_on_channel_membership(event,Bot.instruction_message)

    @staticmethod
    async def handle_quality_command(event):
        await Bot.update_bot_version_user_season(event)
        user_id = event.sender_id
        if await db.get_user_updated_flag(user_id):
            user_setting = await db.get_user_settings(user_id)
            await Bot.respond_based_on_channel_membership(event, f"Your Quality Setting:\nFormat: {user_setting[0]['format']}\nQuality: {user_setting[0]['quality']}\n\nQualities Available :",
                            _buttons=Bot.quality_setting_buttons)
        
    @staticmethod
    async def handle_core_command(event):
        await Bot.update_bot_version_user_season(event)
        user_id = event.sender_id
        if await db.get_user_updated_flag(user_id):
            user_setting = await db.get_user_settings(user_id)
            await Bot.respond_based_on_channel_membership(event, Bot.core_selection_message+f"\nCore: {user_setting[1]}",
                            _buttons=Bot.core_setting_buttons)
        
    @staticmethod
    async def handle_admin_command(event):
        if event.sender_id not in Bot.ADMIN_USER_IDS:
            return
        await Bot.send_message_and_store_id(event,"Admin commands:", buttons=Bot.admins_buttons)

    @staticmethod
    async def handle_stats_command(event):
        if event.sender_id not in Bot.ADMIN_USER_IDS:
            return
        number_of_users = await db.count_all_user_ids()
        number_of_subscribed = await db.count_subscribed_users()
        number_of_unsubscribed = number_of_users - number_of_subscribed
        await event.respond(f"""Number of Users: {number_of_users}
Number of Subscribed Users: {number_of_subscribed}
Number of Unsubscribed Users: {number_of_unsubscribed}""")

    @staticmethod
    async def handle_ping_command(event):
        start_time = time.time()
        ping_message = await event.reply('Pong!')
        end_time = time.time()
        response_time = (end_time - start_time)*1000
        await ping_message.edit(f'Pong!\nResponse time: {response_time:3.3f} ms')
        
    @staticmethod
    async def handle_search_command(event):
        await Bot.update_bot_version_user_season(event)
        user_id = event.sender_id
        if await db.get_user_updated_flag(user_id):
            search_query = event.message.text[8:]
            
            if not search_query.strip():
                await event.respond("Please provide a search term after the /search command. \nOr simply send me everything you want to Search for.")
                return
            if Bot.search_result[user_id] != None:
                await Bot.search_result[user_id].delete()
                Bot.search_result[user_id] = None
                
            waiting_message_search = await event.respond('⏳')
            sanitized_query = await sanitize_query(search_query)
            if not sanitized_query:
                await event.respond("Your input was not valid. Please try again with a valid search term.")
                return

            await SpotifyDownloader.search_spotify_based_on_user_input(event,sanitized_query)
            song_dict = await db.get_user_song_dict(user_id)
            if all(not value for value in song_dict.values()):
                await waiting_message_search.delete()
                await event.respond("Sorry,I couldnt Find any music that matches your Search query.")
                return
            
            song_dict = await db.get_user_song_dict(user_id)
            button_list = [
                [Button.inline(f"🎧 {details['track_name']} - {details['artist']} 🎧 ({details['release_year']})", data=str(idx))]
                for idx, details in song_dict.items()
            ]

            button_list.append([Button.inline("Cancel", b"cancel")])

            try:
                Bot.search_result[user_id] = await event.respond(Bot.search_result_message, buttons=button_list)
            except Exception as Err:
                await event.respond(f"Sorry There Was an Error Processing Your Request: {str(Err)}")

            await asyncio.sleep(1.5)
            await waiting_message_search.delete()
    
    @staticmethod
    async def handle_user_info_command(event):
        await Bot.update_bot_version_user_season(event)
        
        user_id = event.sender_id
        if await db.get_user_updated_flag(user_id):
            username = f"@{event.sender.username}" if event.sender.username else "No username"
            first_name = event.sender.first_name
            last_name = event.sender.last_name if event.sender.last_name else "No last name"
            is_bot = event.sender.bot
            is_verified = event.sender.verified
            is_restricted = event.sender.restricted
            is_scam = event.sender.scam
            is_support = event.sender.support

            # Prepare the user information message
            user_info_message = f"""
    User Information:

    ID: {user_id}
    Username: {username}

    First Name: {first_name}
    Last Name: {last_name}

    Is Bot: {is_bot}
    Is Verified: {is_verified}
    Is Restricted: {is_restricted}
    Is Scam: {is_scam}
    Is Support: {is_support}

    """
        # Send the user information to the user
            await event.reply(user_info_message)

    @staticmethod
    async def handle_unavailable_feature(event):
        await event.answer("not available", alert=True)

    @staticmethod
    async def handle_music_callback(client, event):
        if event.data == b"@music_info_preview":
            await SpotifyDownloader.send_30s_preview(client, event)
        elif event.data == b"@music_artist_info":
            await SpotifyDownloader.send_artists_info(event)
        elif event.data == b"@music_icon":
            await SpotifyDownloader.send_music_icon(client, event)
        elif event.data == b"@music_lyrics":
            await SpotifyDownloader.send_music_lyrics(event)
        else:
            send_file_result = await SpotifyDownloader.download_spotify_file_and_send(client, event)
            if not send_file_result:
                await db.set_file_processing_flag(event.sender_id,0)
                await event.respond(f"Sorry, there was an error downloading the song.\nTry Using a Different Core.\nYou Can Change Your Core in the Settings or Simply Use This command to See Available Cores: /core")
    
    @staticmethod
    async def callback_query_handler(event):
        user_id = event.sender_id
        await Bot.update_bot_version_user_season(event)
        if not await db.get_user_updated_flag(user_id):
            return

        action = Bot.button_actions.get(event.data)
        if action:
            await action(event)
        elif event.data == b"@unavailable_feature":
            await Bot.handle_unavailable_feature(event)
        elif event.data == b"@X_download_media":
            await X.download(Bot.Client,event)
        elif event.data.startswith(b"@music"):
            await Bot.handle_music_callback(Bot.Client, event)
        elif event.data == b"@playlist_download_10":
            await SpotifyDownloader.download_playlist(Bot.Client, event)
        elif event.data.isdigit():
            song_pages = await db.get_user_song_dict(user_id)
            current_page = await db.get_current_page(user_id)
            song_index = str(event.data.decode('utf-8'))
            song_details = song_pages[str(current_page)][int(song_index)]
            spotify_link = song_details.get('spotify_link')
            if spotify_link:
                Bot.waiting_message[user_id] = await event.respond('⏳')
                await SpotifyDownloader.extract_data_from_spotify_link(event, spotify_link)
                send_info_result = await SpotifyDownloader.download_and_send_spotify_info(Bot.Client, event)
                if not send_info_result:
                    await event.respond(f"Sorry, there was an error downloading the song.\nTry Using a Different Core.\nYou Can Change Your Core in the Settings or Simply Use This command to See Available Cores: /core")
                if Bot.waiting_message.get(user_id, None) is not None:
                    await Bot.waiting_message[user_id].delete()
                await db.set_file_processing_flag(user_id, 0)

    @staticmethod
    async def handle_message(event):
        user_id = event.sender_id

        if isinstance(event.message.media, MessageMediaDocument):
            await Bot.process_audio_file(event, user_id)
        elif SpotifyDownloader.is_spotify_link(event.message.text):
            await Bot.process_spotify_link(event, user_id)
        elif X.contains_x_or_twitter_link(event.message.text):
            await Bot.process_x_or_twitter_link(event)
        elif Insta.is_instagram_url(event.message.text):
            link = Insta.extract_url(event.message.text)
            await Insta.download(Bot.Client, event, link)
        elif not event.message.text.startswith('/'):
            await Bot.process_text_query(event, user_id)

    @staticmethod
    async def run():
        Bot.Client = await TelegramClient('bot', Bot.API_ID, Bot.API_HASH).start(bot_token=Bot.BOT_TOKEN)
        # Register event handlers
        Bot.Client.add_event_handler(Bot.start, events.NewMessage(pattern='/start'))
        Bot.Client.add_event_handler(Bot.handle_broadcast_command, events.NewMessage(pattern='/broadcast'))
        Bot.Client.add_event_handler(Bot.handle_settings_command, events.NewMessage(pattern='/settings'))
        Bot.Client.add_event_handler(Bot.handle_subscribe_command, events.NewMessage(pattern='/subscribe'))
        Bot.Client.add_event_handler(Bot.handle_unsubscribe_command, events.NewMessage(pattern='/unsubscribe'))
        Bot.Client.add_event_handler(Bot.handle_help_command, events.NewMessage(pattern='/help'))
        Bot.Client.add_event_handler(Bot.handle_quality_command, events.NewMessage(pattern='/quality'))
        Bot.Client.add_event_handler(Bot.handle_core_command, events.NewMessage(pattern='/core'))
        Bot.Client.add_event_handler(Bot.handle_admin_command, events.NewMessage(pattern='/admin'))
        Bot.Client.add_event_handler(Bot.handle_stats_command, events.NewMessage(pattern='/stats'))
        Bot.Client.add_event_handler(Bot.handle_ping_command,events.NewMessage(pattern='/ping'))
        Bot.Client.add_event_handler(Bot.handle_search_command,events.NewMessage(pattern='/search'))
        Bot.Client.add_event_handler(Bot.handle_user_info_command,events.NewMessage(pattern='/user_info'))
        Bot.Client.add_event_handler(Bot.callback_query_handler, events.CallbackQuery)
        Bot.Client.add_event_handler(Bot.handle_message, events.NewMessage)
            
        await Bot.Client.run_until_disconnected()   

