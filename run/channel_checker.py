from .glob_variables import BotState
from run import GetParticipantsRequest, ChannelParticipantsSearch, ChatAdminRequiredError, Button
from .buttons import Buttons
from .messages import BotMessageHandler
from utils import db


async def is_user_in_channel(user_id, channel_usernames=None):
    if channel_usernames is None:
        channel_usernames = BotState.channel_usernames
    channels_user_is_not_in = []

    for channel_username in channel_usernames:
        channel = await BotState.BOT_CLIENT.get_entity(channel_username)
        offset = 0
        while True:
            try:
                participants = await BotState.BOT_CLIENT(GetParticipantsRequest(
                    channel,
                    ChannelParticipantsSearch(''),  # Search query, empty for all participants
                    offset=offset,  # Providing the offset
                    limit=10 ** 9,  # Adjust the limit as needed
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


def join_channel_button(channel_username):
    """
    Returns a Button object that, when clicked, directs users to join the specified channel.
    """
    return Button.url("Join Channel", f"https://t.me/{channel_username}")


async def respond_based_on_channel_membership(event, message_if_in_channels: str = None, buttons: str = None,
                                              channels_user_is_not_in: list = None):
    sender_name = event.sender.first_name
    user_id = event.sender_id
    buttons_if_in_channel = buttons

    channels_user_is_not_in = await is_user_in_channel(
        user_id) if channels_user_is_not_in is None else channels_user_is_not_in

    if channels_user_is_not_in != [] and (user_id not in BotState.ADMIN_USER_IDS):
        join_channel_buttons = [[join_channel_button(channel)] for channel in channels_user_is_not_in]
        join_channel_buttons.append(Buttons.continue_button)
        await BotMessageHandler.send_message(event,
                                             f"""Hey {sender_name}!👋 \n{BotMessageHandler.JOIN_CHANNEL_MESSAGE}""",
                                             buttons=join_channel_buttons)
    elif message_if_in_channels is not None or (user_id in BotState.ADMIN_USER_IDS):
        await BotMessageHandler.send_message(event, f"""{message_if_in_channels}""",
                                             buttons=buttons_if_in_channel)


async def handle_continue_in_membership_message(event):
    sender_name = event.sender.first_name
    user_id = event.sender_id
    channels_user_is_not_in = await is_user_in_channel(user_id)
    if channels_user_is_not_in != []:
        join_channel_buttons = [[join_channel_button(channel)] for channel in channels_user_is_not_in]
        join_channel_buttons.append(Buttons.continue_button)
        await BotMessageHandler.edit_message(event,
                                             f"""Hey {sender_name}!👋 \n{BotMessageHandler.JOIN_CHANNEL_MESSAGE}""",
                                             buttons=join_channel_buttons)
        await event.answer("⚠️ You need to join our channels to continue.")
    else:
        user_already_in_db = await db.check_username_in_database(user_id)
        if not user_already_in_db:
            await db.create_user_settings(user_id)
        await event.delete()
        await respond_based_on_channel_membership(event, f"""Hey {sender_name}!👋 \n{BotMessageHandler.start_message}""",
                                                  buttons=Buttons.main_menu_buttons)
