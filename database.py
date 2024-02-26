import sqlite3
import json

class db:
    db_name = 'user_settings.db'
    
    @staticmethod
    def initialize_database():
        with db.get_connection() as conn:
            c = conn.cursor()
            # Create user_settings table if it doesn't exist
            c.execute('''CREATE TABLE IF NOT EXISTS user_settings
                        (user_id INTEGER PRIMARY KEY, music_quality TEXT, downloading_core TEXT)''')
            # Create subscriptions table if it doesn't exist, including a temporary flag
            c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                        (user_id INTEGER PRIMARY KEY, subscribed BOOLEAN DEFAULT   1, temporary BOOLEAN DEFAULT   0)''')
            conn.commit()
        # Set up the trigger to automatically add new users to the subscriptions table
        db.create_trigger()
        db.set_defualt_values()

    @classmethod
    def set_defualt_values(cls,default_downloading_core:str = "YoutubeDL",default_music_quality:str = "693"):
        cls.default_downloading_core = default_downloading_core
        cls.default_music_quality = default_music_quality
        
    @staticmethod
    def get_connection():
        """
        Returns a database connection. Use as a context manager.
        """
        return sqlite3.connect(db.db_name)

    @staticmethod
    def execute_query(query, params=()):
        """
        Executes a query with optional parameters.
        """
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute(query, params)
            conn.commit()

    @staticmethod
    def fetch_one(query, params=()):
        """
        Executes a query and fetches one result.
        """
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute(query, params)
            return c.fetchone()

    @staticmethod
    def fetch_all(query, params=()):
        """
        Executes a query and fetches all results.
        """
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute(query, params)
            return c.fetchall()

    @staticmethod
    def create_trigger():
        """
        Creates a database trigger to automatically add new users to the subscriptions table with the subscribed flag set to   1.
        """
        # First, check if the trigger exists and drop it if it does
        db.execute_query('DROP TRIGGER IF EXISTS add_user_to_subscriptions')

        # Now, create the trigger
        trigger_sql = '''
        CREATE TRIGGER add_user_to_subscriptions
        AFTER INSERT ON user_settings
        BEGIN
            INSERT INTO subscriptions (user_id, subscribed, temporary)
            VALUES (NEW.user_id, 1, 0);
        END;
        '''
        db.execute_query(trigger_sql)
        
    @staticmethod
    def save_user_settings(user_id, music_quality, downloading_core):
        music_quality_json = json.dumps(music_quality)
        db.execute_query('''INSERT OR REPLACE INTO user_settings
                          (user_id, music_quality, downloading_core) VALUES (?, ?, ?)''',
                         (user_id, music_quality_json, downloading_core))

    @staticmethod
    def get_user_settings(user_id):
        result = db.fetch_one('SELECT music_quality, downloading_core FROM user_settings WHERE user_id = ?', (user_id,))
        if result:
            music_quality = json.loads(result[0])
            downloading_core = result[1]
            return music_quality, downloading_core
        else:
            return None, None

    @staticmethod
    def change_music_quality(user_id, new_music_quality):
        current_music_quality, current_downloading_core = db.get_user_settings(user_id)
        if current_music_quality is not None:
            db.save_user_settings(user_id, new_music_quality, current_downloading_core)
        else:
            db.save_user_settings(user_id, new_music_quality, db.default_downloading_core)

    @staticmethod
    def change_downloading_core(user_id, new_downloading_core):
        current_music_quality, current_downloading_core = db.get_user_settings(user_id)
        if current_downloading_core is not None:
            db.save_user_settings(user_id, current_music_quality, new_downloading_core)
        else:
            db.save_user_settings(user_id, db.default_music_quality, new_downloading_core)

    @staticmethod
    def get_all_user_ids():
        return [row[0] for row in db.fetch_all('SELECT user_id FROM user_settings')]

    @staticmethod
    def count_all_user_ids():
        return db.fetch_one('SELECT COUNT(*) FROM user_settings')[0]

    @staticmethod
    def add_user_to_temp(user_id):
        db.execute_query('''UPDATE subscriptions SET temporary = 1 WHERE user_id = ?''', (user_id,))

    @staticmethod
    def remove_user_from_temp(user_id):
        db.execute_query('''UPDATE subscriptions SET temporary = 0 WHERE user_id = ?''', (user_id,))

    @staticmethod
    def add_subscribed_user(user_id):
        db.execute_query('''UPDATE subscriptions SET subscribed = 1 WHERE user_id = ?''', (user_id,))

    @staticmethod
    def remove_subscribed_user(user_id):
        db.execute_query('''UPDATE subscriptions SET subscribed = 0 WHERE user_id = ?''', (user_id,))

    @staticmethod
    def get_subscribed_user_ids():
        return [row[0] for row in db.fetch_all('SELECT user_id FROM subscriptions WHERE subscribed = 1')]

    @staticmethod
    def clear_subscribed_users():
        db.execute_query('''UPDATE subscriptions SET subscribed = 0''')

    @staticmethod
    def mark_temporary_subscriptions():
        db.execute_query('''UPDATE subscriptions SET temporary = 1''')

    @staticmethod
    def mark_temporary_unsubscriptions():
        db.execute_query('''UPDATE subscriptions SET temporary = 0''')

    @staticmethod
    def get_temporary_subscribed_user_ids():
        return [row[0] for row in db.fetch_all('SELECT user_id FROM subscriptions WHERE temporary = 1')]

    @staticmethod
    def is_user_subscribed(user_id):
        result = db.fetch_one('SELECT subscribed FROM subscriptions WHERE user_id = ?', (user_id,))
        return result is not None and result[0] ==  1