from utils import Shazam, os


class ShazamHelper:

    @classmethod
    def initialize(cls):
        cls.Shazam = Shazam()

        cls.voice_repository_dir = "repository/Voices"
        if not os.path.isdir(cls.voice_repository_dir):
            os.makedirs(cls.voice_repository_dir, exist_ok=True)

    @staticmethod
    async def recognize(file):
        try:
            out = await ShazamHelper.Shazam.recognize(file)
        except:
            out = await ShazamHelper.Shazam.recognize_song(file)
        return ShazamHelper.extract_song_details(out)

    # Function to extract the Spotify link
    @staticmethod
    def extract_spotify_link(data):
        for provider in data['track']['hub']['providers']:
            if provider['type'] == 'SPOTIFY':
                for action in provider['actions']:
                    if action['type'] == 'uri':
                        return action['uri']
        return None

    @staticmethod
    def extract_song_details(data):

        try:
            music_name = data['track']['title']
            artists_name = data['track']['subtitle']
        except:
            return ""

        song_details = {
            'music_name': music_name,
            'artists_name': artists_name
        }
        song_details_string = ", ".join(f"{value}" for value in song_details.values())
        return song_details_string
