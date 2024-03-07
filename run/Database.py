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
    
    @staticmethod
    async def initialize_database():
        conn = await db.get_connection()
        try:
            await conn.execute('''CREATE TABLE IF NOT EXISTS user_settings
                                (user_id INTEGER PRIMARY KEY, music_quality TEXT, downloading_core TEXT,
                                spotify_link_info TEXT, song_dict TEXT,is_file_processing BOOLEAN DEFAULT 0,
                                is_user_updated BOOLEAN DEFAULT 1)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                                (user_id INTEGER PRIMARY KEY, subscribed BOOLEAN DEFAULT   1, temporary BOOLEAN DEFAULT   0)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS musics
                                        (filename TEXT PRIMARY KEY, downloads INTEGER DEFAULT 1)''')
            await conn.commit()
        except:
            raise 
        await db.create_trigger()
        await db.set_defualt_values()

    @classmethod
    async def set_defualt_values(cls, default_downloading_core:str = "YoutubeDL", default_music_quality:dict = {'format': 'flac', 'quality': '693'}):
        cls.default_downloading_core = default_downloading_core
        cls.default_music_quality = default_music_quality
        
    @staticmethod
    async def get_connection():
        return await db.pool.get_connection()

    @staticmethod
    async def release_connection(conn):
        await db.pool.release_connection(conn)

    @staticmethod
    async def execute_query(query, params=()):
        conn = await db.get_connection()
        try:
            async with conn.cursor() as c:
                await c.execute(query, params)
                await conn.commit()
        finally:
            await db.release_connection(conn)

    @staticmethod
    async def fetch_one(query, params=()):
        conn = await db.get_connection()
        try:
            async with conn.cursor() as c:
                await c.execute(query, params)
                return await c.fetchone()
        finally:
            await db.release_connection(conn)

    @staticmethod
    async def fetch_all(query, params=()):
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
    async def save_user_settings(user_id, music_quality, downloading_core):
        music_quality_json = json.dumps(music_quality)
        is_file_processing = await db.get_file_processing_flag(user_id)
        song_dict = await db.get_user_song_dict(user_id) 
        song_dict = json.dumps(song_dict) if song_dict else None
        spotify_link_info = await db.get_user_spotify_link_info(user_id)
        spotify_link_info = json.dumps(spotify_link_info) if spotify_link_info else None
        is_user_updated = await db.get_user_updated_flag(user_id)
        await db.execute_query('''INSERT OR REPLACE INTO user_settings
                          (user_id, music_quality, downloading_core, spotify_link_info, song_dict, is_file_processing, is_user_updated) VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (user_id, music_quality_json, downloading_core, spotify_link_info, song_dict, is_file_processing, is_user_updated))

    @staticmethod
    async def get_user_settings(user_id):
        result = await db.fetch_one('SELECT music_quality, downloading_core FROM user_settings WHERE user_id = ?', (user_id,))
        if result:
            music_quality = json.loads(result[0])
            downloading_core = result[1]
            return music_quality, downloading_core
        else:
            return None, None

    @staticmethod
    async def change_music_quality(user_id, new_music_quality):
        current_music_quality, current_downloading_core = await db.get_user_settings(user_id)
        if current_music_quality is not None:
            await db.save_user_settings(user_id, new_music_quality, current_downloading_core)
        else:
            await db.save_user_settings(user_id, new_music_quality, db.default_downloading_core)

    @staticmethod
    async def change_downloading_core(user_id, new_downloading_core):
        current_music_quality, current_downloading_core = await db.get_user_settings(user_id)
        if current_downloading_core is not None:
            await db.save_user_settings(user_id, current_music_quality, new_downloading_core)
        else:
            await db.save_user_settings(user_id, db.default_music_quality, new_downloading_core)

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
        return result is not None and result[0] ==  1

    @staticmethod
    async def update_user_spotify_link_info(user_id, spotify_link_info):
        serialized_info = json.dumps(spotify_link_info)
        await db.execute_query('UPDATE user_settings SET spotify_link_info = ? WHERE user_id = ?', (serialized_info, user_id))

    @staticmethod
    async def set_user_song_dict(user_id, song_dict):
        serialized_dict = json.dumps(song_dict)
        await db.execute_query('UPDATE user_settings SET song_dict = ? WHERE user_id = ?', (serialized_dict, user_id))

    @staticmethod
    async def update_user_is_admin(user_id, is_admin):
        await db.execute_query('UPDATE user_settings SET is_admin = ? WHERE user_id = ?', (is_admin, user_id))

    @staticmethod
    async def get_user_song_dict(user_id):
        result = await db.fetch_one('SELECT song_dict FROM user_settings WHERE user_id = ?', (user_id,))
        if result:
            return json.loads(result[0]) if result[0] else {}
        return {}
    
    @staticmethod
    async def is_user_admin(user_id):
        result = await db.fetch_one('SELECT is_admin FROM user_settings WHERE user_id = ?', (user_id,))
        return result is not None and result[0] ==  1

    @staticmethod
    async def set_admin_broadcast(user_id, admin_broadcast):
        await db.execute_query('UPDATE user_settings SET admin_broadcast = ? WHERE user_id = ?', (admin_broadcast, user_id))

    @staticmethod
    async def get_admin_broadcast(user_id):
        result = await db.fetch_one('SELECT admin_broadcast FROM user_settings WHERE user_id = ?', (user_id,))
        if result:
            return result[0]
        return False # Default to False if the user is not found or the flag is not set

    @staticmethod
    async def count_subscribed_users():
        result = await db.fetch_one('SELECT COUNT(*) FROM subscriptions WHERE subscribed = 1')
        return result[0] if result else 0

    @staticmethod
    async def set_user_updated_flag(user_id, is_user_updated):
        is_user_updated_value = 1 if is_user_updated else 0
        await db.execute_query('UPDATE user_settings SET is_user_updated = ? WHERE user_id = ?', (is_user_updated_value, user_id))

    @staticmethod
    async def get_user_updated_flag(user_id):
        result = await db.fetch_one('SELECT is_user_updated FROM user_settings WHERE user_id = ?', (user_id,))
        if result:
            return bool(result[0])
        return False
        
    @staticmethod
    async def set_user_spotify_link_info(user_id, spotify_link_info):
        serialized_info = json.dumps(spotify_link_info)
        await db.execute_query('UPDATE user_settings SET spotify_link_info = ? WHERE user_id = ?', (serialized_info, user_id))
        
    @staticmethod
    async def get_user_spotify_link_info(user_id):
        result = await db.fetch_one('SELECT spotify_link_info FROM user_settings WHERE user_id = ?', (user_id,))
        if result != None:
            return json.loads(result[0]) if result[0] else {}
        return {} # Return an empty dictionary if the user is not found or the Spotify link info is not set

    @staticmethod
    async def set_file_processing_flag(user_id, is_processing):
        is_processing_value = 1 if is_processing else 0
        await db.execute_query('UPDATE user_settings SET is_file_processing = ? WHERE user_id = ?', (is_processing_value, user_id))
        
    @staticmethod
    async def get_file_processing_flag(user_id):
        result = await db.fetch_one('SELECT is_file_processing FROM user_settings WHERE user_id = ?', (user_id,))
        if result:
            return bool(result[0]) if result[0] else False
        return False # Return False if the file is not found or the flag is not set

    @staticmethod
    async def reset_all_file_processing_flags():
        await db.execute_query('UPDATE user_settings SET is_file_processing = 0')

    @staticmethod
    async def increment_download_counter(filename):
        await db.execute_query('UPDATE musics SET downloads = downloads + 1 WHERE filename = ?', (filename,))

    @staticmethod
    async def add_or_increment_song(filename):
        conn = await db.get_connection()
        try:
            async with conn.cursor() as c:
                try:
                    # Attempt to insert the new song
                    await c.execute('INSERT INTO musics (filename) VALUES (?)', (filename,))
                except aiosqlite.IntegrityError:
                    # If the song already exists, increment the download counter
                    await c.execute('UPDATE musics SET downloads = downloads + 1 WHERE filename = ?', (filename,))
                # Commit the transaction
                await conn.commit()
        except Exception as e:
            # Rollback the transaction in case of any error
            await conn.rollback()
            raise e
        finally:
            # Release the connection back to the pool
            await db.release_connection(conn)
            
    @staticmethod
    async def get_total_downloads():
        result = await db.fetch_one('SELECT SUM(downloads) FROM musics')
        return result[0] if result else 0

    @staticmethod
    async def get_song_downloads(filename):
        result = await db.fetch_one('SELECT downloads FROM musics WHERE filename = ?', (filename,))
        return result[0] if result else 0