from telethon import Button
from tweetcapture import TweetCapture
import os, hashlib, re, asyncio, bs4, requests
from utils import db

class X:
    
    @classmethod
    def initialize(cls):
        cls.tweet = TweetCapture()
        cls.screen_shot_path = 'repository/X_screen'
        if not os.path.isdir(cls.screen_shot_path):
            os.makedirs(cls.screen_shot_path, exist_ok=True)
        
    @staticmethod
    async def take_screenshot_of_tweet(event, tweet_url):
        
        tweet_message = await event.respond("Processing Your X/Twitter Link ......")
        
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
    async def send_screenshot(client,event,screenshot_path, has_media) -> bool:
        screen_shot_message = await event.respond("Uploading ScreenShot ......")
        button = Button.inline("Download Media", data=b"@X_download_media") if has_media else None
        try :    
            await client.send_file(event.chat_id,screenshot_path,
            caption = f"""Here's Your Tweet! :)""",
            buttons=button
            )
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

    @staticmethod
    async def has_media(link):
        link = link.replace("x.com","fxtwitter.com") if "x.com" in link else link.replace("twitter.com","fxtwitter.com")
        try:
            response = requests.get(link)
            soup = bs4.BeautifulSoup(response.content, "html.parser")

            # Check if the URL has an og:video meta tag
            meta_tag = soup.find("meta", attrs={"property": "og:video"})
            if meta_tag:
                return True

            # Check if the URL has an og:image meta tag
            meta_tag = soup.find("meta", attrs={"property": "og:image"})
            if meta_tag:
                return True

            # If neither og:video nor og:image meta tag is found, return False
            return False

        except Exception as e:
            print(f"Error checking media in URL: {e}")
            return False
        
    @staticmethod
    async def download(client, event):
        user_id = event.sender_id
        link = await db.get_tweet_url(user_id)
        link = link.replace("x.com", "fxtwitter.com") if "x.com" in link else link.replace("twitter.com", "fxtwitter.com")

        try:
            await client.send_file(event.chat_id, link, caption="Thank you for using - @InstaReelsdownbot")
        except Exception as e:
            print(f"Error sending file: {e}")
            try:
                get_api = requests.get(link).text
                soup = bs4.BeautifulSoup(get_api, "html.parser")
                meta_tag = soup.find("meta", attrs={"property": "og:video"}) or soup.find("meta", attrs={"property": "og:image"})
                if meta_tag:
                    content_value = meta_tag['content']
                    try:
                        await client.send_file(event.chat_id, content_value, caption="Thank you for using - @InstaReelsdownbot")
                    except Exception as e:
                        print(f"Error sending file: {e}")
                        try:
                            await asyncio.sleep(1)
                            await client.send_file(event.chat_id, content_value, caption="Thank you for using - @InstaReelsdownbot")
                        except Exception as e:
                            print(f"Error sending file: {e}")
                            await event.reply("Oops Invalid link or Media Is Not Available :(")
                else:
                    await event.reply("Oops Invalid link or Media Is Not Available :(")
            except Exception as e:
                print(f"Error: {e}")
                await event.reply("Oops Invalid link or Media Is Not Available :(")
