from utils import bs4, wget
from utils import asyncio, re, requests


class Insta:

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
    def extract_url(text) -> str | None:
        pattern = r'(https?:\/\/(?:www\.)?(?:ddinstagram\.com|instagram\.com|instagr\.am)\/(?:p|reel|tv|stories)\/[\w-]+\/?(?:\?[^\s]+)?(?:={1,2})?)'
        match = re.search(pattern, text)
        if match:
            return match.group(0)
        return None

    @staticmethod
    def determine_content_type(text) -> str:
        content_types = {
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
            response = requests.get(url, headers=Insta.headers)
            if response.status_code == 200:
                return True
            else:
                return False
        except:
            return False

    @staticmethod
    async def download_content(client, event, start_message, link) -> bool:
        content_type = Insta.determine_content_type(link)
        try:
            if content_type == 'reel':
                await Insta.download_reel(client, event, link)
                await start_message.delete()
                return True
            elif content_type == 'post':
                await Insta.download_post(client, event, link)
                await start_message.delete()
                return True
            elif content_type == 'story':
                await Insta.download_story(client, event, link)
                await start_message.delete()
                return True
            else:
                await event.reply(
                    "Sorry, unable to find the requested content. Please ensure it's publicly available.")
                await start_message.delete()
                return True
        except:
            await event.reply("Sorry, unable to find the requested content. Please ensure it's publicly available.")
            await start_message.delete()
            return False

    @staticmethod
    async def download(client, event) -> bool:
        link = Insta.extract_url(event.message.text)

        start_message = await event.respond("Processing Your insta link ....")
        try:
            if "ddinstagram.com" in link:
                raise Exception
            link = link.replace("instagram.com", "ddinstagram.com")
            return await Insta.download_content(client, event, start_message, link)
        except:
            await Insta.download_content(client, event, start_message, link)

    @staticmethod
    async def download_reel(client, event, link):
        try:
            meta_tag = await Insta.get_meta_tag(link)
            content_value = f"https://ddinstagram.com{meta_tag['content']}"
        except:
            meta_tag = await Insta.search_saveig(link)
            content_value = meta_tag[0] if meta_tag else None

        if content_value:
            await Insta.send_file(client, event, content_value)
        else:
            await event.reply("Oops, something went wrong")

    @staticmethod
    async def download_post(client, event, link):
        meta_tags = await Insta.search_saveig(link)
        if meta_tags:
            for meta in meta_tags[:-1]:
                await asyncio.sleep(1)
                await Insta.send_file(client, event, meta)
        else:
            await event.reply("Oops, something went wrong")

    @staticmethod
    async def download_story(client, event, link):
        meta_tag = await Insta.search_saveig(link)
        if meta_tag:
            await Insta.send_file(client, event, meta_tag[0])
        else:
            await event.reply("Oops, something went wrong")

    @staticmethod
    async def get_meta_tag(link):
        getdata = requests.get(link).text
        soup = bs4.BeautifulSoup(getdata, 'html.parser')
        return soup.find('meta', attrs={'property': 'og:video'})

    @staticmethod
    async def search_saveig(link):
        meta_tag = requests.post("https://saveig.app/api/ajaxSearch", data={"q": link, "t": "media", "lang": "en"},
                                 headers=Insta.headers)
        if meta_tag.ok:
            res = meta_tag.json()
            return re.findall(r'href="(https?://[^"]+)"', res['data'])
        return None

    @staticmethod
    async def send_file(client, event, content_value):
        try:
            await client.send_file(event.chat_id, content_value, caption="Here's your Instagram content")
        except:
            fileoutput = f"{str(content_value)}"
            downfile = wget.download(content_value, out=fileoutput)
            await client.send_file(event.chat_id, fileoutput, caption="Here's your Instagram content")
