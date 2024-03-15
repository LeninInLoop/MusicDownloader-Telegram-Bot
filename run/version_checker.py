from utils import db

@staticmethod
async def update_bot_version_user_season(event):
    user_id = event.sender_id 
    music_quality, downloading_core = await db.get_user_settings(user_id)
    if music_quality == None or downloading_core == None:
        await event.respond("We Have Updated The Bot, Please start Over using the /start command.")
        await db.set_user_updated_flag(user_id,0)
    await db.set_user_updated_flag(user_id,1)