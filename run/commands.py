from utils import time, os
from utils import db, asyncio
from .buttons import buttons
from utils import BroadcastManager

ADMIN_USER_IDS = [int(id) for id in os.getenv('ADMIN_USER_IDS').split(',')]

class commands:
    @staticmethod
    async def start(event):
        sender_name = event.sender.first_name
        user_id = event.sender_id
        
        user_settings = await db.get_user_settings(user_id)
        if user_settings[0] == None and user_settings[1] == None:
            await db.save_user_settings(user_id, db.default_music_quality, db.default_downloading_core)
        await respond_based_on_channel_membership(event,f"""Hey {sender_name}!👋 \n{Bot.start_message}""", buttons=buttons.main_menu_buttons)
        
    @staticmethod
    async def handle_stats_command(event):
        if event.sender_id not in ADMIN_USER_IDS:
            return
        number_of_users = await db.count_all_user_ids()
        number_of_subscribed = await db.count_subscribed_users()
        number_of_unsubscribed = number_of_users - number_of_subscribed
        await event.respond(f"""Number of Users: {number_of_users}
    Number of Subscribed Users: {number_of_subscribed}
    Number of Unsubscribed Users: {number_of_unsubscribed}""")
        
    @staticmethod
    async def handle_admin_command(event):
        if event.sender_id not in ADMIN_USER_IDS:
            return
        await send_message_and_store_id(event,"Admin commands:", buttons=buttons.admins_buttons)
            
    @staticmethod
    async def handle_ping_command(event):
        start_time = time.time()
        ping_message = await event.reply('Pong!')
        end_time = time.time()
        response_time = (end_time - start_time)*1000
        await ping_message.edit(f'Pong!\nResponse time: {response_time:3.3f} ms')
        
    @staticmethod
    async def handle_core_command(event):
        await update_bot_version_user_season(event)
        user_id = event.sender_id
        if await db.get_user_updated_flag(user_id):
            user_setting = await db.get_user_settings(user_id)
            await respond_based_on_channel_membership(event, Bot.core_selection_message+f"\nCore: {user_setting[1]}",
                            buttons=buttons.core_setting_buttons)

    @staticmethod
    async def handle_quality_command(event):
        await update_bot_version_user_season(event)
        user_id = event.sender_id
        if await db.get_user_updated_flag(user_id):
            user_setting = await db.get_user_settings(user_id)
            await respond_based_on_channel_membership(event, f"Your Quality Setting:\nFormat: {user_setting[0]['format']}\nQuality: {user_setting[0]['quality']}\n\nQualities Available :",
                            buttons=buttons.quality_setting_buttons)

    @staticmethod
    async def handle_help_command(event):
        await update_bot_version_user_season(event)
        user_id = event.sender_id
        if await db.get_user_updated_flag(user_id):
            await respond_based_on_channel_membership(event,buttons.instruction_message)
            
    @staticmethod
    async def handle_unsubscribe_command(event):
    # Check if the user is subscribed
        await update_bot_version_user_season(event)
        user_id = event.sender_id
        if await db.get_user_updated_flag(user_id):
            if not await db.is_user_subscribed(user_id):
                await respond_based_on_channel_membership(event,"You are not currently subscribed.")
                return
            await db.remove_subscribed_user(user_id)
            await respond_based_on_channel_membership(event,"You have successfully unsubscribed.")
            
    @staticmethod
    async def handle_subscribe_command(event):
    # Check if the user is already subscribed
        await update_bot_version_user_season(event)
        user_id = event.sender_id
        if await db.get_user_updated_flag(user_id):
            if await db.is_user_subscribed(user_id):
                await respond_based_on_channel_membership(event,"You are already subscribed.")
                return
            await db.add_subscribed_user(user_id)
            await respond_based_on_channel_membership(event,"You have successfully subscribed.")

    @staticmethod
    async def handle_settings_command(event):
        await update_bot_version_user_season(event)
        if await db.get_user_updated_flag(event.sender_id):
            await respond_based_on_channel_membership(event,"Settings :", buttons=buttons.setting_button)
            
    @staticmethod
    async def handle_broadcast_command(event):
        # ... implementation of the handle_*_command methods ...
        
        user_id = event.sender_id
        if user_id not in ADMIN_USER_IDS:
                    return
                
        Bot.cancel_broadcast[user_id] = False
        Bot.admin_broadcast[user_id] = True
        if event.message.text.startswith('/broadcast_to_all'):
            await BroadcastManager.add_all_users_to_temp()
            
        elif event.message.text.startswith('/broadcast'):
            command_parts = event.message.text.split(' ',  1)

            if len(command_parts) == 1:
                pass
            elif len(command_parts) <  2 or not command_parts[1].startswith('(') or not command_parts[1].endswith(')'):
                await event.respond("Invalid command format. Use /broadcast (user_id1,user_id2,...)")
                Bot.admin_broadcast[user_id] = False
                Bot.admin_message_to_send[user_id] = None
                return

            if len(command_parts) != 1:
                await BroadcastManager.remove_all_users_from_temp()
                user_ids_str = command_parts[1][1:-1]  # Remove the parentheses
                specified_user_ids = [int(user_id) for user_id in user_ids_str.split(',')]
                for user_id in specified_user_ids:
                    await BroadcastManager.add_user_to_temp(user_id)
            Bot.admin_message_to_send[user_id] = None
        time = 60 
        time_to_send = await event.respond(f"You've Got {time} seconds to send your message",buttons=buttons.cancel_broadcast_button)

        for remaining_time in range(time-1, 0, -1):
            # Edit the message to show the new time
            await time_to_send.edit(f"You've Got {remaining_time} seconds to send your message")
            if Bot.cancel_broadcast[user_id]:
                await time_to_send.edit("BroadCast Cancelled by User.", buttons = None)
                break
            elif Bot.admin_message_to_send[user_id] != None:
                break
            await asyncio.sleep(1)
        
        # Check if the message is "/broadcast_to_all"
        if Bot.admin_message_to_send[user_id]== None and Bot.cancel_broadcast[user_id] != True:
            await event.respond("There is nothing to send")
            Bot.admin_broadcast[user_id] = False
            Bot.admin_message_to_send[user_id] = None
            await BroadcastManager.remove_all_users_from_temp()
            return
        
        cancel_subscription_button = Button.inline("Cancel Subscription To News", b"setting/subscription/cancel/quite")
        try:
            if not Bot.cancel_broadcast[user_id] and len(command_parts) != 1:
                await BroadcastManager.broadcast_message_to_temp_members(Bot.Client, Bot.admin_message_to_send[user_id])
                await event.respond("Broadcast initiated.")
            elif not Bot.cancel_broadcast[user_id] and len(command_parts) == 1:
                await BroadcastManager.broadcast_message_to_sub_members(Bot.Client, Bot.admin_message_to_send[user_id], cancel_subscription_button)
                await event.respond("Broadcast initiated.")
        except:
            try:
                if not Bot.cancel_broadcast[user_id]:
                    await BroadcastManager.broadcast_message_to_temp_members(Bot.Client, Bot.admin_message_to_send[user_id])
                    await event.respond("Broadcast initiated.")
            except Exception as e:
                await event.respond(f"Broadcast Failed: {str(e)}")
                Bot.admin_broadcast[user_id] = False
                Bot.admin_message_to_send[user_id] = None
                await BroadcastManager.remove_all_users_from_temp()
                
        await BroadcastManager.remove_all_users_from_temp()
        Bot.admin_broadcast[user_id] = False
        Bot.admin_message_to_send[user_id] = None