from run import Button, Buttons
from utils import asyncio, re, os, load_dotenv, combinations
from utils import db, SpotifyException, fast_upload, Any
from utils import Image, BytesIO, YoutubeDL, lyricsgenius, aiohttp, InputMediaUploadedDocument
from utils import SpotifyClientCredentials, spotipy, ThreadPoolExecutor, DocumentAttributeAudio


class SpotifyDownloader:

    @classmethod
    def _load_dotenv_and_create_folders(cls):
        try:
            load_dotenv('config.env')
            cls.SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
            cls.SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
            cls.GENIUS_ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
        except FileNotFoundError:
            print("Failed to Load .env variables")

        # Create a directory for the download
        cls.download_directory = "repository/Musics"
        if not os.path.isdir(cls.download_directory):
            os.makedirs(cls.download_directory, exist_ok=True)

        cls.download_icon_directory = "repository/Icons"
        if not os.path.isdir(cls.download_icon_directory):
            os.makedirs(cls.download_icon_directory, exist_ok=True)

    @classmethod
    def initialize(cls):
        cls._load_dotenv_and_create_folders()
        cls.MAXIMUM_DOWNLOAD_SIZE_MB = 50
        cls.spotify_account = spotipy.Spotify(client_credentials_manager=
                                              SpotifyClientCredentials(client_id=cls.SPOTIFY_CLIENT_ID,
                                                                       client_secret=cls.SPOTIFY_CLIENT_SECRET))
        cls.genius = lyricsgenius.Genius(cls.GENIUS_ACCESS_TOKEN)

    @staticmethod
    def is_spotify_link(url):
        pattern = r'https?://open\.spotify\.com/.*'
        return re.match(pattern, url) is not None

    @staticmethod
    def identify_spotify_link_type(spotify_url) -> str:
        # Define a list of all primary resource types supported by Spotify
        resource_types = ['track', 'playlist', 'album', 'artist', 'show', 'episode']

        for resource_type in resource_types:
            try:
                # Dynamically call the appropriate method on the Spotify API client
                resource = getattr(SpotifyDownloader.spotify_account, resource_type)(spotify_url)
                return resource_type
            except (SpotifyException, Exception) as e:
                # Continue to the next resource type if an exception occurs
                continue

        # Return 'none' if no resource type matches
        return 'none'

    @staticmethod
    async def extract_data_from_spotify_link(event, spotify_url):

        # Identify the type of Spotify link to handle the data extraction accordingly
        link_type = SpotifyDownloader.identify_spotify_link_type(spotify_url)

        try:
            if link_type == "track":
                # Extract track information and construct the link_info dictionary
                track_info = SpotifyDownloader.spotify_account.track(spotify_url)
                artists = track_info['artists']
                album = track_info['album']
                link_info = {
                    'type': "track",
                    'track_name': track_info['name'],
                    'artist_name': ', '.join(artist['name'] for artist in artists),
                    'artist_ids': [artist['id'] for artist in artists],
                    'artist_url': artists[0]['external_urls']['spotify'],
                    'album_name': album['name'].translate(str.maketrans('', '', '()[]')),
                    'album_url': album['external_urls']['spotify'],
                    'release_year': album['release_date'].split('-')[0],
                    'image_url': album['images'][0]['url'],
                    'track_id': track_info['id'],
                    'isrc': track_info['external_ids']['isrc'],
                    'track_url': track_info['external_urls']['spotify'],
                    'youtube_link': None,  # Placeholder, will be resolved below
                    'preview_url': track_info.get('preview_url'),
                    'duration_ms': track_info['duration_ms'],
                    'track_number': track_info['track_number'],
                    'is_explicit': track_info['explicit']
                }

                # Attempt to enhance track info with additional external data (e.g., YouTube link)
                link_info['youtube_link'] = await SpotifyDownloader.extract_yt_video_info(link_info)
                return link_info

            elif link_type == "playlist":
                # Extract playlist information and compile playlist tracks into a dictionary
                playlist_info = SpotifyDownloader.spotify_account.playlist(spotify_url)

                playlist_info_dict = {
                    'type': 'playlist',
                    'playlist_name': playlist_info['name'],
                    'playlist_id': playlist_info['id'],
                    'playlist_url': playlist_info['external_urls']['spotify'],
                    'playlist_owner': playlist_info['owner']['display_name'],
                    'playlist_image_url': playlist_info['images'][0]['url'] if playlist_info['images'] else None,
                    'playlist_followers': playlist_info['followers']['total'],
                    'playlist_public': playlist_info['public'],
                    'playlist_tracks_total': playlist_info['tracks']['total'],
                }
                return playlist_info_dict

            else:
                # Handle unsupported Spotify link types
                link_info = {'type': link_type}
                print(f"Unsupported Spotify link type provided: {spotify_url}")
                return link_info

        except Exception as e:
            # Log and handle any errors encountered during information extraction
            print(f"Error extracting Spotify information: {e}")
            await event.respond("An error occurred while processing the Spotify link. Please try again.")
            return {}

    @staticmethod
    async def extract_yt_video_info(spotify_link_info):
        if spotify_link_info is None:
            return None

        video_url = spotify_link_info.get('youtube_link')
        if video_url:
            return video_url

        artist_name = spotify_link_info["artist_name"]
        track_name = spotify_link_info["track_name"]
        release_year = spotify_link_info["release_year"]
        track_duration = spotify_link_info.get("duration_ms", 0) / 1000
        album_name = spotify_link_info.get("album_name", "")

        queries = [
            f'"{artist_name}" "{track_name}" lyrics {release_year}',
            f'"{track_name}" by "{artist_name}" {release_year}',
            f'"{artist_name}" "{track_name}" "{album_name}" {release_year}',
        ]

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'ytsearch': 3,  # Limit the number of search results
            'skip_download': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'noplaylist': True,  # Disable playlist processing
            'nocheckcertificate': True,  # Disable SSL certificate verification
            'cachedir': False  # Disable caching
        }

        executor = ThreadPoolExecutor(max_workers=16)  # Use 16 workers for the blocking I/O operation
        stop_event = asyncio.Event()

        async def search_query(query):
            def extract_info_blocking():
                with YoutubeDL(ydl_opts) as ydl:
                    try:
                        info = ydl.extract_info(f'ytsearch:{query}', download=False)
                        entries = info.get('entries', [])
                        return entries
                    except Exception:
                        return []

            entries = await asyncio.get_running_loop().run_in_executor(executor, extract_info_blocking)

            if not stop_event.is_set():
                for video_info in entries:
                    video_url = video_info.get('webpage_url')
                    video_duration = video_info.get('duration', 0)

                    # Compare the video duration with the track duration from Spotify
                    duration_diff = abs(video_duration - track_duration)
                    if duration_diff <= 35:
                        stop_event.set()
                        return video_url

            return None

        search_tasks = [asyncio.create_task(search_query(query)) for query in queries]
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        for result in search_results:
            if isinstance(result, Exception):
                continue
            if result is not None:
                return result

        return None

    @staticmethod
    async def download_and_send_spotify_info(event, is_query: bool = True) -> bool:
        user_id = event.sender_id
        waiting_message = None
        if is_query:
            waiting_message = await event.respond('⏳')
            query_data = str(event.data)
            spotify_link = query_data.split("/")[-1][:-1]
        else:
            spotify_link = str(event.message.text)

        # Ensure the user's data is up-to-date
        if not await db.get_user_updated_flag(user_id):
            await event.respond(
                "Our bot has been updated. Please restart the bot with the /start command."
            )
            return True

        link_info = await SpotifyDownloader.extract_data_from_spotify_link(event, spotify_url=spotify_link)
        if link_info["type"] == "track":
            await waiting_message.delete() if is_query else None
            return await SpotifyDownloader.send_track_info(event.client, event, link_info)
        elif link_info["type"] == "playlist":
            return await SpotifyDownloader.send_playlist_info(event.client, event, link_info)
        else:
            await event.respond(
                f"""Unsupported Spotify link type.\n\nThe Bot is currently supports:\n- track \n- playlist\n\nYou 
                requested: {link_info["type"]} """)
            return False

    @staticmethod
    async def fetch_and_save_playlist_image(playlist_id, playlist_image_url):
        icon_name = f"{playlist_id}.jpeg"
        icon_path = os.path.join(SpotifyDownloader.download_icon_directory, icon_name)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(playlist_image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        img = Image.open(BytesIO(image_data))
                        img.save(icon_path)
                        return icon_path
                    else:
                        print(f"Failed to download playlist image. Status code: {response.status}")
        except Exception as e:
            print(f"Error downloading or saving playlist image: {e}")

        return None

    @staticmethod
    async def send_playlist_info(client, event, link_info):
        playlist_image_url = link_info.get('playlist_image_url')
        playlist_name = link_info.get('playlist_name', 'Unavailable')
        playlist_id = link_info.get('playlist_id', 'Unavailable')
        playlist_url = link_info.get('playlist_url', 'Unavailable')
        playlist_owner = link_info.get('playlist_owner', 'Unavailable')
        total_tracks = link_info.get('playlist_tracks_total', 0)
        collaborative = 'Yes' if link_info.get('collaborative', False) else 'No'
        public = 'Yes' if link_info.get('playlist_public', False) else 'No'
        followers = link_info.get('playlist_followers', 'Unavailable')

        # Construct the playlist information text
        playlist_info = (
            f"🎧 **Playlist: {playlist_name}** 🎶\n\n"
            f"---\n\n"
            f"**Details:**\n\n"

            f"  - 👤 Owner: {playlist_owner}\n"
            f"  - 👥 Followers: {followers}\n"

            f"  - 🎵 Total Tracks: {total_tracks}\n"
            f"  - 🤝 Collaborative: {collaborative}\n"
            f"  - 🌐 Public: {public}\n"

            f"  - 🎧 Playlist URL: [Listen On Spotify]({playlist_url})\n"
            f"---\n\n"
            f"**Enjoy the music!** 🎶"
        )

        # Buttons for interactivity
        buttons = [
            [Button.inline("Download All Tracks Inside [mp3]", data=f"spotify/dl/playlist/{playlist_id}/all")],
            [Button.inline("Download Top 10", data=f"spotify/dl/playlist/{playlist_id}/10")],
            [Button.inline("Search Tracks inside", data=f"spotify/s/playlist/{playlist_id}")],
            [Button.inline("Cancel", data=b"cancel")]
        ]

        # Handle the playlist image if exists
        if playlist_image_url:
            icon_path = await SpotifyDownloader.fetch_and_save_playlist_image(playlist_id, playlist_image_url)
            if icon_path:
                sent_message = await client.send_file(
                    event.chat_id,
                    icon_path,
                    caption=playlist_info,
                    parse_mode='Markdown',
                    buttons=buttons,
                )
            else:
                await event.respond(playlist_info, parse_mode='Markdown', buttons=buttons)
        else:
            await event.respond(playlist_info, parse_mode='Markdown', buttons=buttons)

        return True

    @staticmethod
    async def download_icon(link_info):
        track_name = link_info['track_name']
        artist_name = link_info['artist_name']
        image_url = link_info["image_url"]

        icon_name = f"{track_name} - {artist_name}.jpeg".replace("/", " ")
        icon_path = os.path.join(SpotifyDownloader.download_icon_directory, icon_name)

        if not os.path.isfile(icon_path):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            img = Image.open(BytesIO(image_data))
                            img.save(icon_path)
                        else:
                            print(
                                f"Failed to download track image for {track_name} - {artist_name}. Status code: {response.status}")
            except Exception as e:
                print(f"Failed to download or save track image for {track_name} - {artist_name}: {e}")
        return icon_path

    @staticmethod
    async def send_track_info(client, event, link_info):
        user_id = event.sender_id
        music_quality = await db.get_user_music_quality(user_id)
        downloading_core = await db.get_user_downloading_core(user_id)

        if downloading_core == "Auto":
            spotdl = True if (link_info.get('youtube_link') is None) else False
        else:
            spotdl = downloading_core == "SpotDL"

        def build_file_path(artist, track_name, quality_info, format, make_dir=False):
            filename = f"{artist} - {track_name}".replace("/", "")
            if not spotdl:
                filename += f"-{quality_info['quality']}"
            directory = os.path.join(SpotifyDownloader.download_directory, filename)
            if make_dir and not os.path.exists(directory):
                os.makedirs(directory)
            return f"{directory}.{quality_info['format']}"

        def is_track_local(artist_names, track_name):
            for r in range(1, len(artist_names) + 1):
                for combination in combinations(artist_names, r):
                    file_path = build_file_path(", ".join(combination), track_name, music_quality,
                                                music_quality['format'])
                    if os.path.isfile(file_path):
                        return True, file_path
            return False, None

        artist_names = link_info['artist_name'].split(', ')
        is_local, file_path = is_track_local(artist_names, link_info['track_name'])

        icon_path = await SpotifyDownloader.download_icon(link_info)

        SpotifyInfoButtons = [
            [Button.inline("Download 30s Preview",
                           data=f"spotify/dl/30s_preview/{link_info['preview_url'].split('?cid')[0].replace('https://p.scdn.co/mp3-preview/', '')}")
             if link_info['preview_url'] is not None else Button.inline("Download 30s Preview",
                                                                        data=b"unavailable_feature")],
            [Button.inline("Download Track", data=f"spotify/dl/music/{link_info['track_id']}")],
            [Button.inline("Download Icon",
                           data=f"spotify/dl/icon/{link_info['image_url'].replace('https://i.scdn.co/image/', '')}")],
            [Button.inline("Artist Info", data=f"spotify/artist/{link_info['track_id']}")],
            [Button.inline("Lyrics", data=f"spotify/lyrics/{link_info['track_id']}")],
            [Button.url("Listen On Spotify", url=link_info["track_url"]),
             Button.url("Listen On Youtube", url=link_info['youtube_link']) if link_info[
                 'youtube_link'] else Button.inline("Listen On Youtube", data=b"unavailable_feature")],
            [Button.inline("Cancel", data=b"cancel")]
        ]

        caption = (
            f"**🎧 Title:** [{link_info['track_name']}]({link_info['track_url']})\n"
            f"**🎤 Artist:** [{link_info['artist_name']}]({link_info['artist_url']})\n"
            f"**💽 Album:** [{link_info['album_name']}]({link_info['album_url']})\n"
            f"**🗓 Release Year:** {link_info['release_year']}\n"
            f"**❗️ Is Local:** {is_local}\n"
            f"**🌐 ISRC:** {link_info['isrc']}\n"
            f"**🔄 Downloaded:** {await db.get_song_downloads(link_info['track_name'])} times\n\n"
            f"**Image URL:** [Click here]({link_info['image_url']})\n"
            f"**Track id:** {link_info['track_id']}\n"
        )

        try:
            await client.send_file(
                event.chat_id,
                icon_path,
                caption=caption,
                parse_mode='Markdown',
                buttons=SpotifyInfoButtons
            )
            return True
        except Exception as Err:
            print(f"Failed to send track info: {Err}")
            return False

    @staticmethod
    async def send_local_file(event, file_info, spotify_link_info, is_playlist: bool = False) -> bool:
        user_id = event.sender_id
        upload_status_message = None

        # Unpack file_info for clarity
        was_local = file_info['is_local']

        # Notify the user about local availability for faster processing, if applicable
        local_availability_message = None
        if was_local and not is_playlist:
            local_availability_message = await event.respond(
                "This track is available locally. Preparing it for you now...")

        # Provide feedback to the user during the upload process
        if not is_playlist:
            upload_status_message = await event.reply("Now uploading... Please hold on.")

        try:
            # Indicate ongoing file upload to enhance user experience
            async with event.client.action(event.chat_id, 'document'):
                # Use a ThreadPoolExecutor to upload files in parallel
                await SpotifyDownloader._upload_file(
                    event, file_info, spotify_link_info, is_playlist
                )

        except Exception as e:
            # Handle exceptions and provide feedback
            await db.set_file_processing_flag(user_id, 0)  # Reset file processing flag
            await event.respond(f"Unfortunately, uploading failed.\nReason: {e}") if not is_playlist else None
            return False  # Returning False signifies the operation didn't complete successfully

        # Clean up feedback messages
        if local_availability_message:
            await local_availability_message.delete()

        if not is_playlist:
            await upload_status_message.delete()

            # Reset file processing flag after completion
            await db.set_file_processing_flag(user_id, 0)

        await db.add_or_increment_song(spotify_link_info['track_name'])
        # Indicate successful upload operation
        return True

    @staticmethod
    async def _upload_file(event, file_info, spotify_link_info, playlist: bool = False):

        if not os.path.exists(file_info['icon_path']):
            await SpotifyDownloader.download_icon(spotify_link_info)

        # Unpack file_info for clarity
        file_path = file_info['file_path']
        icon_path = file_info['icon_path']
        video_url = file_info['video_url']

        if not playlist:
            # Use fast_upload for faster uploads
            uploaded_file = await fast_upload(
                client=event.client,
                file_location=file_path,
                reply=None,  # No need for a progress bar in this case
                name=file_info['file_name'],
                progress_bar_function=None
            )

        uploaded_file = await event.client.upload_file(uploaded_file if not playlist else file_path)
        uploaded_thumbnail = await event.client.upload_file(icon_path)

        audio_attributes = DocumentAttributeAudio(
            duration=0,
            title=f"{spotify_link_info['track_name']} - {spotify_link_info['artist_name']}",
            performer="@Spotify_YT_Downloader_BOT",
            waveform=None,
            voice=False
        )

        # Send the uploaded file as music
        media = InputMediaUploadedDocument(
            file=uploaded_file,
            thumb=uploaded_thumbnail,
            mime_type='audio/mpeg',  # Adjust the MIME type based on your file's format
            attributes=[audio_attributes],
        )

        # Send the media to the chat
        await event.client.send_file(
            event.chat_id,
            media,
            caption=(
                    f"🎵 **{spotify_link_info['track_name']}** by **{spotify_link_info['artist_name']}**\n\n"
                    f"▶️ [Listen on Spotify]({spotify_link_info['track_url']})\n"
                    + (f"🎥 [Watch on YouTube]({video_url})\n" if video_url else "")
            ),
            supports_streaming=True,
            force_document=False,
            thumb=icon_path
        )

    @staticmethod
    async def download_spotdl(event, music_quality, spotify_link_info, quite: bool = False, initial_message=None,
                              audio_option: str = "piped") -> bool | tuple[bool, Any | None] | tuple[bool, bool]:
        user_id = event.sender_id
        command = f'python3 -m spotdl --format {music_quality["format"]} --audio {audio_option} --output "{SpotifyDownloader.download_directory}" --threads {15} "{spotify_link_info["track_url"]}"'
        try:
            # Start the subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL
            )
        except Exception as e:
            await event.respond(f"Failed to download. Error: {e}")
            await db.set_file_processing_flag(user_id, 0)
            return False

        if initial_message is None and not quite:
            # Send an initial message to the user with a progress bar
            initial_message = await event.reply("SpotDL: Downloading...\nApproach: Piped")
        elif quite:
            initial_message = None

        # Function to send updates to the user
        async def send_updates(process, message):
            while True:
                # Read a line from stdout
                line = await process.stdout.readline()
                line = line.decode().strip()

                print(line)

                if not quite:
                    if audio_option == "piped":
                        await message.edit(f"SpotDL: Downloading...\nApproach: Piped\n\n{line}")
                    elif audio_option == "soundcloud":
                        await message.edit(f"SpotDL: Downloading...\nApproach: SoundCloud\n\n{line}")
                    else:
                        await message.edit(f"SpotDL: Downloading...\nApproach: YouTube\n\n{line}")

                # Check for errors
                if any(err in line for err in (
                        "LookupError", "FFmpegError", "JSONDecodeError", "ReadTimeout", "KeyError", "Forbidden",
                        "AudioProviderError")):
                    if audio_option == "piped":
                        if not quite:
                            await message.edit(
                                f"SpotDL: Downloading...\nApproach: Piped Failed, Using SoundCloud Approach.\n\n{line}")
                        return False  # Indicate that an error occurred
                    elif audio_option == "soundcloud":
                        if not quite:
                            await message.edit(
                                f"SpotDL: Downloading...\nApproach: SoundCloud Failed, Using Youtube Approach.\n\n{line}")
                        return False
                    else:
                        if not quite:
                            await message.edit(f"SpotDL: Downloading...\nApproach: All Approaches Failed.\n\n{line}")
                        return False
                elif not line:
                    return True

        success = await send_updates(process, initial_message)
        if not success and audio_option == "piped":
            if not quite:
                await initial_message.edit(
                    f"SpotDL: Downloading...\nApproach: Piped Failed, Using SoundCloud Approach.")
            return False, initial_message
        elif not success and audio_option == "soundcloud":
            if not quite:
                await initial_message.edit(
                    f"SpotDL: Downloading...\nApproach: SoundCloud Failed, Using Youtube Approach.")
            return False, initial_message
        elif not success and audio_option == "youtube":
            return False, False
        # Wait for the process to finish
        await process.wait()
        await initial_message.delete() if initial_message else None
        return True, True

    @staticmethod
    async def download_YoutubeDL(event, file_info, music_quality, is_playlist: bool = False):
        user_id = event.sender_id
        video_url = file_info['video_url']
        filename = file_info['file_name']

        download_message = None
        if not is_playlist:
            download_message = await event.respond("Downloading .")

        async def get_file_size(video_url):
            ydl_opts = {
                'format': "bestaudio",
                'default_search': 'ytsearch',
                'noplaylist': True,
                "nocheckcertificate": True,
                "quiet": True,
                "geo_bypass": True,
                'get_filesize': True  # Retrieve the file size without downloading
            }

            with YoutubeDL(ydl_opts) as ydl:
                info_dict = await asyncio.to_thread(ydl.extract_info, video_url, download=False)
                file_size = info_dict.get('filesize', None)
                return file_size

        async def download_audio(video_url, filename, music_quality):
            ydl_opts = {
                'format': "bestaudio",
                'default_search': 'ytsearch',
                'noplaylist': True,
                "nocheckcertificate": True,
                "outtmpl": f"{SpotifyDownloader.download_directory}/{filename}",
                "quiet": True,
                "addmetadata": True,
                "prefer_ffmpeg": False,
                "geo_bypass": True,
                "postprocessors": [{'key': 'FFmpegExtractAudio', 'preferredcodec': music_quality['format'],
                                    'preferredquality': music_quality['quality']}]
            }

            with YoutubeDL(ydl_opts) as ydl:
                await download_message.edit("Downloading . . .") if not is_playlist else None
                await asyncio.to_thread(ydl.extract_info, video_url, download=True)

        async def download_handler():
            file_size_task = asyncio.create_task(get_file_size(video_url))
            file_size = await file_size_task

            if file_size and file_size > SpotifyDownloader.MAXIMUM_DOWNLOAD_SIZE_MB * 1024 * 1024:
                await event.respond("Err: File size is more than 50 MB.\nSkipping download.")
                await db.set_file_processing_flag(user_id, 0)
                return False, None  # Skip the download

            if not is_playlist:
                await download_message.edit("Downloading . .")

            download_task = asyncio.create_task(download_audio(video_url, filename, music_quality))
            try:
                await download_task
                return True, download_message
            except Exception as ERR:
                await event.respond(f"Something Went Wrong Processing Your Query.")
                await db.set_file_processing_flag(user_id, 0)
                return False, download_message

        return await download_handler()

    @staticmethod
    async def download_spotify_file_and_send(event) -> bool:

        user_id = event.sender_id

        query_data = str(event.data)
        is_playlist = True if query_data.split("/")[-3] == "playlist" else False

        if is_playlist:
            spotify_link = query_data.split("/")[-2]
        else:
            spotify_link = query_data.split("/")[-1][:-1]

        if await db.get_file_processing_flag(user_id):
            await event.respond("Sorry,There is already a file being processed for you.")
            return True

        fetch_message = await event.respond("Fetching information... Please wait.")
        spotify_link_info = await SpotifyDownloader.extract_data_from_spotify_link(event, spotify_link)

        await db.set_file_processing_flag(user_id, 1)
        await fetch_message.delete()

        if spotify_link_info['type'] == "track":
            return await SpotifyDownloader.download_track(event, spotify_link_info)
        elif spotify_link_info['type'] == "playlist":
            return await SpotifyDownloader.download_playlist(event, spotify_link_info,
                                                             number_of_downloads=query_data.split("/")[-1][:-1])

    @staticmethod
    async def download_track(event, spotify_link_info, is_playlist: bool = False):

        user_id = event.sender_id

        music_quality = await db.get_user_music_quality(user_id)
        downloading_core = await db.get_user_downloading_core(user_id)

        if downloading_core == "Auto":
            spotdl = True if (spotify_link_info.get('youtube_link') is None) else False
        else:
            spotdl = downloading_core == "SpotDL"

        if (spotify_link_info.get('youtube_link', None) is None) and not spotdl:
            await db.set_file_processing_flag(user_id, 0)
            return False

        file_path, filename, is_local = SpotifyDownloader._determine_file_path(spotify_link_info, music_quality, spotdl)

        file_info = {
            "file_name": filename,
            "file_path": file_path,
            "icon_path": SpotifyDownloader._get_icon_path(spotify_link_info),
            "is_local": is_local,
            "video_url": spotify_link_info.get('youtube_link')
        }

        if is_local:
            return await SpotifyDownloader.send_local_file(event, file_info, spotify_link_info, is_playlist)
        else:
            return await SpotifyDownloader._handle_download(event, spotify_link_info, music_quality, file_info,
                                                            spotdl, is_playlist)

    @staticmethod
    async def _handle_download(event, spotify_link_info, music_quality, file_info, spotdl, is_playlist):
        file_path = file_info["file_path"]
        if not spotdl:
            result, download_message = await SpotifyDownloader.download_YoutubeDL(event, file_info, music_quality,
                                                                                  is_playlist)

            if os.path.isfile(file_path) and result:

                if not is_playlist:
                    download_message = await download_message.edit("Downloading . . . .")
                    download_message = await download_message.edit("Downloading . . . . .")

                    await download_message.delete()

                send_file_result = await SpotifyDownloader.send_local_file(event, file_info, spotify_link_info,
                                                                           is_playlist)
                return send_file_result
            else:
                return False

        else:
            result, message = await SpotifyDownloader.download_spotdl(event, music_quality, spotify_link_info)
            if not result:
                result, message = await SpotifyDownloader.download_spotdl(event, music_quality,
                                                                          spotify_link_info, is_playlist,
                                                                          message,
                                                                          audio_option="soundcloud")
                if not result:
                    result, _ = await SpotifyDownloader.download_spotdl(event, music_quality, spotify_link_info,
                                                                        is_playlist,
                                                                        message, audio_option="youtube")
            if result and message:
                return await SpotifyDownloader.send_local_file(event, file_info,
                                                               spotify_link_info, is_playlist) if result else False
            else:
                return False

    @staticmethod
    def _get_icon_path(spotify_link_info):
        icon_name = f"{spotify_link_info['track_name']} - {spotify_link_info['artist_name']}.jpeg".replace("/", " ")
        return os.path.join(SpotifyDownloader.download_icon_directory, icon_name)

    @staticmethod
    def _determine_file_path(spotify_link_info, music_quality, spotdl):
        artist_names = spotify_link_info['artist_name'].split(', ')
        for r in range(1, len(artist_names) + 1):
            for combination in combinations(artist_names, r):
                filename = f"{', '.join(combination)} - {spotify_link_info['track_name']}".replace("/", "")
                filename += f"-{music_quality['quality']}" if not spotdl else ""
                file_path = os.path.join(SpotifyDownloader.download_directory, f"{filename}.{music_quality['format']}")
                if os.path.isfile(file_path):
                    return file_path, filename, True
        filename = f"{spotify_link_info['artist_name']} - {spotify_link_info['track_name']}".replace("/", "")
        filename += f"-{music_quality['quality']}" if not spotdl else ""
        return os.path.join(SpotifyDownloader.download_directory,
                            f"{filename}.{music_quality['format']}"), filename, False

    @staticmethod
    async def download_playlist(event, spotify_link_info, number_of_downloads: str):
        playlist_id = spotify_link_info["playlist_id"]
        music_quality = None

        await db.set_file_processing_flag(event.sender_id, 1)

        if number_of_downloads == "10":
            tracks_info = await SpotifyDownloader.get_playlist_tracks(playlist_id)
        elif number_of_downloads == "all":
            music_quality = await db.get_user_music_quality(event.sender_id)
            new_music_quality = {'format': "mp3", 'quality': 320}
            await db.set_user_music_quality(event.sender_id, new_music_quality)
            tracks_info = await SpotifyDownloader.get_playlist_tracks(playlist_id, get_all=True)
        else:
            await db.set_file_processing_flag(event.sender_id, 0)
            return await event.respond("Sorry, Something went wrong.\ntry again later.")

        start_message = await event.respond("Checking the playlist ....")

        batch_size = 10
        track_batches = [tracks_info[i:i + batch_size] for i in range(0, len(tracks_info), batch_size)]
        download_tasks = []

        await start_message.edit("Sending musics.... Please Hold on.")

        for batch in track_batches:
            # Download tracks in the current batch concurrently
            download_tasks.extend([SpotifyDownloader.download_track(event,
                                                                    await SpotifyDownloader.extract_data_from_spotify_link(
                                                                        event, track["track_id"]), is_playlist=True) for
                                   track in batch])

            # Wait for all downloads in the batch to complete before proceeding to the next batch
            await asyncio.gather(*download_tasks)
            download_tasks.clear()  # Clear completed tasks

        await start_message.delete()
        if music_quality is not None:
            await db.set_user_music_quality(event.sender_id, music_quality)
        await db.set_file_processing_flag(event.sender_id, 0)
        return await event.respond("Enjoy!\n\nOur bot is OpenSource.", buttons=Buttons.source_code_button)

    @staticmethod
    async def search_spotify_based_on_user_input(query, limit=10):
        results = SpotifyDownloader.spotify_account.search(q=query, limit=limit)

        extracted_details = []

        for result in results['tracks']['items']:
            # Extracting track name, artist's name, release year, and track ID
            track_name = result['name']
            artist_name = result['artists'][0]['name']  # Assuming the first artist is the primary one
            release_year = result['album']['release_date']
            track_id = result['id']

            # Append the extracted details to the list
            extracted_details.append({
                "track_name": track_name,
                "artist_name": artist_name,
                "release_year": release_year.split("-")[0],
                "track_id": track_id
            })

        return extracted_details

    @staticmethod
    async def send_30s_preview(event):
        try:
            query_data = str(event.data)
            preview_url = "https://p.scdn.co/mp3-preview/" + query_data.split("/")[-1][:-1]
            await event.respond(file=preview_url)
        except Exception as Err:
            await event.respond(f"Sorry, Something went wrong:\nError\n{str(Err)}")

    @staticmethod
    async def send_artists_info(event):
        query_data = str(event.data)
        track_id = query_data.split("/")[-1][:-1]
        track_info = SpotifyDownloader.spotify_account.track(track_id=track_id)
        artist_ids = [artist["id"] for artist in track_info['artists']]
        artist_details = []

        def format_number(number):
            if number >= 1000000000:
                return f"{number // 1000000000}.{(number % 1000000000) // 100000000}B"
            elif number >= 1000000:
                return f"{number // 1000000}.{(number % 1000000) // 100000}M"
            elif number >= 1000:
                return f"{number // 1000}.{(number % 1000) // 100}K"
            else:
                return str(number)

        for artist_id in artist_ids:
            artist = SpotifyDownloader.spotify_account.artist(artist_id.replace("'", ""))
            artist_details.append({
                'name': artist['name'],
                'followers': format_number(artist['followers']['total']),
                'genres': artist['genres'],
                'popularity': artist['popularity'],
                'image_url': artist['images'][0]['url'] if artist['images'] else None,
                'external_url': artist['external_urls']['spotify']
            })

        # Create a professional artist info message with more details and formatting
        message = "🎤 <b>Artists Information</b> :\n\n"
        for artist in artist_details:
            message += f"🌟 <b>Artist Name:</b> {artist['name']}\n"
            message += f"👥 <b>Followers:</b> {artist['followers']}\n"
            message += f"🎵 <b>Genres:</b> {', '.join(artist['genres'])}\n"
            message += f"📈 <b>Popularity:</b> {artist['popularity']}\n"
            if artist['image_url']:
                message += f"\n🖼️ <b>Image:</b> <a href='{artist['image_url']}'>Image Url</a>\n"
            message += f"🔗 <b>Spotify URL:</b> <a href='{artist['external_url']}'>Spotify Link</a>\n\n"
            message += "───────────\n\n"

        # Create buttons with URLs
        artist_buttons = [
            [Button.url(f"🎧 {artist['name']}", artist['external_url'])]
            for artist in artist_details
        ]
        artist_buttons.append([Button.inline("Remove", data='cancel')])

        await event.respond(message, parse_mode='html', buttons=artist_buttons)

    @staticmethod
    async def send_music_lyrics(event):
        MAX_MESSAGE_LENGTH = 4096  # Telegram's maximum message length
        SECTION_HEADER_PATTERN = r'\[.+?\]'  # Pattern to match section headers

        query_data = str(event.data)
        track_id = query_data.split("/")[-1][:-1]
        track_info = SpotifyDownloader.spotify_account.track(track_id=track_id)
        artist_names = ",".join(artist['name'] for artist in track_info['artists'])

        waiting_message = await event.respond("Searching For Lyrics in Genius ....")
        song = SpotifyDownloader.genius.search_song(
            f""" "{track_info['name']}"+"{artist_names}" """)
        if song:
            await waiting_message.delete()
            lyrics = song.lyrics

            if not lyrics:
                error_message = "Sorry, I couldn't find the lyrics for this track."
                return await event.respond(error_message)

            # Remove 'Embed' and the first line of the lyrics
            lyrics = song.lyrics.strip().split('\n', 1)[-1]
            lyrics = lyrics.replace('Embed', '').strip()

            metadata = f"**Song:** {track_info['name']}\n**Artist:** {artist_names}\n\n"

            # Split the lyrics into multiple messages if necessary
            lyrics_chunks = []
            current_chunk = ""
            section_lines = []
            for line in lyrics.split('\n'):
                if re.match(SECTION_HEADER_PATTERN, line) or not section_lines:
                    if section_lines:
                        section_text = '\n'.join(section_lines)
                        if len(current_chunk) + len(section_text) + 2 <= MAX_MESSAGE_LENGTH:
                            current_chunk += section_text + "\n"
                        else:
                            lyrics_chunks.append(f"```{current_chunk.strip()}```")
                            current_chunk = section_text + "\n"
                    section_lines = [line]
                else:
                    section_lines.append(line)

            # Add the last section to the chunks
            if section_lines:
                section_text = '\n'.join(section_lines)
                if len(current_chunk) + len(section_text) + 2 <= MAX_MESSAGE_LENGTH:
                    current_chunk += section_text + "\n"
                else:
                    lyrics_chunks.append(f"```{current_chunk.strip()}```")
                    current_chunk = section_text + "\n"
            if current_chunk:
                lyrics_chunks.append(f"```{current_chunk.strip()}```")

            for i, chunk in enumerate(lyrics_chunks, start=1):
                page_header = f"Page {i}/{len(lyrics_chunks)}\n"
                if chunk == "``````":
                    await waiting_message.delete() if waiting_message is not None else None
                    error_message = "Sorry, I couldn't find the lyrics for this track."
                    return await event.respond(error_message)
                message = metadata + chunk + page_header
                await event.respond(message, buttons=[Button.inline("Remove", data='cancel')])
        else:
            await waiting_message.delete()
            error_message = "Sorry, I couldn't find the lyrics for this track."
            return await event.respond(error_message)

    @staticmethod
    async def send_music_icon(event):
        try:
            query_data = str(event.data)
            image_url = "https://i.scdn.co/image/" + query_data.split("/")[-1][:-1]
            await event.respond(file=image_url)
        except Exception:
            await event.reply("An error occurred while processing your request. Please try again later.")

    @staticmethod
    async def get_playlist_tracks(playlist_id, limit: int = 10, get_all: bool = False):

        # Retrieve playlist tracks
        if get_all:
            results = SpotifyDownloader.spotify_account.playlist_items(playlist_id)
        else:
            results = SpotifyDownloader.spotify_account.playlist_items(playlist_id, limit=limit)

        extracted_details = []
        for item in results['items']:
            track = item['track']
            # Extracting track name, artist's name, release year, and track ID
            track_name = track['name']
            artist_name = track['artists'][0]['name']  # Assuming the first artist is the primary one
            release_year = track['album']['release_date']
            track_id = track['id']

            # Append the extracted details to the list
            extracted_details.append({
                "track_name": track_name,
                "artist_name": artist_name,
                "release_year": release_year.split("-")[0],  # Format release year as YYYY
                "track_id": track_id
            })

        return extracted_details
