import aiosqlite
import json
import asyncio


class ConnectionPool:
    def __init__(self, db_name, max_connections=100):
        self.db_name = db_name
        self.max_connections = max_connections
        self.pool = asyncio.Queue()

    async def get_connection(self):
        if self.pool.empty():
            conn = await aiosqlite.connect(self.db_name)
        else:
            conn = await self.pool.get()
        return conn

    async def release_connection(self, conn):
        if self.pool.qsize() < self.max_connections:
            await self.pool.put(conn)
        else:
            await conn.close()


class db:
    db_name = 'user_settings.db'
    pool = ConnectionPool(db_name)
    lock = asyncio.Lock()

    @staticmethod
    async def initialize_database():
        conn = await db.get_connection()
        try:
            await conn.execute('''CREATE TABLE IF NOT EXISTS user_settings
                                (user_id INTEGER PRIMARY KEY, music_quality TEXT, downloading_core TEXT,
                                tweet_capture_settings TEXT,
                                is_file_processing BOOLEAN DEFAULT 0,is_user_updated BOOLEAN DEFAULT 1)'''
                               )
            await conn.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                                (user_id INTEGER PRIMARY KEY, subscribed BOOLEAN DEFAULT   1, temporary BOOLEAN DEFAULT   0)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS musics
                                        (filename TEXT PRIMARY KEY, downloads INTEGER DEFAULT 1)''')
            await conn.commit()
        except:
            raise
        await db.create_trigger()
        await db.set_default_values()

    @classmethod
    async def set_default_values(cls):
        cls.default_downloading_core: str = "Auto"
        cls.default_music_quality: dict = {'format': 'flac', 'quality': '693'}
        cls.default_tweet_capture_setting: dict = {'night_mode': '0'}

    @staticmethod
    async def get_connection():
        return await db.pool.get_connection()

    @staticmethod
    async def release_connection(conn):
        await db.pool.release_connection(conn)

    @staticmethod
    async def execute_query(query, params=()):
        async with db.lock:
            conn = await db.get_connection()
            try:
                async with conn.cursor() as c:
                    await c.execute(query, params)
                    await conn.commit()
            except aiosqlite.OperationalError as e:
                if 'database is locked' in str(e):
                    await db.execute_query(query, params)
                else:
                    raise e
            finally:
                await db.release_connection(conn)

    @staticmethod
    async def fetch_one(query, params=()):
        async with db.lock:
            conn = await db.get_connection()
            try:
                async with conn.cursor() as c:
                    try:
                        await c.execute(query, params)
                        return await c.fetchone()
                    except Exception as e:
                        print(f"Error executing query: {query}")
                        print(f"Parameters: {params}")
                        print(f"Error details: {e}")
                        raise e
            finally:
                await db.release_connection(conn)

    @staticmethod
    async def fetch_all(query, params=()):
        async with db.lock:
            conn = await db.get_connection()
            try:
                async with conn.cursor() as c:
                    await c.execute(query, params)
                    return await c.fetchall()
            finally:
                await db.release_connection(conn)

    @staticmethod
    async def create_trigger():
        await db.execute_query('DROP TRIGGER IF EXISTS add_user_to_subscriptions')
        trigger_sql = '''
        CREATE TRIGGER add_user_to_subscriptions
        AFTER INSERT ON user_settings
        BEGIN
            INSERT INTO subscriptions (user_id, subscribed, temporary)
            VALUES (NEW.user_id, 1, 0);
        END;
        '''
        await db.execute_query(trigger_sql)

    @staticmethod
    async def create_user_settings(user_id):
        music_quality = await db.get_user_music_quality(user_id)
        music_quality = json.dumps(music_quality) if music_quality != {} else json.dumps(db.default_music_quality)

        downloading_core = await db.get_user_downloading_core(user_id)
        downloading_core = downloading_core if downloading_core else db.default_downloading_core

        tweet_capture_setting = await db.get_user_tweet_capture_settings(user_id)
        tweet_capture_setting = json.dumps(tweet_capture_setting) if tweet_capture_setting != {} else json.dumps(
            db.default_tweet_capture_setting)

        await db.execute_query('''INSERT OR REPLACE INTO user_settings
                          (user_id, music_quality, downloading_core, tweet_capture_settings) VALUES (?, ?, ?, ?)''',
                               (user_id, music_quality, downloading_core, tweet_capture_setting))

    @staticmethod
    async def check_username_in_database(user_id):
        query = "SELECT COUNT(*) FROM user_settings WHERE user_id = ?"
        result = await db.fetch_one(query, (user_id,))
        if result:
            count = result[0]
            if count > 0 and await db.get_user_downloading_core(user_id) is not None:
                if await db.get_user_music_quality(user_id) != {} and await db.get_user_tweet_capture_settings(
                        user_id) != {}:
                    return True
        else:
            return False

    @staticmethod
    async def get_user_music_quality(user_id):
        result = await db.fetch_one('SELECT music_quality FROM user_settings WHERE user_id = ?', (user_id,))
        if result:
            music_quality = json.loads(result[0])
            return music_quality
        else:
            return {}

    @staticmethod
    async def get_user_downloading_core(user_id):
        result = await db.fetch_one('SELECT downloading_core FROM user_settings WHERE user_id = ?', (user_id,))
        if result:
            return result[0]
        else:
            return None

    @staticmethod
    async def set_user_music_quality(user_id, music_quality):
        serialized_dict = json.dumps(music_quality)
        await db.execute_query('UPDATE user_settings SET music_quality = ? WHERE user_id = ?',
                               (serialized_dict, user_id))

    @staticmethod
    async def set_user_downloading_core(user_id, downloading_core):
        await db.execute_query('UPDATE user_settings SET downloading_core = ? WHERE user_id = ?',
                               (downloading_core, user_id))

    @staticmethod
    async def get_all_user_ids():
        return [row[0] for row in await db.fetch_all('SELECT user_id FROM user_settings')]

    @staticmethod
    async def count_all_user_ids():
        return (await db.fetch_one('SELECT COUNT(*) FROM user_settings'))[0]

    @staticmethod
    async def add_user_to_temp(user_id):
        await db.execute_query('''UPDATE subscriptions SET temporary = 1 WHERE user_id = ?''', (user_id,))

    @staticmethod
    async def remove_user_from_temp(user_id):
        await db.execute_query('''UPDATE subscriptions SET temporary = 0 WHERE user_id = ?''', (user_id,))

    @staticmethod
    async def add_subscribed_user(user_id):
        await db.execute_query('''UPDATE subscriptions SET subscribed = 1 WHERE user_id = ?''', (user_id,))

    @staticmethod
    async def remove_subscribed_user(user_id):
        await db.execute_query('''UPDATE subscriptions SET subscribed = 0 WHERE user_id = ?''', (user_id,))

    @staticmethod
    async def get_subscribed_user_ids():
        return [row[0] for row in await db.fetch_all('SELECT user_id FROM subscriptions WHERE subscribed = 1')]

    @staticmethod
    async def clear_subscribed_users():
        await db.execute_query('''UPDATE subscriptions SET subscribed = 0''')

    @staticmethod
    async def mark_temporary_subscriptions():
        await db.execute_query('''UPDATE subscriptions SET temporary = 1''')

    @staticmethod
    async def mark_temporary_unsubscriptions():
        await db.execute_query('''UPDATE subscriptions SET temporary = 0''')

    @staticmethod
    async def get_temporary_subscribed_user_ids():
        return [row[0] for row in await db.fetch_all('SELECT user_id FROM subscriptions WHERE temporary = 1')]

    @staticmethod
    async def is_user_subscribed(user_id):
        result = await db.fetch_one('SELECT subscribed FROM subscriptions WHERE user_id = ?', (user_id,))
        return result is not None and result[0] == 1

    @staticmethod
    async def update_user_is_admin(user_id, is_admin):
        await db.execute_query('UPDATE user_settings SET is_admin = ? WHERE user_id = ?', (is_admin, user_id))

    @staticmethod
    async def is_user_admin(user_id):
        result = await db.fetch_one('SELECT is_admin FROM user_settings WHERE user_id = ?', (user_id,))
        return result is not None and result[0] == 1

    @staticmethod
    async def set_admin_broadcast(user_id, admin_broadcast):
        await db.execute_query('UPDATE user_settings SET admin_broadcast = ? WHERE user_id = ?',
                               (admin_broadcast, user_id))

    @staticmethod
    async def get_admin_broadcast(user_id):
        result = await db.fetch_one('SELECT admin_broadcast FROM user_settings WHERE user_id = ?', (user_id,))
        if result:
            return result[0]
        return False  # Default to False if the user is not found or the flag is not set

    @staticmethod
    async def count_subscribed_users():
        result = await db.fetch_one('SELECT COUNT(*) FROM subscriptions WHERE subscribed = 1')
        return result[0] if result else 0

    @staticmethod
    async def set_user_updated_flag(user_id, is_user_updated):
        is_user_updated_value = 1 if is_user_updated else 0
        await db.execute_query('UPDATE user_settings SET is_user_updated = ? WHERE user_id = ?',
                               (is_user_updated_value, user_id))

    @staticmethod
    async def get_user_updated_flag(user_id):
        result = await db.fetch_one('SELECT is_user_updated FROM user_settings WHERE user_id = ?', (user_id,))
        if result:
            return bool(result[0])
        return False

    @staticmethod
    async def set_file_processing_flag(user_id, is_processing):
        is_processing_value = 1 if is_processing else 0
        await db.execute_query('UPDATE user_settings SET is_file_processing = ? WHERE user_id = ?',
                               (is_processing_value, user_id))

    @staticmethod
    async def get_file_processing_flag(user_id):
        result = await db.fetch_one('SELECT is_file_processing FROM user_settings WHERE user_id = ?', (user_id,))
        if result:
            return bool(result[0]) if result[0] else False
        return False  # Return False if the file is not found or the flag is not set

    @staticmethod
    async def reset_all_file_processing_flags():
        await db.execute_query('UPDATE user_settings SET is_file_processing = 0')

    @staticmethod
    async def increment_download_counter(filename):
        await db.execute_query('UPDATE musics SET downloads = downloads + 1 WHERE filename = ?', (filename,))

    @staticmethod
    async def add_or_increment_song(filename):
        try:
            query = 'INSERT INTO musics (filename) VALUES (?)'
            await db.execute_query(query, (filename,))
        except aiosqlite.IntegrityError:
            query = 'UPDATE musics SET downloads = downloads + 1 WHERE filename = ?'
            await db.execute_query(query, (filename,))

    @staticmethod
    async def get_total_downloads():
        result = await db.fetch_one('SELECT SUM(downloads) FROM musics')
        return result[0] if result else 0

    @staticmethod
    async def get_song_downloads(filename):
        result = await db.fetch_one('SELECT downloads FROM musics WHERE filename = ?', (filename,))
        return result[0] if result else 0

    @staticmethod
    async def set_user_tweet_capture_settings(user_id, tweet_capture_settings):
        serialized_info = json.dumps(tweet_capture_settings)
        await db.execute_query('UPDATE user_settings SET tweet_capture_settings = ? WHERE user_id = ?',
                               (serialized_info, user_id))

    @staticmethod
    async def get_user_tweet_capture_settings(user_id):
        result = await db.fetch_one('SELECT tweet_capture_settings FROM user_settings WHERE user_id = ?', (user_id,))
        if result is not None:
            return json.loads(result[0]) if result[0] else {}
        return {}  # Return an empty dictionary if the user is not found or the Spotify link info is not set
