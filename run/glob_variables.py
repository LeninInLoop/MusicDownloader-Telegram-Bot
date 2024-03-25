from utils import os, load_dotenv, dataclass, field
from telethon import TelegramClient

@dataclass
class UserState:
    admin_message_to_send: str = None
    admin_broadcast: bool = False
    send_to_specified_flag: bool = False
    messages: dict = field(default_factory=dict)
    search_result: str = None
    tweet_screenshot: str = None
    youtube_search: str = None
    waiting_message: str = None
    
class BotState:
    
    channel_usernames = ["Spotify_yt_downloader"]
    user_states = {}

    load_dotenv('config.env')

    BOT_TOKEN = os.getenv('BOT_TOKEN')
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    ADMIN_USER_IDS = [int(id) for id in os.getenv('ADMIN_USER_IDS').split(',')]

    if not all([BOT_TOKEN, API_ID, API_HASH, ADMIN_USER_IDS]):
        raise ValueError("Required environment variables are missing.")
        
    BOT_CLIENT = TelegramClient('bot', API_ID, API_HASH)

    # @staticmethod #[DEPRECATED]
    # def initialize_user_state(user_id):
    #     if user_id not in BotState.user_states:
    #         BotState.user_states[user_id] = {
    #             'admin_message_to_send': None,
    #             'admin_broadcast': False,
    #             'send_to_specified_flag': False,
    #             'messages': {},
    #             'search_result': None,
    #             'tweet_screenshot': None,
    #             'youtube_search': None,
    #             'waiting_message': None
    #         }

    @staticmethod
    def initialize_user_state(user_id):
        if user_id not in BotState.user_states:
            BotState.user_states[user_id] = UserState()
            
    @staticmethod
    def get_user_state(user_id):
        BotState.initialize_user_state(user_id)
        return BotState.user_states[user_id]

    @staticmethod
    def get_admin_message_to_send(user_id):
        user_state = BotState.get_user_state(user_id)
        return user_state.admin_message_to_send

    @staticmethod
    def get_tweet_screenshot(user_id):
        user_state = BotState.get_user_state(user_id)
        return user_state.tweet_screenshot

    @staticmethod
    def get_youtube_search(user_id):
        user_state = BotState.get_user_state(user_id)
        return user_state.youtube_search
    
    @staticmethod
    def get_admin_broadcast(user_id):
        user_state = BotState.get_user_state(user_id)
        return user_state.admin_broadcast
    
    @staticmethod
    def get_send_to_specified_flag(user_id):
        user_state = BotState.get_user_state(user_id)
        return user_state.send_to_specified_flag

    @staticmethod
    def get_messages(user_id):
        user_state = BotState.get_user_state(user_id)
        return user_state.messages

    @staticmethod
    def get_search_result(user_id):
        user_state = BotState.get_user_state(user_id)
        return user_state.search_result

    @staticmethod
    def get_waiting_message(user_id):
        user_state = BotState.get_user_state(user_id)
        return user_state.waiting_message
    
    @staticmethod
    def set_admin_message_to_send(user_id, message):
        user_state = BotState.get_user_state(user_id)
        user_state.admin_message_to_send = message

    @staticmethod
    def set_tweet_screenshot(user_id, value):
        user_state = BotState.get_user_state(user_id)
        user_state.tweet_screenshot = value

    @staticmethod
    def set_youtube_search(user_id, value):
        user_state = BotState.get_user_state(user_id)
        user_state.youtube_search = value
        
    @staticmethod
    def set_admin_broadcast(user_id, value):
        user_state = BotState.get_user_state(user_id)
        user_state.admin_broadcast = value
        
    @staticmethod
    def set_send_to_specified_flag(user_id, value):
        user_state = BotState.get_user_state(user_id)
        user_state.send_to_specified_flag = value

    @staticmethod
    def set_messages(user_id, messages):
        user_state = BotState.get_user_state(user_id)
        user_state.messages = messages

    @staticmethod
    def set_search_result(user_id, result):
        user_state = BotState.get_user_state(user_id)
        user_state.search_result = result

    @staticmethod
    def set_waiting_message(user_id, message):
        user_state = BotState.get_user_state(user_id)
        user_state.waiting_message = message
    