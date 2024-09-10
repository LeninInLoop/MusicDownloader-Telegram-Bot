from utils import BroadcastManager, db, asyncio, sanitize_query, TweetCapture
from plugins import SpotifyDownloader, ShazamHelper, X, Insta, YoutubeDownloader
from run import events, Button, MessageMediaDocument, update_bot_version_user_season, is_user_in_channel, \
    handle_continue_in_membership_message
from run import Buttons, BotMessageHandler, BotState, BotCommandHandler, respond_based_on_channel_membership


class Bot:
    Client = None

    @staticmethod
    async def initialize():
        try:
            Bot.initialize_spotify_downloader()
            await Bot.initialize_database()
            Bot.initialize_shazam()
            Bot.initialize_x()
            Bot.initialize_instagram()
            Bot.initialize_youtube()
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
            print("Plugins: Shazam initialized.")
        except Exception as e:
            print(f"An error occurred while initializing Shazam helper: {str(e)}")

    @staticmethod
    def initialize_x():
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

    @staticmethod
    def initialize_youtube():
        try:
            YoutubeDownloader.initialize()
            print("Plugins: Youtube downloader initialized.")
        except Exception as e:
            print(f"An error occurred while initializing Youtube downloader: {str(e)}")

    @classmethod
    def initialize_messages(cls):
        # Initialize messages here
        cls.start_message = BotMessageHandler.start_message
        cls.instruction_message = BotMessageHandler.instruction_message
        cls.search_result_message = BotMessageHandler.search_result_message
        cls.core_selection_message = BotMessageHandler.core_selection_message
        cls.JOIN_CHANNEL_MESSAGE = BotMessageHandler.JOIN_CHANNEL_MESSAGE
        cls.search_playlist_message = BotMessageHandler.search_playlist_message

    @classmethod
    def initialize_buttons(cls):
        # Initialize buttons here
        cls.main_menu_buttons = Buttons.main_menu_buttons
        cls.back_button = Buttons.back_button
        cls.setting_button = Buttons.setting_button
        cls.back_button_to_setting = Buttons.back_button_to_setting
        cls.cancel_broadcast_button = Buttons.cancel_broadcast_button
        cls.admins_buttons = Buttons.admins_buttons
        cls.broadcast_options_buttons = Buttons.broadcast_options_buttons

    @classmethod
    async def initialize_action_queries(cls):
        # Mapping button actions to functions
        cls.button_actions = {
            b"membership/continue": lambda e: asyncio.create_task(handle_continue_in_membership_message(e)),
            b"instructions": lambda e: asyncio.create_task(
                BotMessageHandler.edit_message(e, Bot.instruction_message, buttons=Bot.back_button)),
            b"back": lambda e: asyncio.create_task(
                BotMessageHandler.edit_message(e, f"Hey {e.sender.first_name}!👋\n {Bot.start_message}",
                                               buttons=Bot.main_menu_buttons)),
            b"setting": lambda e: asyncio.create_task(
                BotMessageHandler.edit_message(e, "Settings :", buttons=Bot.setting_button)),
            b"setting/back": lambda e: asyncio.create_task(
                BotMessageHandler.edit_message(e, "Settings :", buttons=Bot.setting_button)),
            b"setting/quality": lambda e: asyncio.create_task(BotMessageHandler.edit_quality_setting_message(e)),
            b"setting/quality/mp3/320": lambda e: asyncio.create_task(Bot.change_music_quality(e, "mp3", "320")),
            b"setting/quality/mp3/128": lambda e: asyncio.create_task(Bot.change_music_quality(e, "mp3", "128")),
            b"setting/quality/flac": lambda e: asyncio.create_task(Bot.change_music_quality(e, "flac", "693")),
            b"setting/core": lambda e: asyncio.create_task(BotMessageHandler.edit_core_setting_message(e)),
            b"setting/core/auto": lambda e: asyncio.create_task(Bot.change_downloading_core(e, "Auto")),
            b"setting/core/spotdl": lambda e: asyncio.create_task(Bot.change_downloading_core(e, "SpotDL")),
            b"setting/core/youtubedl": lambda e: asyncio.create_task(Bot.change_downloading_core(e, "YoutubeDL")),
            b"setting/subscription": lambda e: asyncio.create_task(
                BotMessageHandler.edit_subscription_status_message(e)),
            b"setting/subscription/cancel": lambda e: asyncio.create_task(Bot.cancel_subscription(e)),
            b"setting/subscription/cancel/quite": lambda e: asyncio.create_task(Bot.cancel_subscription(e, quite=True)),
            b"setting/subscription/add": lambda e: asyncio.create_task(Bot.add_subscription(e)),
            b"setting/TweetCapture": lambda e: asyncio.create_task(
                BotMessageHandler.edit_tweet_capture_setting_message(e)),
            b"setting/TweetCapture/mode/0": lambda e: asyncio.create_task(Bot.change_tweet_capture_night_mode(e, "0")),
            b"setting/TweetCapture/mode/1": lambda e: asyncio.create_task(Bot.change_tweet_capture_night_mode(e, "1")),
            b"setting/TweetCapture/mode/2": lambda e: asyncio.create_task(Bot.change_tweet_capture_night_mode(e, "2")),
            b"cancel": lambda e: e.delete(),
            b"admin/cancel_broadcast": lambda e: asyncio.create_task(BotState.set_admin_broadcast(e.sender_id, False)),
            b"admin/stats": lambda e: asyncio.create_task(BotCommandHandler.handle_stats_command(e)),
            b"admin/broadcast": lambda e: asyncio.create_task(
                BotMessageHandler.edit_message(e, "BroadCast Options: ", buttons=Bot.broadcast_options_buttons)),
            b"admin/broadcast/all": lambda e: asyncio.create_task(Bot.handle_broadcast(e, send_to_all=True)),
            b"admin/broadcast/subs": lambda e: asyncio.create_task(Bot.handle_broadcast(e, send_to_subs=True)),
            b"admin/broadcast/specified": lambda e: asyncio.create_task(
                Bot.handle_broadcast(e, send_to_specified=True)),
            b"unavailable_feature": lambda e: asyncio.create_task(Bot.handle_unavailable_feature(e))
            # Add other actions here
        }

    @staticmethod
    async def change_music_quality(event, format, quality):
        user_id = event.sender_id
        music_quality = {'format': format, 'quality': quality}
        await db.set_user_music_quality(user_id, music_quality)
        await BotMessageHandler.edit_message(event,
                                             f"Quality successfully changed.\n\nFormat: {music_quality['format']}"
                                             f"\nQuality: {music_quality['quality']}",
                                             buttons=Buttons.get_quality_setting_buttons(music_quality))

    @staticmethod
    async def change_downloading_core(event, downloading_core):
        user_id = event.sender_id
        await db.set_user_downloading_core(user_id, downloading_core)
        await BotMessageHandler.edit_message(event, f"Core successfully changed.\n\nCore: {downloading_core}",
                                             buttons=Buttons.get_core_setting_buttons(downloading_core))

    @staticmethod
    async def change_tweet_capture_night_mode(event, mode: str):
        user_id = event.sender_id
        await TweetCapture.set_settings(user_id, {'night_mode': mode})
        mode_to_show = "Light"
        match mode:
            case "1":
                mode_to_show = "Dark"
            case "2":
                mode_to_show = "Black"
        await BotMessageHandler.edit_message(event, f"Night mode successfully changed.\n\nNight mode: {mode_to_show}",
                                             buttons=Buttons.get_tweet_capture_setting_buttons(mode))

    @staticmethod
    async def cancel_subscription(event, quite: bool = False):
        user_id = event.sender_id
        if await db.is_user_subscribed(user_id):
            await db.remove_subscribed_user(user_id)
            if not quite:
                await BotMessageHandler.edit_message(event, "You have successfully unsubscribed.",
                                                     buttons=Buttons.get_subscription_setting_buttons(
                                                         subscription=False))
            else:
                await event.respond(
                    "You have successfully unsubscribed.\nYou Can Subscribe Any Time Using /subscribe command. :)")

    @staticmethod
    async def add_subscription(event):
        user_id = event.sender_id
        if not await db.is_user_subscribed(user_id):
            await db.add_subscribed_user(user_id)
            await BotMessageHandler.edit_message(event, "You have successfully subscribed.",
                                                 buttons=Buttons.get_subscription_setting_buttons(subscription=True))

    @staticmethod
    async def process_bot_interaction(event) -> bool:
        user_id = event.sender_id
        await update_bot_version_user_season(event)
        if not await db.get_user_updated_flag(user_id):
            return False

        channels_user_is_not_in = await is_user_in_channel(user_id)
        if channels_user_is_not_in != [] and (user_id not in BotState.ADMIN_USER_IDS):
            return await respond_based_on_channel_membership(event, None, None, channels_user_is_not_in)

        if await BotState.get_admin_broadcast(user_id) and await BotState.get_send_to_specified_flag(user_id):
            await BotState.set_admin_message_to_send(user_id, event.message)
            return False
        elif await BotState.get_admin_broadcast(user_id):
            await BotState.set_admin_message_to_send(user_id, event.message)
            return False
        return True

    @staticmethod
    async def handle_broadcast(e, send_to_all: bool = False, send_to_subs: bool = False,
                               send_to_specified: bool = False):

        user_id = e.sender_id
        if user_id not in BotState.ADMIN_USER_IDS:
            return

        if send_to_specified:
            await BotState.set_send_to_specified_flag(user_id, True)

        await BotState.set_admin_broadcast(user_id, True)
        if send_to_all:
            await BroadcastManager.add_all_users_to_temp()

        elif send_to_specified:
            await BroadcastManager.remove_all_users_from_temp()
            time = 60
            time_to_send = await e.respond("Please enter the user_ids (comma-separated) within the next 60 seconds.",
                                           buttons=Bot.cancel_broadcast_button)

            for remaining_time in range(time - 1, 0, -1):
                # Edit the message to show the new time
                await time_to_send.edit(f"You've Got {remaining_time} seconds to send the user ids seperated with:")
                if await BotState.get_admin_broadcast(user_id):
                    await time_to_send.edit("BroadCast Cancelled by User.", buttons=None)
                    await BotState.set_send_to_specified_flag(user_id, False)
                    await BotState.set_admin_message_to_send(user_id, None)
                    await BotState.set_admin_broadcast(user_id, False)
                    return
                elif await BotState.get_admin_message_to_send(user_id) is not None:
                    break
                await asyncio.sleep(1)
            await BotState.set_send_to_specified_flag(user_id, False)
            try:
                parts = await BotState.get_admin_message_to_send(user_id)
                parts = parts.message.replace(" ", "").split(",")
                user_ids = [int(part) for part in parts]
                for user_id in user_ids:
                    await BroadcastManager.add_user_to_temp(user_id)
            except:
                await time_to_send.edit("Invalid command format. Use user_id1,user_id2,...")
                await BotState.set_admin_message_to_send(user_id, None)
                await BotState.set_admin_broadcast(user_id, False)
                return
            await BotState.set_admin_message_to_send(user_id, None)

        time = 60
        time_to_send = await e.respond(f"You've Got {time} seconds to send your message",
                                       buttons=Bot.cancel_broadcast_button)

        for remaining_time in range(time - 1, 0, -1):
            # Edit the message to show the new time
            await time_to_send.edit(f"You've Got {remaining_time} seconds to send your message")
            if not await BotState.get_admin_broadcast(user_id):
                await time_to_send.edit("BroadCast Cancelled by User.", buttons=None)
                break
            elif await BotState.get_admin_message_to_send(user_id) is not None:
                break
            await asyncio.sleep(1)

        if await BotState.get_admin_message_to_send(user_id) is None and await BotState.get_admin_broadcast(user_id):
            await e.respond("There is nothing to send")
            await BotState.set_admin_broadcast(user_id, False)
            await BotState.set_admin_message_to_send(user_id, None)
            await BroadcastManager.remove_all_users_from_temp()
            return

        try:
            if await BotState.get_admin_broadcast(user_id) and send_to_specified:
                await BroadcastManager.broadcast_message_to_temp_members(Bot.Client,
                                                                         await BotState.get_admin_message_to_send(
                                                                             user_id))
                await e.respond("Broadcast initiated.")
            elif await BotState.get_admin_broadcast(user_id) and send_to_subs:
                await BroadcastManager.broadcast_message_to_sub_members(Bot.Client,
                                                                        await BotState.get_admin_message_to_send(
                                                                            user_id),
                                                                        Buttons.cancel_subscription_button_quite)
                await e.respond("Broadcast initiated.")
            elif await BotState.get_admin_broadcast(user_id) and send_to_all:
                await BroadcastManager.broadcast_message_to_temp_members(Bot.Client,
                                                                         await BotState.get_admin_message_to_send(
                                                                             user_id))
                await e.respond("Broadcast initiated.")
        except Exception as e:
            await e.respond(f"Broadcast Failed: {str(e)}")
            await BotState.set_admin_broadcast(user_id, False)
            await BotState.set_admin_message_to_send(user_id, None)
            await BroadcastManager.remove_all_users_from_temp()

        await BroadcastManager.remove_all_users_from_temp()
        await BotState.set_admin_broadcast(user_id, False)
        await BotState.set_admin_message_to_send(user_id, None)

    @staticmethod
    async def process_audio_file(event, user_id):
        if not await Bot.process_bot_interaction(event):
            return

        waiting_message_search = await event.respond('⏳')
        process_file_message = await event.respond("Processing Your File ...")

        file_path = await event.message.download_media(file=f"{ShazamHelper.voice_repository_dir}")
        shazam_recognized = await ShazamHelper.recognize(file_path)
        if not shazam_recognized:
            await waiting_message_search.delete()
            await process_file_message.delete()
            await event.respond("Sorry I Couldnt find any song that matches your Voice.")
            return

        sanitized_query = await sanitize_query(shazam_recognized)
        if not sanitized_query:
            await waiting_message_search.delete()
            await event.respond("Sorry I Couldnt find any song that matches your Voice.")
            return

        search_result = await SpotifyDownloader.search_spotify_based_on_user_input(sanitized_query, limit=10)
        button_list = Buttons.get_search_result_buttons(sanitized_query, search_result)

        try:
            await event.respond(Bot.search_result_message, buttons=button_list)
        except Exception as Err:
            await event.respond(f"Sorry There Was an Error Processing Your Request: {str(Err)}")

        await process_file_message.delete()
        await waiting_message_search.delete()

    @staticmethod
    async def process_spotify_link(event):
        if not await Bot.process_bot_interaction(event):
            return

        waiting_message = await event.respond('⏳')
        info_tuple = await SpotifyDownloader.download_and_send_spotify_info(event, is_query=False)

        if not info_tuple:  # if getting info of the link failed
            await waiting_message.delete()
            return await event.respond("Sorry, There was a problem processing your request.")

    @staticmethod
    async def process_text_query(event):
        if not await Bot.process_bot_interaction(event):
            return

        if len(event.message.text) > 33:
            return await event.respond("Your Search Query is too long. :(")

        waiting_message_search = await event.respond('⏳')
        sanitized_query = await sanitize_query(event.message.text)
        if not sanitized_query:
            await event.respond("Your input was not valid. Please try again with a valid search term.")
            return

        search_result = await SpotifyDownloader.search_spotify_based_on_user_input(sanitized_query, limit=10)
        button_list = Buttons.get_search_result_buttons(sanitized_query, search_result)

        try:
            await event.respond(Bot.search_result_message, buttons=button_list)
        except Exception as Err:
            await event.respond(f"Sorry There Was an Error Processing Your Request: {str(Err)}")

        await waiting_message_search.delete()

    @staticmethod
    async def handle_next_prev_page(event):
        query_data = str(event.data)
        is_playlist = True if query_data.split("/")[1] == "p" else False
        current_page = query_data.split("/page/")[-1][:-1]

        search_query = query_data.split("/")[2]

        if current_page == "0" or (current_page == "6" and is_playlist):
            return await event.answer("⚠️ Not available.")

        if is_playlist:
            search_result = await SpotifyDownloader.get_playlist_tracks(search_query,
                                                                        limit=int(current_page) * 10)
            button_list = Buttons.get_playlist_search_buttons(search_query, search_result, page=int(current_page))
        else:
            search_result = await SpotifyDownloader.search_spotify_based_on_user_input(search_query,
                                                                                       limit=int(current_page) * 10)
            button_list = Buttons.get_search_result_buttons(search_query, search_result, page=int(current_page))

        try:
            await event.edit(buttons=button_list)
        except:
            await event.answer("⚠️ Not available.")

    @staticmethod
    async def process_x_or_twitter_link(event):
        if not await Bot.process_bot_interaction(event):
            return

        x_link = X.find_and_return_x_or_twitter_link(event.message.text)
        if x_link:
            return await X.send_screenshot(Bot.Client, event, x_link)

    @staticmethod
    async def process_youtube_link(event):
        if not await Bot.process_bot_interaction(event):
            return

        waiting_message = await event.respond('⏳')

        youtube_link = YoutubeDownloader.extract_youtube_url(event.message.text)
        if not youtube_link:
            return await event.respond("Sorry, Bad Youtube Link.")
        await YoutubeDownloader.send_youtube_info(Bot.Client, event, youtube_link)
        await waiting_message.delete()

    @staticmethod
    async def handle_unavailable_feature(event):
        await event.answer("not available", alert=True)

    @staticmethod
    async def search_inside_playlist(event):

        query_data = str(event.data)
        playlist_id = query_data.split("/playlist/")[-1][:-1]

        waiting_message_search = await event.respond('⏳')
        search_result = await SpotifyDownloader.get_playlist_tracks(playlist_id)
        button_list = Buttons.get_playlist_search_buttons(playlist_id, search_result)

        try:
            await event.respond(Bot.search_result_message, buttons=button_list)
        except Exception as Err:
            await event.respond(f"Sorry There Was an Error Processing Your Request: {str(Err)}")

        await asyncio.sleep(1.5)
        await waiting_message_search.delete()

    @staticmethod
    async def handle_spotify_callback(event):
        handlers = {
            "spotify/dl/icon/": SpotifyDownloader.send_music_icon,
            "spotify/dl/30s_preview": SpotifyDownloader.send_30s_preview,
            "spotify/artist/": SpotifyDownloader.send_artists_info,
            "spotify/lyrics": SpotifyDownloader.send_music_lyrics,
            "spotify/dl/playlist/": SpotifyDownloader.download_spotify_file_and_send,
            "spotify/s/playlist/": Bot.search_inside_playlist,
            "spotify/dl/music/": SpotifyDownloader.download_spotify_file_and_send,
            "spotify/info/": SpotifyDownloader.download_and_send_spotify_info,
        }

        for key, handler in handlers.items():
            if event.data.startswith(key.encode()):
                await handler(event)
                break
        else:
            pass

    @staticmethod
    async def handle_youtube_callback(client, event):
        if event.data.startswith(b"yt/dl/"):
            await YoutubeDownloader.download_and_send_yt_file(client, event)

    @staticmethod
    async def handle_x_callback(client, event):
        if event.data.startswith(b"X/dl"):
            await X.download(client, event)
        else:
            pass  # Add another x callbacks here

    @staticmethod
    async def callback_query_handler(event):
        user_id = event.sender_id
        await update_bot_version_user_season(event)
        if not await db.get_user_updated_flag(user_id):
            return

        action = Bot.button_actions.get(event.data)
        if action:
            await action(event)
        elif event.data.startswith(b"spotify"):
            await Bot.handle_spotify_callback(event)
        elif event.data.startswith(b"yt"):
            await Bot.handle_youtube_callback(Bot.Client, event)
        elif event.data.startswith(b"X"):
            await Bot.handle_x_callback(Bot.Client, event)
        elif event.data.startswith(b"next_page") or event.data.startswith(b"prev_page"):
            await Bot.handle_next_prev_page(event)
        else:
            pass

    @staticmethod
    async def handle_message(event):
        user_id = event.sender_id

        if isinstance(event.message.media, MessageMediaDocument):
            if event.message.media.voice:
                await Bot.process_audio_file(event, user_id)
            else:
                await event.respond("Sorry, I can only process:\n-Text\n-Voice\n-Link")
        elif YoutubeDownloader.is_youtube_link(event.message.text):
            await Bot.process_youtube_link(event)
        elif SpotifyDownloader.is_spotify_link(event.message.text):
            await Bot.process_spotify_link(event)
        elif X.contains_x_or_twitter_link(event.message.text):
            await Bot.process_x_or_twitter_link(event)
        elif Insta.is_instagram_url(event.message.text):
            await Insta.download(Bot.Client, event)
        elif not event.message.text.startswith('/'):
            await Bot.process_text_query(event)

    @staticmethod
    async def run():
        Bot.Client = await BotState.BOT_CLIENT.start(bot_token=BotState.BOT_TOKEN)

        # Register event handlers
        Bot.Client.add_event_handler(BotCommandHandler.start, events.NewMessage(pattern='/start'))

        Bot.Client.add_event_handler(BotCommandHandler.handle_broadcast_command,
                                     events.NewMessage(pattern='/broadcast'))

        Bot.Client.add_event_handler(BotCommandHandler.handle_settings_command, events.NewMessage(pattern='/settings'))

        Bot.Client.add_event_handler(BotCommandHandler.handle_subscribe_command,
                                     events.NewMessage(pattern='/subscribe'))

        Bot.Client.add_event_handler(BotCommandHandler.handle_unsubscribe_command,
                                     events.NewMessage(pattern='/unsubscribe'))

        Bot.Client.add_event_handler(BotCommandHandler.handle_help_command, events.NewMessage(pattern='/help'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_quality_command, events.NewMessage(pattern='/quality'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_core_command, events.NewMessage(pattern='/core'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_admin_command, events.NewMessage(pattern='/admin'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_stats_command, events.NewMessage(pattern='/stats'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_ping_command, events.NewMessage(pattern='/ping'))
        Bot.Client.add_event_handler(BotCommandHandler.handle_search_command, events.NewMessage(pattern='/search'))

        Bot.Client.add_event_handler(BotCommandHandler.handle_user_info_command,
                                     events.NewMessage(pattern='/user_info'))

        Bot.Client.add_event_handler(Bot.callback_query_handler, events.CallbackQuery)
        Bot.Client.add_event_handler(Bot.handle_message, events.NewMessage)

        await Bot.Client.run_until_disconnected()
