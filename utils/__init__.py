from utils.broadcast import BroadcastManager
from utils.database import db
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
from itertools import combinations
from PIL import Image
from io import BytesIO
from yt_dlp import YoutubeDL
from shazamio import Shazam
import requests, asyncio, re, os
import bs4, wget, hashlib, time
import lyricsgenius
import spotipy
from concurrent.futures import ThreadPoolExecutor
import aiohttp
from telethon import sync
from telethon.tl.functions.messages import SendMediaRequest
from telethon.tl.types import InputMediaUploadedDocument, DocumentAttributeAudio, InputMediaPhotoExternal, DocumentAttributeVideo
from FastTelethonhelper import fast_upload
from threading import Thread
import concurrent 
from functools import lru_cache, partial
from .tweet_capture import TweetCapture
from .helper import sanitize_query
import io
import sys
from dataclasses import dataclass, field
from spotipy.exceptions import SpotifyException
from typing import Tuple, Any