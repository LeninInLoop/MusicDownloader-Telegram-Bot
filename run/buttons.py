from run import Button

class Buttons:
    
    source_code_button = [Button.url("Source Code", url="https://github.com/AdibNikjou/telegram_spotify_downloader")]
    
    main_menu_buttons = [
        [Button.inline("Settings", b"setting"),Button.inline("Instructions", b"instructions")],
        source_code_button,
        [Button.inline("Contact Creator", b"contact_creator")],
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

    quality_setting_buttons = [
        [Button.inline("flac", b"setting/quality/flac")],
        [Button.inline("mp3-320", b"setting/quality/mp3/320")],
        [Button.inline("mp3-128", b"setting/quality/mp3/128")],
        [back_button, back_button_to_setting],
    ]

    core_setting_buttons = [
        [Button.inline("Auto", data=b"setting/core/auto")],
        [Button.inline("YoutubeDL", b"setting/core/youtubedl")],
        [Button.inline("SpotDL", b"setting/core/spotdl")],
        [back_button, back_button_to_setting],
    ]

    subscription_setting_buttons = [
        [Button.inline("Subscribe",data=b"setting/subscription/add")],
        [Button.inline("Cancel Subscription",data=b"setting/subscription/cancel")],
        [back_button, back_button_to_setting]
    ]

    tweet_capture_setting_buttons = [
        [Button.inline("Mode 0",data=b"setting/TweetCapture/mode_0")],
        [Button.inline("Mode 1",data=b"setting/TweetCapture/mode_1")],
        [Button.inline("Mode 2",data=b"setting/TweetCapture/mode_2")],
        [back_button, back_button_to_setting]
    ]
    
    cancel_broadcast_button = [Button.inline("Cancel BroadCast",data=b"admin/cancel_broadcast")]

    admins_buttons  =  [
                [Button.inline("Broadcast", b"admin/broadcast")],
                [Button.inline("Stats", b"admin/stats")],
                [Button.inline("Cancel",b"cancel")]
    ]

    broadcast_options_buttons = [
        [Button.inline("Broadcast To All Members", b"admin/broadcast/all")],
        [Button.inline("Broadcast To Subscribers Only", b"admin/broadcast/subs")],
        [Button.inline("Broadcast To Specified Users Only", b"admin/broadcast/specified")],
        [Button.inline("Cancel",b"cancel")]
    ]
    
    continue_button = [Button.inline("Continue",data='membership/continue')]
    
    cancel_subscription_button_quite = [Button.inline("Cancel Subscription To News", b"setting/subscription/cancel/quite")]
    
    cancel_button = [Button.inline("Cancel", b"cancel")]
    
