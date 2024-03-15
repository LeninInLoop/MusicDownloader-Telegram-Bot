from utils import BroadcastManager, db, asyncio, sanitize_query, is_file_voice
from plugins import SpotifyDownloader, ShazamHelper, X, Insta
from run import events, Button, MessageMediaDocument, update_bot_version_user_season, is_user_in_channel, handle_continue_in_membership_message
from run import Buttons, BotMessageHandler, BotState, BotCommandHandler, respond_based_on_channel_membership


class Bot:
    
    @staticmethod
    async def initialize():
        try:
            Bot.initialize_spotify_downloader()
            await Bot.initialize_database()
            Bot.initialize_shazam()
            Bot.initialize_X()
            Bot.initialize_instagram()
            Bot.initialize_messages()
            Bot.initialize_buttons()
            await Bot.initialize_action_queries()
            print("Bot initialization completed successfully.")
        except Exception as e:
            print(f"An error occurred during bot initialization: {str(e)}")

    @staticmethod
    def initialize_spotify_downloader():
        try:
            SpotifyDownloader.initialize()
            print("Plugins: Spotify downloader initialized.")
        except Exception as e:
            print(f"An error occurred while initializing Spotify downloader: {str(e)}")

    @staticmethod
    async def initialize_database():
        try:
            await db.initialize_database()
            await db.reset_all_file_processing_flags()
            print("Utils: Database initialized and file processing flags reset.")
        except Exception as e:
            print(f"An error occurred while initializing the database: {str(e)}")

    @staticmethod 
    def initialize_shazam():
        try:
            ShazamHelper.initialize()
            print("Plugins: Shazam helper initialized.")
        except Exception as e:
            print(f"An error occurred while initializing Shazam helper: {str(e)}")

    @staticmethod
    def initialize_X():
        try:
            X.initialize()
            print("Plugins: X initialized.")
        except Exception as e:
            print(f"An error occurred while initializing X: {str(e)}")

    @staticmethod
    def initialize_instagram():
        try:
            Insta.initialize()
            print("Plugins: Instagram initialized.")
        except Exception as e:
            print(f"An error occurred while initializing Instagram: {str(e)}")

    @classmethod
    def initialize_messages(cls):
        # Initialize messages here
        cls.start_message = BotMessageHandler.start_message
        cls.instruction_message = BotMessageHandler.instruction_message
        cls.contact_creator_message = BotMessageHandler.contact_creator_message
        cls.search_result_message = BotMessageHandler.search_result_message
        cls.core_selection_message = BotMessageHandler.core_selection_message
        cls.JOIN_CHANNEL_MESSAGE = BotMessageHandler.JOIN_CHANNEL_MESSAGE

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
        
    @classmethod
    async def initialize_action_queries(cls):
        # Mapping button actions to functions
        cls.button_actions = {
            b"membership/continue": lambda e: handle_continue_in_membership_message(e),
            b"instructions": lambda e: BotMessageHandler.edit_message(e, Bot.instruction_message, buttons=Bot.back_button),
            b"contact_creator": lambda e: BotMessageHandler.edit_message(e, Bot.contact_creator_message, buttons=Bot.back_button),
            b"back": lambda e: BotMessageHandler.edit_message(e, f"Hey {e.sender.first_name}!👋\n {Bot.start_message}", buttons=Bot.main_menu_buttons),
            b"setting": lambda e: BotMessageHandler.edit_message(e, "Settings :", buttons=Bot.setting_button),
            b"setting/back": lambda e: BotMessageHandler.edit_message(e, "Settings :", buttons=Bot.setting_button),
            b"setting/quality": lambda e: asyncio.create_task(BotMessageHandler.edit_quality_setting_message(e)),
            b"setting/quality/mp3/320": lambda e: Bot.change_music_quality(e, "mp3",   320),
            b"setting/quality/mp3/128": lambda e: Bot.change_music_quality(e, "mp3",   128),
            b"setting/quality/flac": lambda e: Bot.change_music_quality(e, "flac",   693),
            b"setting/core": lambda e: asyncio.create_task(BotMessageHandler.edit_core_setting_message(e)),
            b"setting/core/auto": lambda e: Bot.change_downloading_core(e, "Auto"),
            b"setting/core/spotdl": lambda e: Bot.change_downloading_core(e, "SpotDL"),
            b"setting/core/youtubedl": lambda e: Bot.change_downloading_core(e, "YoutubeDL"),
            b"setting/subscription": lambda e: asyncio.create_task(BotMessageHandler.edit_subscription_status_message(e)),
            b"setting/subscription/cancel": lambda e: asyncio.create_task(Bot.cancel_subscription(e)),
            b"setting/subscription/cancel/quite": lambda e: asyncio.create_task(Bot.cancel_subscription(e,quite=True)),
            b"setting/subscription/add": lambda e: asyncio.create_task(Bot.add_subscription(e)),
            b"cancel": lambda e: e.delete(),
            b"admin/cancel_broadcast": lambda e: BotState.set_admin_broadcast(e.sender_id,False),
            b"admin/stats": lambda e: asyncio.create_task(BotCommandHandler.handle_stats_command(e)),
            b"admin/broadcast": lambda e: BotMessageHandler.edit_message(e, "BroadCast Options: ", buttons=Bot.broadcast_options_buttons),
            b"admin/broadcast/all": lambda e: Bot.handle_broadcast(e,send_to_all=True),
            b"admin/broadcast/subs": lambda e: Bot.handle_broadcast(e,send_to_subs=True),
            b"admin/broadcast/specified": lambda e: Bot.handle_broadcast(e,send_to_specified=True),
            b"next_page": lambda e: Bot.next_page(e),
            b"prev_page": lambda e: Bot.prev_page(e)
            # Add other actions here
        }

    @staticmethod
    async def change_music_quality(event, format, quality):
        user_id = event.sender_id
        music_quality = {'format': format, 'quality': quality}
        await db.change_music_quality(user_id, music_quality)
        user_settings = await db.get_user_settings(user_id)
        music_quality = user_settings[0]
        await BotMessageHandler.edit_message(event, f"Quality successfully changed. \nFormat: {music_quality['format']}\nQuality: {music_quality['quality']}", buttons=Bot.quality_setting_buttons)

    @staticmethod
    async def change_downloading_core(event, core):
        user_id = event.sender_id
        await db.change_downloading_core(user_id, core)
        user_settings = await db.get_user_settings(user_id)
        downloading_core = user_settings[1]
        await BotMessageHandler.edit_message(event, f"Core successfully changed. \nCore: {downloading_core}", buttons=Bot.core_setting_buttons)

    @staticmethod
    async def cancel_subscription(event, quite: bool = False):
        user_id = event.sender_id
        if await db.is_user_subscribed(user_id):
            await db.remove_subscribed_user(user_id)
            if not quite:
                await BotMessageHandler.edit_message(event, "You have successfully unsubscribed.", buttons=Bot.subscription_setting_buttons)
            else:
                await event.respond("You have successfully unsubscribed.\nYou Can Subscribe Any Time Using /subscribe command. :)")

    @staticmethod
    async def add_subscription(event):
        user_id = event.sender_id
        if not await db.is_user_subscribed(user_id):
            await db.add_subscribed_user(user_id)
            await BotMessageHandler.edit_message(event, "You have successfully subscribed.", buttons=Bot.subscription_setting_buttons) 

    @staticmethod
    async def handle_broadcast(e, send_to_all: bool = False, send_to_subs: bool = False, send_to_specified: bool = False):
        
        user_id = e.sender_id
        if user_id not in BotState.ADMIN_USER_IDS:
            return
        
        if send_to_specified:
            BotState.set_send_to_specified_flag(user_id , True)
            
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
                if BotState.get_admin_broadcast(user_id):
                    await time_to_send.edit("BroadCast Cancelled by User.", buttons = None)
                    BotState.set_send_to_specified_flag(user_id, False)
                    BotState.set_admin_message_to_send(user_id, None)
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
                BotState.set_admin_broadcast(user_id, False)
                return
            BotState.set_admin_message_to_send(user_id, None)
            
        time = 60 
        time_to_send = await e.respond(f"You've Got {time} seconds to send your message",buttons=Bot.cancel_broadcast_button)

        for remaining_time in range(time-1, 0, -1):
            # Edit the message to show the new time
            await time_to_send.edit(f"You've Got {remaining_time} seconds to send your message")
            if not BotState.get_admin_broadcast(user_id):
                await time_to_send.edit("BroadCast Cancelled by User.", buttons = None)
                break
            elif BotState.get_admin_message_to_send(user_id) != None:
                break
            await asyncio.sleep(1)
            
        if BotState.get_admin_message_to_send(user_id) == None and BotState.get_admin_broadcast(user_id):
            await e.respond("There is nothing to send")
            BotState.set_admin_broadcast(user_id, False)
            BotState.set_admin_message_to_send(user_id, None)
            await BroadcastManager.remove_all_users_from_temp()
            return
        
        try:
            if BotState.get_admin_broadcast(user_id) and send_to_specified:
                await BroadcastManager.broadcast_message_to_temp_members(Bot.Client, BotState.get_admin_message_to_send(user_id))
                await e.respond("Broadcast initiated.")
            elif BotState.get_admin_broadcast(user_id) and send_to_subs:
                await BroadcastManager.broadcast_message_to_sub_members(Bot.Client, BotState.get_admin_message_to_send(user_id), Buttons.cancel_subscription_button_quite)
                await e.respond("Broadcast initiated.")
            elif BotState.get_admin_broadcast(user_id) and send_to_all:
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
    async def process_audio_file(event, user_id):
        await update_bot_version_user_season(event)
        if not await db.get_user_updated_flag(user_id):
            return

        if BotState.get_messages(user_id) == {}:
            BotState.initialize_user_state(user_id)

        channels_user_is_not_in = await is_user_in_channel(event.sender_id)
        if channels_user_is_not_in != []:
            return await respond_based_on_channel_membership(event, None, None, channels_user_is_not_in)

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
        await update_bot_version_user_season(event)
        if not await db.get_user_updated_flag(user_id):
            return

        if BotState.get_messages(user_id) == {}:
            BotState.initialize_user_state(user_id)

        channels_user_is_not_in = await is_user_in_channel(event.sender_id)
        if channels_user_is_not_in != []:
            return await respond_based_on_channel_membership(event, None, None, channels_user_is_not_in)

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
        await update_bot_version_user_season(event)
        if not await db.get_user_updated_flag(user_id):
            return

        if BotState.get_messages(user_id) == {}:
            BotState.initialize_user_state(user_id)

        channels_user_is_not_in = await is_user_in_channel(event.sender_id)
        if channels_user_is_not_in != []:
            return await respond_based_on_channel_membership(event, None, None, channels_user_is_not_in)

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
        await update_bot_version_user_season(event)
        if not await db.get_user_updated_flag(user_id):
            return

        if BotState.get_messages(user_id) == {}:
            BotState.initialize_user_state(user_id)

        channels_user_is_not_in = await is_user_in_channel(user_id)
        if channels_user_is_not_in != []:
            return await respond_based_on_channel_membership(event, None, None, channels_user_is_not_in)

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
        await update_bot_version_user_season(event)
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
                BotState.set_waiting_message(user_id,await event.respond('⏳'))
                await SpotifyDownloader.extract_data_from_spotify_link(event, spotify_link)
                send_info_result = await SpotifyDownloader.download_and_send_spotify_info(Bot.Client, event)
                if not send_info_result:
                    await event.respond(f"Sorry, there was an error downloading the song.\nTry Using a Different Core.\nYou Can Change Your Core in the Settings or Simply Use This command to See Available Cores: /core")
                if BotState.get_waiting_message(user_id) is not None:
                    waiting_message = BotState.get_waiting_message(user_id)
                    await waiting_message.delete()
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
        Bot.Client = await BotState.BOT_CLIENT.start(bot_token=BotState.BOT_TOKEN)
        # Register event handlers
        Bot.Client.add_event_handler(BotCommandHandler.start , events.NewMessage(pattern='/start'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_broadcast_command, events.NewMessage(pattern='/broadcast'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_settings_command, events.NewMessage(pattern='/settings'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_subscribe_command, events.NewMessage(pattern='/subscribe'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_unsubscribe_command, events.NewMessage(pattern='/unsubscribe'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_help_command, events.NewMessage(pattern='/help'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_quality_command, events.NewMessage(pattern='/quality'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_core_command, events.NewMessage(pattern='/core'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_admin_command, events.NewMessage(pattern='/admin'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_stats_command, events.NewMessage(pattern='/stats'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_ping_command,events.NewMessage(pattern='/ping'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_search_command,events.NewMessage(pattern='/search'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_user_info_command,events.NewMessage(pattern='/user_info'))
        Bot.Client.add_event_handler(Bot.callback_query_handler, events.CallbackQuery)
        Bot.Client.add_event_handler(Bot.handle_message, events.NewMessage)
            
        await Bot.Client.run_until_disconnected()   

