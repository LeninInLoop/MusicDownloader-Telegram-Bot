import re, requests, bs4
import wget, asyncio

class insta():
    
    @classmethod
    def initialize(cls):
        cls.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:105.0) Gecko/20100101 Firefox/105.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Length": "99",
        "Origin": "https://saveig.app",
        "Connection": "keep-alive",
        "Referer": "https://saveig.app/en",
        }

    @staticmethod
    def is_instagram_url(text) -> bool:
        pattern = r'(?:https?:\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am)(?:\/(?:p|reel|tv|stories)\/(?:[^\s\/]+)|\/([\w-]+)(?:\/(?:[^\s\/]+))?)'
        match = re.search(pattern, text)
        return bool(match)
    
    @staticmethod
    def extract_url(text) -> str:
        pattern = r'(?:https?:\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am)(?:\/(?:p|reel|tv|stories)\/(?:[^\s\/]+)|\/([\w-]+)(?:\/(?:[^\s\/]+))?)'
        match = re.search(pattern, text)
        if match:
            return match.group()
        return None
    
    @staticmethod
    def determine_content_type(text) -> str:
        content_types  = {
            '/p/': 'post',
            '/reel/': 'reel',
            '/tv': 'igtv',
            '/stories/': 'story',
        }

        for pattern, content_type in content_types.items():
            if pattern in text:
                return content_type

        return None

    @staticmethod
    def is_publicly_available(url) -> bool:
        try:
            response = requests.get(url, headers=insta.headers)
            if response.status_code == 200:
                return True
            else:
                return False
        except:
            return False
        
    @staticmethod
    async def download(client, event, link) -> bool:
        start_message = await event.respond("Processing Your insta link ....")
        try:
            url = link.replace("instagram.com", "ddinstagram.com").replace("==", "%3D%3D")
            await client.send_file(event.chat_id, url[:-1] if url.endswith("=") else url[:], caption="Here's your Instagram content")
        except:
            content_type = insta.determine_content_type(link)
            try:
                if content_type == 'reel':
                    await insta.download_reel(client, event, link)
                    await start_message.delete()
                elif content_type == 'post':
                    await insta.download_post(client, event, link)
                    await start_message.delete()
                elif content_type == 'story':
                    await insta.download_story(client, event, link)
                    await start_message.delete()
                else:
                    await event.reply("Sorry, unable to find the requested content. Please ensure it's publicly available.")
                    await start_message.delete()
            except:
                    await event.reply("Sorry, unable to find the requested content. Please ensure it's publicly available.")
                    await start_message.delete()
                
    async def download_reel(client, event, link):
        try:
            meta_tag = await insta.get_meta_tag(link)
            content_value = f"https://ddinstagram.com{meta_tag['content']}"
        except:
            meta_tag = await insta.search_saveig(link)
            content_value = meta_tag[0] if meta_tag else None
        
        if content_value:
            await insta.send_file(client, event, content_value)
        else:
            await event.reply("Oops, something went wrong")

    async def download_post(client, event, link):
        meta_tags = await insta.search_saveig(link)
        
        if meta_tags:
            for meta in meta_tags[:-1]:
                com = await event.reply_text(meta)
                await asyncio.sleep(1)
                await insta.send_file(client, event, com.text)
                await com.delete()
        else:
            await event.reply("Oops, something went wrong")

    async def download_story(client, event, link):
        meta_tag = await insta.search_saveig(link)
        
        if meta_tag:
            await insta.send_file(client, event, meta_tag[0])
        else:
            await event.reply("Oops, something went wrong")

    async def get_meta_tag(link):
        getdata = requests.get(link).text
        soup = bs4.BeautifulSoup(getdata, 'html.parser')
        return soup.find('meta', attrs={'property': 'og:video'})

    async def search_saveig(link):
        meta_tag = requests.post("https://saveig.app/api/ajaxSearch", data={"q": link, "t": "media", "lang": "en"}, headers=insta.headers)
        if meta_tag.ok:
            res = meta_tag.json()
            return re.findall(r'href="(https?://[^"]+)"', res['data'])
        return None

    async def send_file(client, event, content_value):
        try:
            await client.send_file(event.chat_id, content_value, caption="Here's your Instagram content")
        except:
            downfile = wget.download(content_value)
            await event.send_file(event.chat_id, downfile, caption="Here's your Instagram content")
