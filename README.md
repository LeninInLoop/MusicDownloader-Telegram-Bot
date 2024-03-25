# Music/Video Downloader Bot

Music/Video Downloader Bot is a Telegram bot that allows users to download music/video from Spotify and YouTube. It provides a convenient way to access and download your favorite tracks/videos directly to your device.

You can test this bot at:
```telegram.me/spotify_yt_downloader_bot```

## Features

- Download music from Spotify links
- Search for songs on Spotify using keywords
- Supports different audio formats and qualities
- Option to select between SpotDL and YoutubeDL for downloading
- Broadcast messages to all users or specific subscribers
- Subscription management for users
- Voice recognition for song search
- Screenshot capture of tweets
- Download twitter media
- Download Instagram media
- Download Youtube media

## Installation

Follow these steps to set up the `telegram_spotify_downloader` project on your system.

### Step 1: Clone the Repository

Open a terminal and clone the `telegram_spotify_downloader` repository from GitHub:

```zsh
git clone https://github.com/AdibNikjou/telegram_video_music_downloader.git
```

### Step 2: Install Python Dependencies

Navigate to the cloned repository's directory and install the required Python dependencies using `pip`:

```zsh
cd telegram_spotify_downloader
pip install -r requirements.txt
```

### Step 3: Install Google Chrome

Ensure you have Google Chrome version 122 installed on your system. The installation process varies depending on your operating system.

#### For Ubuntu:

```zsh
sudo apt update
sudo apt install google-chrome-stable -y
```

#### For Fedora:

```zsh
sudo dnf update
sudo dnf install google-chrome-stable -y
```

### Step 4: Verify Installation

After completing the installation steps, verify that Google Chrome is installed and that the version is 122. You can check the version by running:

```zsh
google-chrome --version
```

### Step 5: Set Up Your Environment Variables

Create a `config.env` file in the root directory of the project and add the following environment variables:

- `SPOTIFY_CLIENT_ID=your_spotify_client_id`
- `SPOTIFY_CLIENT_SECRET=your_spotify_client_secret`
- `BOT_TOKEN=your_telegram_bot_token`
- `API_ID=your_telegram_api_id`
- `API_HASH=your_telegram_api_hash`
- `GENIUS_ACCESS_TOKEN=your_genius_access_token`

### Step 6: Run the Bot

With all dependencies installed and environment variables set, you can now run the bot:

```zsh
python3 main.py
```

## Usage

1. Start a conversation with the bot by sending the `/start` command.
2. Share a Spotify link or use the `/search` command followed by a song title or lyrics to find and download music.
3. Use the `/settings` command to change the audio format and quality.
4. Subscribe to receive updates and news from the bot.
5. Use the `/admin` command to access admin features (available only to authorized users).

## Commands

- `/start`: Start the bot and get the welcome message.
- `/search <query>`: Search for songs on Spotify.
- `/settings`: Access settings to change audio format and quality, downloading core, and subscription.
- `/core`: Access directly to core settings to change downloading core.
- `/quality`: Access directly to quality settings to change audio format and quality.
- `/subscribe`: Subscribe to receive updates.
- `/unsubscribe`: Unsubscribe from updates.
- `/help`: Get help on how to use the bot.
- `/ping`: Check the bot's response time.
- `/stats`: Get statistics about the bot's usage.
- `/admin`: Access admin features.

## Admin Commands

- `/broadcast`: Send a message to all subscribed users or specific subscribers.
   - Ex: `/broadcast` -> Send a message to all subscribed users.
   - Ex: `/broadcast (1297994832,1297994833)` -> Send a message to 1297994832 and 1297994833 only.
   - Ex: `/broadcast_to_all` -> Send a message to all users.
- `/stats`: Get statistics about the bot's usage.

## Dependencies

- Python 3.8+
- Telethon
- Spotipy
- Yt-dlp
- spotdl
- Shazamio
- Pillow
- dotenv
- aiosqlite
- lyricsgenius
- FastTelethonhelper

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue if you find any bugs or have suggestions for improvements.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contact

For any inquiries or feedback, please contact the creator:
- Telegram: @AdibNikjou
- Email: adib.n7789@gmail.com

## Acknowledgments

- Spotify API for providing access to music metadata.
- Telegram API for the bot framework.
- Shazam API for voice recognition.
- YoutubeDL for downloading music from YouTube.
