from utils import YoutubeDL, re, lru_cache, hashlib, InputMediaPhotoExternal, db
from utils import os, InputMediaUploadedDocument, DocumentAttributeVideo, fast_upload
from utils import DocumentAttributeAudio
from run import Button, BotState, Buttons


class YoutubeDownloader():

    @classmethod
    def initialize(cls):
        cls.MAXIMUM_DOWNLOAD_SIZE_MB = 100
        cls.DOWNLOAD_DIR = 'repository/Youtube'

        if not os.path.isdir(cls.DOWNLOAD_DIR):
            os.mkdir(cls.DOWNLOAD_DIR)

    @lru_cache(maxsize=128)  # Cache the last 128 screenshots
    def get_file_path(url, format_id, extension):
        url = url + format_id + extension
        url_hash = hashlib.blake2b(url.encode()).hexdigest()
        filename = f"{url_hash}.{extension}"
        return os.path.join(YoutubeDownloader.DOWNLOAD_DIR, filename)

    @staticmethod
    def is_youtube_link(url):
        youtube_patterns = [
            r'(https?\:\/\/)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11}).*',
            r'(https?\:\/\/)?www\.youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})(?!.*list=)',
            r'(https?\:\/\/)?youtu\.be\/([a-zA-Z0-9_-]{11})(?!.*list=)',
            r'(https?\:\/\/)?www\.youtube\.com\/embed\/([a-zA-Z0-9_-]{11})(?!.*list=)',
            r'(https?\:\/\/)?www\.youtube\.com\/v\/([a-zA-Z0-9_-]{11})(?!.*list=)',
            r'(https?\:\/\/)?www\.youtube\.com\/[^\/]+\?v=([a-zA-Z0-9_-]{11})(?!.*list=)',
        ]
        for pattern in youtube_patterns:
            match = re.match(pattern, url)
            if match:
                return True
        return False

    @staticmethod
    def extract_youtube_url(text):
        # Regular expression patterns to match different types of YouTube URLs
        youtube_patterns = [
            r'(https?\:\/\/)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11}).*',
            r'(https?\:\/\/)?www\.youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})(?!.*list=)',
            r'(https?\:\/\/)?youtu\.be\/([a-zA-Z0-9_-]{11})(?!.*list=)',
            r'(https?\:\/\/)?www\.youtube\.com\/embed\/([a-zA-Z0-9_-]{11})(?!.*list=)',
            r'(https?\:\/\/)?www\.youtube\.com\/v\/([a-zA-Z0-9_-]{11})(?!.*list=)',
            r'(https?\:\/\/)?www\.youtube\.com\/[^\/]+\?v=([a-zA-Z0-9_-]{11})(?!.*list=)',
        ]

        for pattern in youtube_patterns:
            match = re.search(pattern, text)
            if match:
                video_id = match.group(2)
                if 'youtube.com/shorts/' in match.group(0):
                    return f'https://www.youtube.com/shorts/{video_id}'
                else:
                    return f'https://www.youtube.com/watch?v={video_id}'

        return None

    @staticmethod
    def _get_formats(url):
        ydl_opts = {
            'listformats': True,
            'no_warnings': True,
            'quiet': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = info['formats']
        return formats

    @staticmethod
    async def send_youtube_info(client, event, youtube_link):
        url = youtube_link
        video_id = youtube_link.replace("https://www.youtube.com/watch?v=", "")
        user_id = event.sender_id
        formats = YoutubeDownloader._get_formats(url)

        # Download the video thumbnail
        with YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            thumbnail_url = info['thumbnail']
            duration = info.get('duration', 'Unknown')
            width = info.get('width', 'Unknown')
            height = info.get('height', 'Unknown')

        # Create buttons for each format
        video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
        audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']

        video_buttons = []
        counter = 0
        for f in reversed(video_formats):
            extension = f['ext']
            resolution = f.get('resolution')
            filesize = f.get('filesize') if f.get('filesize') is not None else f.get('filesize_approx')
            if resolution and filesize and counter < 5:
                filesize = f"{filesize / 1024 / 1024:.2f} MB"
                button = [Button.inline(f"{extension} - {resolution} - {filesize}",
                                        data=f"yt/dl/{video_id}/_{width}_{height}_{duration}_{extension}_video_{f['format_id']}_{filesize}")]
                if not button in video_buttons:
                    video_buttons.append(button)
                    counter += 1

        audio_buttons = []
        counter = 0
        for f in reversed(audio_formats):
            extension = f['ext']
            resolution = f.get('resolution')
            filesize = f.get('filesize') if f.get('filesize') is not None else f.get('filesize_approx')
            if resolution and filesize and counter < 5:
                filesize = f"{filesize / 1024 / 1024:.2f} MB"
                button = [Button.inline(f"{extension} - {resolution} - {filesize}",
                                        data=f"yt/dl/{video_id}/_{width}_{height}_{duration}_{extension}_audio_{f['format_id']}_{filesize}")]
                if not button in audio_buttons:
                    audio_buttons.append(button)
                    counter += 1

        buttons = video_buttons + audio_buttons
        buttons.append(Buttons.cancel_button)

        # Set thumbnail attributes
        thumbnail = InputMediaPhotoExternal(thumbnail_url)
        thumbnail.ttl_seconds = 0

        # Send the thumbnail as a picture with format buttons
        youtube_search = await client.send_file(event.chat_id, file=thumbnail, caption="Select a format to download:",
                                                buttons=buttons)
        await BotState.set_youtube_search(user_id, youtube_search)

    @staticmethod
    async def download_and_send_yt_file(client, event):
        user_id = event.sender_id

        if await db.get_file_processing_flag(user_id):
            return await event.respond("Sorry, There is already a file being processed for you.")

        data = event.data.decode('utf-8')
        parts = data.split('_')
        if len(parts) == 8:
            width = parts[1]
            height = parts[2]
            duration = parts[3]
            extension = parts[4]
            video_or_audio = parts[5]
            format_id = parts[6]
            filesize = parts[7].replace(" MB", "")
            video_id = parts[0].split("/")[-2]

            if float(filesize) > YoutubeDownloader.MAXIMUM_DOWNLOAD_SIZE_MB:
                return await event.answer(
                    f"⚠️ The file size is more than {YoutubeDownloader.MAXIMUM_DOWNLOAD_SIZE_MB}MB.\nTo proceed with the download, please consider upgrading to a premium account. ",
                    alert=True)

            await db.set_file_processing_flag(user_id, is_processing=True)

            local_availability_message = None
            url = "https://www.youtube.com/watch?v=" + video_id

            path = YoutubeDownloader.get_file_path(url, format_id, extension)

            if not os.path.isfile(path):
                downloading_message = await event.respond("Downloading the file for you ...")
                ydl_opts = {
                    'format': format_id,
                    'outtmpl': path,
                    'quiet': True,
                }

                with YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(url)

                await downloading_message.delete()
            else:
                local_availability_message = await event.respond(
                    "This file is available locally. Preparing it for you now...")

            upload_message = await event.respond("Uploading ... Please hold on.")

            try:
                # Indicate ongoing file upload to enhance user experience
                async with client.action(event.chat_id, 'document'):

                    media = await fast_upload(
                        client=client,
                        file_location=path,
                        reply=None,  # No need for a progress bar in this case
                        name=path,
                        progress_bar_function=None
                    )

                    if (extension == "mp4" or extension == "webm") and video_or_audio == "video":

                        uploaded_file = await client.upload_file(media)

                        # Prepare the video attributes
                        video_attributes = DocumentAttributeVideo(
                            duration=int(duration),
                            w=int(width),
                            h=int(height),
                            supports_streaming=True,
                            # Add other attributes as needed
                        )

                        media = InputMediaUploadedDocument(
                            file=uploaded_file,
                            thumb=None,
                            mime_type='video/mp4' if extension == "mp4" else 'video/webm',
                            attributes=[video_attributes],
                        )

                    elif (extension == "m4a" or extension == "webm") and video_or_audio == "audio":

                        uploaded_file = await client.upload_file(media)

                        # Prepare the audio attributes
                        audio_attributes = DocumentAttributeAudio(
                            duration=int(duration),  # Duration in seconds
                            title="Downloaded Audio",  # Replace with actual title
                            performer="@Spotify_YT_Downloader_BOT",  # Replace with actual performer
                            # Add other attributes as needed
                        )

                        media = InputMediaUploadedDocument(
                            file=uploaded_file,
                            thumb=None,  # Assuming you have a thumbnail or will set it later
                            mime_type='audio/m4a' if extension == "m4a" else 'audio/webm',
                            attributes=[audio_attributes],
                        )

                    # Send the downloaded file
                    await client.send_file(event.chat_id, file=media,
                                           caption=f"Enjoy!\n@Spotify_YT_Downloader_BOT",
                                           force_document=False,
                                           # This ensures the file is sent as a video/voice if possible
                                           supports_streaming=True  # This enables video streaming
                                           )

                await upload_message.delete()
                await local_availability_message.delete() if local_availability_message else None
                await db.set_file_processing_flag(user_id, is_processing=False)

            except Exception as Err:
                await db.set_file_processing_flag(user_id, is_processing=False)
                return await event.respond(f"Sorry There was a problem with your request.\nReason:{str(Err)}")
        else:
            await event.answer("Invalid button data.")
