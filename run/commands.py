from plugins import SpotifyDownloader
from utils import db, asyncio, BroadcastManager, time
from utils import sanitize_query
from .glob_variables import BotState
from .buttons import Buttons
from .messages import BotMessageHandler
from .channel_checker import respond_based_on_channel_membership
from .version_checker import update_bot_version_user_season

ADMIN_USER_IDS = BotState.ADMIN_USER_IDS
BOT_CLIENT = BotState.BOT_CLIENT


class BotCommandHandler:

    @staticmethod
    async def start(event):
        sender_name = event.sender.first_name
        user_id = event.sender_id

        user_already_in_db = await db.check_username_in_database(user_id)
        if not user_already_in_db:
            await db.create_user_settings(user_id)
        await respond_based_on_channel_membership(event, f"""Hey {sender_name}!👋 \n{BotMessageHandler.start_message}""",
                                                  buttons=Buttons.main_menu_buttons)

    @staticmethod
    async def handle_stats_command(event):
        if event.sender_id not in ADMIN_USER_IDS:
            return
        number_of_users = await db.count_all_user_ids()
        number_of_subscribed = await db.count_subscribed_users()
        number_of_unsubscribed = number_of_users - number_of_subscribed
        await event.respond(f"""Number of Users: {number_of_users}
Number of Subscribed Users: {number_of_subscribed}
Number of Unsubscribed Users: {number_of_unsubscribed}""")

    @staticmethod
    async def handle_admin_command(event):
        if event.sender_id not in ADMIN_USER_IDS:
            return
        await BotMessageHandler.send_message(event, "Admin commands:", buttons=Buttons.admins_buttons)

    @staticmethod
    async def handle_ping_command(event):
        start_time = time.time()
        ping_message = await event.reply('Pong!')
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        await ping_message.edit(f'Pong!\nResponse time: {response_time:3.3f} ms')

    @staticmethod
    async def handle_core_command(event):
        if await update_bot_version_user_season(event):
            user_id = event.sender_id
            downloading_core = await db.get_user_downloading_core(user_id)
            await respond_based_on_channel_membership(event,
                                                      BotMessageHandler.core_selection_message + f"\nCore: {downloading_core}",
                                                      buttons=Buttons.get_core_setting_buttons(downloading_core))

    @staticmethod
    async def handle_quality_command(event):
        if await update_bot_version_user_season(event):
            user_id = event.sender_id
            music_quality = await db.get_user_music_quality(user_id)
            await respond_based_on_channel_membership(event,
                                                      f"Your Quality Setting:\nFormat: {music_quality['format']}\nQuality: {music_quality['quality']}\n\nQualities Available :",
                                                      buttons=Buttons.get_quality_setting_buttons(music_quality))

    @staticmethod
    async def handle_help_command(event):
        if await update_bot_version_user_season(event):
            user_id = event.sender_id
            if await db.get_user_updated_flag(user_id):
                await respond_based_on_channel_membership(event, BotMessageHandler.instruction_message,
                                                          buttons=Buttons.back_button)

    @staticmethod
    async def handle_unsubscribe_command(event):
        # Check if the user is subscribed
        if await update_bot_version_user_season(event):
            user_id = event.sender_id
            if not await db.is_user_subscribed(user_id):
                await respond_based_on_channel_membership(event, "You are not currently subscribed.")
                return
            await db.remove_subscribed_user(user_id)
            await respond_based_on_channel_membership(event, "You have successfully unsubscribed.")

    @staticmethod
    async def handle_subscribe_command(event):
        # Check if the user is already subscribed
        if await update_bot_version_user_season(event):
            user_id = event.sender_id
            if await db.is_user_subscribed(user_id):
                await respond_based_on_channel_membership(event, "You are already subscribed.")
                return
            await db.add_subscribed_user(user_id)
            await respond_based_on_channel_membership(event, "You have successfully subscribed.")

    @staticmethod
    async def handle_settings_command(event):
        if await update_bot_version_user_season(event):
            await respond_based_on_channel_membership(event, "Settings :", buttons=Buttons.setting_button)

    @staticmethod
    async def handle_broadcast_command(event):

        user_id = event.sender_id
        if user_id not in ADMIN_USER_IDS:
            return

        await BotState.set_admin_broadcast(user_id, True)
        if event.message.text.startswith('/broadcast_to_all'):
            await BroadcastManager.add_all_users_to_temp()

        elif event.message.text.startswith('/broadcast'):
            command_parts = event.message.text.split(' ', 1)

            if len(command_parts) == 1:
                pass
            elif len(command_parts) < 2 or not command_parts[1].startswith('(') or not command_parts[1].endswith(')'):
                await event.respond("Invalid command format. Use /broadcast (user_id1,user_id2,...)")
                await BotState.set_admin_broadcast(user_id, False)
                await BotState.set_admin_message_to_send(user_id, None)
                return

            if len(command_parts) != 1:
                await BroadcastManager.remove_all_users_from_temp()
                user_ids_str = command_parts[1][1:-1]  # Remove the parentheses
                specified_user_ids = [int(user_id) for user_id in user_ids_str.split(',')]
                for user_id in specified_user_ids:
                    await BroadcastManager.add_user_to_temp(user_id)
            await BotState.set_admin_message_to_send(user_id, None)
        time = 60
        time_to_send = await event.respond(f"You've Got {time} seconds to send your message",
                                           buttons=Buttons.cancel_broadcast_button)

        for remaining_time in range(time - 1, 0, -1):
            # Edit the message to show the new time
            await time_to_send.edit(f"You've Got {remaining_time} seconds to send your message")
            if not await BotState.get_admin_broadcast(user_id):
                await time_to_send.edit("BroadCast Cancelled by User.", buttons=None)
                break
            elif await BotState.get_admin_message_to_send(user_id) is not None:
                break
            await asyncio.sleep(1)

        # Check if the message is "/broadcast_to_all"
        if await BotState.get_admin_message_to_send(user_id) is None and await BotState.get_admin_broadcast(user_id):
            await event.respond("There is nothing to send")
            await BotState.set_admin_broadcast(user_id, False)
            await BotState.set_admin_message_to_send(user_id, None)
            await BroadcastManager.remove_all_users_from_temp()
            return

        try:
            if await BotState.get_admin_broadcast(user_id) and len(command_parts) != 1:
                await BroadcastManager.broadcast_message_to_temp_members(BOT_CLIENT,
                                                                         await BotState.get_admin_message_to_send(
                                                                             user_id))
                await event.respond("Broadcast initiated.")
            elif await BotState.get_admin_broadcast(user_id) and len(command_parts) == 1:
                await BroadcastManager.broadcast_message_to_sub_members(BOT_CLIENT,
                                                                        await BotState.get_admin_message_to_send(
                                                                            user_id),
                                                                        Buttons.cancel_subscription_button_quite)
                await event.respond("Broadcast initiated.")
        except:
            try:
                if await BotState.get_admin_broadcast(user_id):
                    await BroadcastManager.broadcast_message_to_temp_members(BOT_CLIENT,
                                                                             await BotState.get_admin_message_to_send(
                                                                                 user_id))
                    await event.respond("Broadcast initiated.")
            except Exception as e:
                await event.respond(f"Broadcast Failed: {str(e)}")
                await BotState.set_admin_broadcast(user_id, False)
                await BotState.set_admin_message_to_send(user_id, None)
                await BroadcastManager.remove_all_users_from_temp()

        await BroadcastManager.remove_all_users_from_temp()
        await BotState.set_admin_broadcast(user_id, False)
        await BotState.set_admin_message_to_send(user_id, None)

    @staticmethod
    async def handle_search_command(event):
        if not await update_bot_version_user_season(event):
            return event.respond("We have updated the bot.\n"
                                 "please start over using /start command.")

        search_query = event.message.text[8:]

        if not search_query.strip():
            await event.respond(
                "Please provide a search term after the /search command. \nOr simply send me everything you want "
                "to Search for.")
            return

        waiting_message_search = await event.respond('⏳')
        sanitized_query = await sanitize_query(search_query)
        if not sanitized_query:
            await event.respond("Your input was not valid. Please try again with a valid search term.")
            return

        search_result = await SpotifyDownloader.search_spotify_based_on_user_input(sanitized_query)
        if len(search_result) == 0:
            await waiting_message_search.delete()
            await event.respond("Sorry, I couldnt Find any music that matches your Search query.")
            return

        button_list = Buttons.get_search_result_buttons(sanitized_query, search_result)

        try:
            await event.respond(BotMessageHandler.search_result_message, buttons=button_list)
        except Exception as Err:
            await event.respond(f"Sorry There Was an Error Processing Your Request: {str(Err)}")

        await asyncio.sleep(1.5)
        await waiting_message_search.delete()

    @staticmethod
    async def handle_user_info_command(event):
        if await update_bot_version_user_season(event):
            user_id = event.sender_id
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
