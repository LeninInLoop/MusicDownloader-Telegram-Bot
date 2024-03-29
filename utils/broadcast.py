from utils.database import db


class BroadcastManager:

    @staticmethod
    async def broadcast_message_to_sub_members(client, message, button=None):
        """
        Sends a message to all users in the broadcast list.
        """
        user_ids = await db.get_subscribed_user_ids()
        for user_id in user_ids:
            try:
                await client.send_message(user_id, message, buttons=button)
            except Exception as e:
                print(f"Failed to send message to user {user_id}: {e}")
                # Optionally, retry sending the message or log the failure for later review

    @staticmethod
    async def broadcast_message_to_temp_members(client, message):
        """
        Sends a message to all users in the broadcast list.
        """
        user_ids = await db.get_temporary_subscribed_user_ids()
        for user_id in user_ids:
            try:
                await client.send_message(user_id, message)
            except Exception as e:
                print(f"Failed to send message to user {user_id}: {e}")
                # Optionally, retry sending the message or log the failure for later review

    @staticmethod
    async def add_sub_user(user_id):  # check
        """
        Adds a user to the broadcast list.
        """
        await db.add_subscribed_user(user_id)  # Removed 'await'

    @staticmethod
    async def remove_sub_user(user_id):  # check
        """
        Removes a user from the broadcast list.
        """
        await db.remove_subscribed_user(user_id)  # Removed 'await'

    @staticmethod
    async def get_all_sub_user_ids():
        """
        Returns all user IDs in the broadcast list.
        """
        return await db.get_subscribed_user_ids()

    @staticmethod
    async def clear_user_ids():
        """
        Clears the broadcast list by removing all user IDs.
        """
        await db.clear_subscribed_users()

    @staticmethod
    async def get_temporary_subscribed_user_ids():  # check
        """
        Returns all user IDs in the subscriptions list that are marked as temporarily subscribed.
        """
        return await db.get_temporary_subscribed_user_ids()

    @staticmethod
    async def add_all_users_to_temp():
        """
        Adds all users from the database to the broadcast list.
        """
        # Mark the current subscribed users as temporarily added for the broadcast
        await db.mark_temporary_subscriptions()

    @staticmethod
    async def remove_all_users_from_temp():
        """
        Remove all users from the database to the broadcast list.
        """
        # Mark the current subscribed users as temporarily added for the broadcast
        await db.mark_temporary_unsubscriptions()

    @staticmethod
    async def add_user_to_temp(user_id):
        """
        add a user from the database to the broadcast list.
        """
        await db.add_user_to_temp(user_id)
