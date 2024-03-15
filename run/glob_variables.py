

class BotState:
    channel_usernames = ["Spotify_yt_downloader"]
    user_states = {}

    @staticmethod
    def initialize_user_state(user_id):
        if user_id not in BotState.user_states:
            BotState.user_states[user_id] = {
                'admin_message_to_send': None,
                'admin_broadcast': False,
                'cancel_broadcast': False,
                'send_to_specified_flag': False,
                'messages': {},
                'search_result': None,
                'waiting_message': None
            }

    @staticmethod
    def get_user_state(user_id):
        BotState.initialize_user_state(user_id)
        return BotState.user_states[user_id]

    @staticmethod
    def get_admin_message_to_send(user_id):
        return BotState.get_user_state(user_id)['admin_message_to_send']

    @staticmethod
    def get_admin_broadcast(user_id):
        return BotState.get_user_state(user_id)['admin_broadcast']

    @staticmethod
    def get_cancel_broadcast(user_id):
        return BotState.get_user_state(user_id)['cancel_broadcast']

    @staticmethod
    def get_send_to_specified_flag(user_id):
        return BotState.get_user_state(user_id)['send_to_specified_flag']

    @staticmethod
    def get_messages(user_id):
        return BotState.get_user_state(user_id)['messages']

    @staticmethod
    def get_search_result(user_id):
        return BotState.get_user_state(user_id)['search_result']

    @staticmethod
    def get_waiting_message(user_id):
        return BotState.get_user_state(user_id)['waiting_message']
    
    @staticmethod
    def set_admin_message_to_send(user_id, message):
        BotState.get_user_state(user_id)['admin_message_to_send'] = message

    @staticmethod
    def set_admin_broadcast(user_id, value):
        BotState.get_user_state(user_id)['admin_broadcast'] = value

    @staticmethod
    def set_cancel_broadcast(user_id, value):
        BotState.get_user_state(user_id)['cancel_broadcast'] = value

    @staticmethod
    def set_send_to_specified_flag(user_id, value):
        BotState.get_user_state(user_id)['send_to_specified_flag'] = value

    @staticmethod
    def set_messages(user_id, messages):
        BotState.get_user_state(user_id)['messages'] = messages

    @staticmethod
    def set_search_result(user_id, result):
        BotState.get_user_state(user_id)['search_result'] = result

    @staticmethod
    def set_waiting_message(user_id, message):
        BotState.get_user_state(user_id)['waiting_message'] = message
    