from .glob_variables import BotState
from .buttons import Buttons
from utils import db, TweetCapture

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
**5.** Get music lyrics, artist info, and more! Just ask. 📜👨‍🎤

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
If you have any questions, feel free to ask @adibnikjou. 😊
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
        if message != {}:
            if message.id:
                BotState.set_messages(user_id,message)
                await BotState.BOT_CLIENT.edit_message(chat_id, message.id, message_text, buttons=buttons)
        else:
            await BotMessageHandler.send_message_and_store_id(event, message_text, buttons=buttons)
            
    @staticmethod
    async def edit_quality_setting_message(e):
        music_quality = await db.get_user_music_quality(e.sender_id)
        if music_quality:
            message = f"Your Quality Setting:\nFormat: {music_quality['format']}\nQuality: {music_quality['quality']}\n\nQualities Available :"
        else:
            message = "No quality settings found."
        await BotMessageHandler.edit_message(e, message, buttons=Buttons.quality_setting_buttons)
        
    @staticmethod
    async def edit_core_setting_message(e):
        downloading_core = await db.get_user_downloading_core(e.sender_id)
        if downloading_core:
            message = BotMessageHandler.core_selection_message + f"\nCore: {downloading_core}"
        else:
            message = BotMessageHandler.core_selection_message + "\nNo core setting found."
        await BotMessageHandler.edit_message(e, message, buttons=Buttons.core_setting_buttons)

    @staticmethod
    async def edit_subscription_status_message(e):
        is_subscribed = await db.is_user_subscribed(e.sender_id)
        message = f"Subscroption settings:\nYour Subscription Status: {is_subscribed}"
        await BotMessageHandler.edit_message(e, message, buttons=Buttons.subscription_setting_buttons)
        
    @staticmethod
    async def edit_tweet_capture_setting_message(client,e):
        night_mode = await TweetCapture.get_settings(e.sender_id)
        message = f"Tweet capture settings:\nYour Night Mode: {night_mode['night_mode']}"
        await BotMessageHandler.edit_message(e, message, buttons=Buttons.tweet_capture_setting_buttons)
        await client.send_file(e.chat_id , "./repository/ScreenShots/night_modes.png", caption="Here's the difference between night modes:")