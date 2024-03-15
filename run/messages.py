from .glob_variables import BotState
from .buttons import Buttons

class BotMessageHandler:
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

UPDATE:
You now have the option to search the Spotify database by providing the song's title, lyrics, or any other pertinent details.

"""

    contact_creator_message = """Should you have any inquiries or require feedback, please do not hesitate to contact me. 🌐
>> @AdibNikjou"""

    search_result_message = """🎵 The following are the top search results that correspond to your query:
"""

    core_selection_message = """🎵 Choose Your Preferred Download Core 🎵

"""
    JOIN_CHANNEL_MESSAGE = """It seems you are not a member of our channel yet.
Please join to continue."""

    @staticmethod
    async def send_message_and_store_id(event, text, buttons=None):
        chat_id = event.chat_id
        user_id = event.sender_id
        if BotState.get_messages(user_id):
            BotState.initialize_user_state(user_id)
        message = await BotState.BOT_CLIENT.send_message(chat_id, text, buttons=buttons)
        BotState.set_messages(user_id,message)

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
                await BotState.BOT_CLIENT.edit_message(chat_id, message.id, message_text, buttons=buttons)
        else:
            await BotMessageHandler.send_message_and_store_id(event, message_text, buttons=buttons)
            