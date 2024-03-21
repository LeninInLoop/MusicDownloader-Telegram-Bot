from utils import db

@staticmethod
async def update_bot_version_user_season(event) -> bool:
    user_id = event.sender_id 
    music_quality = await db.get_user_music_quality(user_id)
    downloading_core = await db.get_user_downloading_core(user_id)
    tweet_capture_setting = await db.get_user_tweet_capture_settings(user_id)
    if music_quality == {} or downloading_core == None or tweet_capture_setting == {}:
        await event.respond("We Have Updated The Bot, Please start Over using the /start command.")
        await db.set_user_updated_flag(user_id,0)
        return False
    await db.set_user_updated_flag(user_id,1)
    return True