import asyncio
from database import db

class BroadcastManager:

    @staticmethod
    async def broadcast_message_to_sub_members(client, message):
        """
        Sends a message to all users in the broadcast list.
        """
        user_ids = db.get_subscribed_user_ids()
        for user_id in user_ids:
            try:
                await client.send_message(user_id, message)
            except Exception as e:
                print(f"Failed to send message to user {user_id}: {e}")
                # Optionally, retry sending the message or log the failure for later review

    @staticmethod
    async def broadcast_message_to_temp_members(client, message):
        """
        Sends a message to all users in the broadcast list.
        """
        user_ids = db.get_temporary_subscribed_user_ids()
        for user_id in user_ids:
            try:
                await client.send_message(user_id, message)
            except Exception as e:
                print(f"Failed to send message to user {user_id}: {e}")
                # Optionally, retry sending the message or log the failure for later review
                
    @staticmethod
    def add_sub_user(user_id):
        """
        Adds a user to the broadcast list.
        """
        db.add_subscribed_user(user_id)  # Removed 'await'

    @staticmethod
    def remove_sub_user(user_id):
        """
        Removes a user from the broadcast list.
        """
        db.remove_subscribed_user(user_id)  # Removed 'await'

    @staticmethod
    async def get_all_sub_user_ids():
        """
        Returns all user IDs in the broadcast list.
        """
        return db.get_subscribed_user_ids()
    
    @staticmethod
    async def clear_user_ids():
        """
        Clears the broadcast list by removing all user IDs.
        """
        db.clear_subscribed_users()

    @staticmethod
    def get_temporary_subscribed_user_ids():
        """
        Returns all user IDs in the subscriptions list that are marked as temporarily subscribed.
        """
        return db.get_temporary_subscribed_user_ids()
   
    @staticmethod
    async def add_all_users_to_temp():
        """
        Adds all users from the database to the broadcast list.
        """
        # Mark the current subscribed users as temporarily added for the broadcast
        db.mark_temporary_subscriptions()
         
    @staticmethod
    async def remove_all_users_from_temp():
        """
        Remove all users from the database to the broadcast list.
        """
        # Mark the current subscribed users as temporarily added for the broadcast
        db.mark_temporary_unsubscriptions()
        
    @staticmethod
    async def add_user_to_temp(user_id):
        """
        add a user from the database to the broadcast list.
        """
        db.add_user_to_temp(user_id)