from tweetcapture import TweetCapture
import os, hashlib, re

class X:
    
    @classmethod
    def initialize(cls):
        cls.tweet = TweetCapture()
        cls.screen_shot_path = 'repository/X_screen'
        if not os.path.isdir(cls.screen_shot_path):
            os.makedirs(cls.screen_shot_path, exist_ok=True)
        
    @staticmethod
    async def take_screenshot_of_tweet(event, tweet_url):
        
        tweet_message = await event.respond("Processing Your X/Twitter Link........")
        
        sanitized_url = tweet_url.replace('/', '_').replace(':', '_')
        if len(sanitized_url) > 50:
            sanitized_url = sanitized_url[:50]

        url_hash = hashlib.md5(tweet_url.encode()).hexdigest()
        filename = f"{url_hash}.png"
        screenshot_path = os.path.join(X.screen_shot_path, filename)
        
        try:
            await X.tweet.screenshot(tweet_url, screenshot_path, mode=3, night_mode=1, overwrite=True)
            await tweet_message.delete()
            return screenshot_path
        except Exception as Err:
            if str(Err) == "File already exists":
                await tweet_message.delete()
                return screenshot_path
            await tweet_message.edit(f"Sorry I Couldnt Find The Tweet.\nReason:{str(Err)}")
            return None
            
    @staticmethod
    async def send_screenshot(client,event,screenshot_path) -> bool:
        screen_shot_message = await event.respond("Uploading ScreenShot......")
        try :    
            await client.send_file(event.chat_id,screenshot_path,
            caption = f"""Here's Your Tweet! :)""")
            await screen_shot_message.delete()
            return True
        except:
            return False
    
    @staticmethod   
    def contains_x_or_twitter_link(text):
        pattern = r'(https?://(?:www\.)?twitter\.com/[^/\s]+/status/\d+|https?://(?:www\.)?x\.com/[^/\s]+)'
        return bool(re.search(pattern, text))
 
    @staticmethod   
    def find_and_send_x_or_twitter_link(text):
        pattern = r'(https?://(?:www\.)?twitter\.com/[^/\s]+/status/\d+|https?://(?:www\.)?x\.com/[^?\s]+)'
        match = re.search(pattern, text)
        return match.group(0) if match else None
