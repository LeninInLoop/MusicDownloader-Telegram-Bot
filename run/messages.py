from .glob_variables import BotState
from .buttons import Buttons
from utils import db, TweetCapture
from telethon.errors.rpcerrorlist import MessageNotModifiedError


class BotMessageHandler:
    start_message = """
Welcome to your **Music Downloader!** 🎧

Send me the name of a song or artist, and I'll find and send you the downloadable track. 🎶

To see what I can do, type: /help
Or simply click the Instructions button below. 👇
"""

    instruction_message = """
    🎧 **Music Downloader** 🎧
    ——————————————————
    **1.** Share the Spotify song link. 🔗
    **2.** Wait for the download confirmation. 📣
    **3.** I'll send you the song file when ready. 💾
    **4.** You can also send a voice message with a song sample. 
        I'll find the best match and send you the details. 🎤🔍📩
    **5.** Get music lyrics, artist info, and more Just ask. 📜👨‍🎤

    💡 **Tip**: Search by title, lyrics, or other details too!

    📸 **Instagram Downloader** 📸
    ——————————————————
    **1.** Send the Instagram post, Reel, or IGTV link. 🔗
    **2.** I'll start downloading the content. ⏳
    **3.** I'll send you the file when it's ready. 📤

    🐦 **TweetCapture** 🐦
    ——————————————————
    **1.** Provide the tweet link. 🔗
    **2.** I'll screenshot the tweet and start downloading. 📸
    **3.** I'll send you the screenshot when it's ready. 🖼️
    **4.** To download media content from the tweet,
        click the "Download Media" button after
        receiving the screenshot. 📥

    ——————————————————
    Use any service by following the instructions!
    If you have any questions,
     feel free to ask @adibnikjou.
        """

    search_result_message = """🎵 The following are the top search results that correspond to your query:
"""

    core_selection_message = """🎵 Choose Your Preferred Download Core 🎵

"""
    JOIN_CHANNEL_MESSAGE = """It seems you are not a member of our channel yet.
Please join to continue."""

    search_playlist_message = """The playlist contains these songs:"""

    @staticmethod
    async def send_message(event, text, buttons=None):
        chat_id = event.chat_id
        user_id = event.sender_id
        await BotState.initialize_user_state(user_id)
        await BotState.BOT_CLIENT.send_message(chat_id, text, buttons=buttons)

    @staticmethod
    async def edit_message(event, message_text, buttons=None):
        user_id = event.sender_id

        await BotState.initialize_user_state(user_id)
        try:
            await event.edit(message_text, buttons=buttons)
        except MessageNotModifiedError:
            pass

    @staticmethod
    async def edit_quality_setting_message(e):
        music_quality = await db.get_user_music_quality(e.sender_id)
        if music_quality:
            message = (f"Your Quality Setting:\nFormat: {music_quality['format']}\nQuality: {music_quality['quality']}"
                       f"\n\nAvailable Qualities :")
        else:
            message = "No quality settings found."
        await BotMessageHandler.edit_message(e, message, buttons=Buttons.get_quality_setting_buttons(music_quality))

    @staticmethod
    async def edit_core_setting_message(e):
        downloading_core = await db.get_user_downloading_core(e.sender_id)
        if downloading_core:
            message = BotMessageHandler.core_selection_message + f"\nCore: {downloading_core}"
        else:
            message = BotMessageHandler.core_selection_message + "\nNo core setting found."
        await BotMessageHandler.edit_message(e, message, buttons=Buttons.get_core_setting_buttons(downloading_core))

    @staticmethod
    async def edit_subscription_status_message(e):
        is_subscribed = await db.is_user_subscribed(e.sender_id)
        message = f"Subscription settings:\n\nYour Subscription Status: {is_subscribed}"
        await BotMessageHandler.edit_message(e, message,
                                             buttons=Buttons.get_subscription_setting_buttons(is_subscribed))

    @staticmethod
    async def edit_tweet_capture_setting_message(e):
        night_mode = await TweetCapture.get_settings(e.sender_id)
        mode = night_mode['night_mode']
        mode_to_show = "Light"
        match mode:
            case "1":
                mode_to_show = "Dark"
            case "2":
                mode_to_show = "Black"
        message = f"Tweet capture settings:\n\nYour Night Mode: {mode_to_show}"
        await BotMessageHandler.edit_message(e, message, buttons=Buttons.get_tweet_capture_setting_buttons(mode))
