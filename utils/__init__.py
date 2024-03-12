from utils.helper import process_flac_music, process_mp3_music, sanitize_query, is_file_voice
from utils.broadcast import BroadcastManager
from utils.database import db
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
from itertools import combinations
from PIL import Image
from io import BytesIO
from yt_dlp import YoutubeDL
from shazamio import Shazam
from tweetcapture import TweetCapture
import requests, asyncio, re, os
import bs4, wget, hashlib, time
import lyricsgenius
import spotipy