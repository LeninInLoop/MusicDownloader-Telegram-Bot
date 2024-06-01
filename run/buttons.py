from run import Button


class Buttons:
    source_code_button = [
        Button.url("Source Code", url="https://github.com/AdibNikjou/MusicDownloader-Telegram-Bot")]

    main_menu_buttons = [
        [Button.inline("Instructions", b"instructions"), Button.inline("Settings", b"setting")],
        source_code_button,
        [Button.url("Contact Creator", url="telegram.me/adibnikjou")],
    ]

    back_button = Button.inline("<< Back To Main Menu", b"back")

    setting_button = [
        [Button.inline("Core", b"setting/core")],
        [Button.inline("Quality", b"setting/quality")],
        [Button.inline("TweetCapture", b"setting/TweetCapture")],
        [Button.inline("Subscription", b"setting/subscription")],
        [back_button]
    ]

    back_button_to_setting = Button.inline("<< Back", b"setting/back")

    cancel_broadcast_button = [Button.inline("Cancel BroadCast", data=b"admin/cancel_broadcast")]

    admins_buttons = [
        [Button.inline("Broadcast", b"admin/broadcast")],
        [Button.inline("Stats", b"admin/stats")],
        [Button.inline("Cancel", b"cancel")]
    ]

    broadcast_options_buttons = [
        [Button.inline("Broadcast To All Members", b"admin/broadcast/all")],
        [Button.inline("Broadcast To Subscribers Only", b"admin/broadcast/subs")],
        [Button.inline("Broadcast To Specified Users Only", b"admin/broadcast/specified")],
        [Button.inline("Cancel", b"cancel")]
    ]

    continue_button = [Button.inline("Continue", data='membership/continue')]

    cancel_subscription_button_quite = [Button.inline("UnSubscribe", b"setting/subscription/cancel/quite")]

    cancel_button = [Button.inline("Cancel", b"cancel")]

    @staticmethod
    def get_tweet_capture_setting_buttons(mode):
        match mode:
            case "0":
                return [
                    [Button.inline("🔹 Light mode", data=b"setting/TweetCapture/mode/0")],
                    [Button.inline("Dark mode", data=b"setting/TweetCapture/mode/1")],
                    [Button.inline("Black mode", data=b"setting/TweetCapture/mode/2")],
                    [Buttons.back_button, Buttons.back_button_to_setting]
                ]
            case "1":
                return [
                    [Button.inline("Light mode", data=b"setting/TweetCapture/mode/0")],
                    [Button.inline("🔹 Dark mode", data=b"setting/TweetCapture/mode/1")],
                    [Button.inline("Black mode", data=b"setting/TweetCapture/mode/2")],
                    [Buttons.back_button, Buttons.back_button_to_setting]
                ]
            case "2":
                return [
                    [Button.inline("Light mode", data=b"setting/TweetCapture/mode/0")],
                    [Button.inline("Dark mode", data=b"setting/TweetCapture/mode/1")],
                    [Button.inline("🔹 Black mode", data=b"setting/TweetCapture/mode/2")],
                    [Buttons.back_button, Buttons.back_button_to_setting]
                ]

    @staticmethod
    def get_subscription_setting_buttons(subscription):
        if subscription:
            return [
                [Button.inline("UnSubscribe", data=b"setting/subscription/cancel")],
                [Buttons.back_button, Buttons.back_button_to_setting]
            ]
        else:
            return [
                [Button.inline("Subscribe", data=b"setting/subscription/add")],
                [Buttons.back_button, Buttons.back_button_to_setting]
            ]

    @staticmethod
    def get_core_setting_buttons(core):
        match core:
            case "Auto":
                return [
                    [Button.inline("🔸 Auto", data=b"setting/core/auto")],
                    [Button.inline("YoutubeDL", b"setting/core/youtubedl")],
                    [Button.inline("SpotDL", b"setting/core/spotdl")],
                    [Buttons.back_button, Buttons.back_button_to_setting],
                ]
            case "SpotDL":
                return [
                    [Button.inline("Auto", data=b"setting/core/auto")],
                    [Button.inline("YoutubeDL", b"setting/core/youtubedl")],
                    [Button.inline("🔸 SpotDL", b"setting/core/spotdl")],
                    [Buttons.back_button, Buttons.back_button_to_setting],
                ]
            case "YoutubeDL":
                return [
                    [Button.inline("Auto", data=b"setting/core/auto")],
                    [Button.inline("🔸 YoutubeDL", b"setting/core/youtubedl")],
                    [Button.inline("SpotDL", b"setting/core/spotdl")],
                    [Buttons.back_button, Buttons.back_button_to_setting],
                ]

    @staticmethod
    def get_quality_setting_buttons(music_quality):
        if isinstance(music_quality['quality'], int):
            music_quality['quality'] = str(music_quality['quality'])

        match music_quality:
            case {'format': 'flac', 'quality': "693"}:
                return [
                    [Button.inline("◽️ Flac", b"setting/quality/flac")],
                    [Button.inline("Mp3 (320)", b"setting/quality/mp3/320")],
                    [Button.inline("Mp3 (128)", b"setting/quality/mp3/128")],
                    [Buttons.back_button, Buttons.back_button_to_setting],
                ]

            case {'format': "mp3", 'quality': "320"}:
                return [
                    [Button.inline("Flac", b"setting/quality/flac")],
                    [Button.inline("◽️ Mp3 (320)", b"setting/quality/mp3/320")],
                    [Button.inline("Mp3 (128)", b"setting/quality/mp3/128")],
                    [Buttons.back_button, Buttons.back_button_to_setting],
                ]

            case {'format': "mp3", 'quality': "128"}:
                return [
                    [Button.inline("Flac", b"setting/quality/flac")],
                    [Button.inline("Mp3 (320)", b"setting/quality/mp3/320")],
                    [Button.inline("◽️ Mp3 (128)", b"setting/quality/mp3/128")],
                    [Buttons.back_button, Buttons.back_button_to_setting],
                ]

    @staticmethod
    def get_search_result_buttons(sanitized_query, search_result, page=1) -> list:

        button_list = [
            [Button.inline(f"🎧 {details['track_name']} - {details['artist_name']} 🎧 ({details['release_year']})",
                           data=f"spotify/info/{details['track_id']}")]
            for details in search_result[(page-1) * 10:]
        ]

        if len(search_result) > 1:
            button_list.append([Button.inline("Previous Page", f"prev_page/s/{sanitized_query}/page/{page - 1}"),
                                Button.inline("Next Page", f"next_page/s/{sanitized_query}/page/{page + 1}")])
        button_list.append([Button.inline("Cancel", b"cancel")])

        return button_list

    @staticmethod
    def get_playlist_search_buttons(playlist_id, search_result, page=1) -> list:
        button_list = [
            [Button.inline(f"🎧 {details['track_name']} - {details['artist_name']} 🎧 ({details['release_year']})",
                           data=f"spotify/info/{details['track_id']}")]
            for details in search_result[(page-1) * 10:]
        ]

        if len(search_result) > 1:
            button_list.append([Button.inline("Previous Page", f"prev_page/p/{playlist_id}/page/{page - 1}"),
                                Button.inline("Next Page", f"next_page/p/{playlist_id}/page/{page + 1}")])
        button_list.append([Button.inline("Cancel", b"cancel")])

        return button_list
