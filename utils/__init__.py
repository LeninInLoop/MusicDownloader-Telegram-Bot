from utils.helper import process_flac_music, process_mp3_music, sanitize_query
from utils.broadcast import BroadcastManager
from utils.database import db, os

pycache_dir = os.environ.get('PYTHONPYCACHEPREFIX')
if pycache_dir:
    os.makedirs(pycache_dir, exist_ok=True)