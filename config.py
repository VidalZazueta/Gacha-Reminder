# config.py - Centralized configuration and constants
import os
from dotenv import load_dotenv
import discord

load_dotenv()

# --- Discord credentials ---
TOKEN: str = os.getenv("DISCORD_TOKEN") or ""
GUILD_ID: str = os.getenv("GUILD_ID") or ""

if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is not set.")
if not GUILD_ID:
    raise ValueError("GUILD_ID environment variable is not set.")

GUILD_OBJECT = discord.Object(id=int(GUILD_ID))

# --- Wiki API URLs ---
API_URL_WUWA = "https://wutheringwaves.fandom.com/api.php"
API_URL_ZZZ  = "https://zenless-zone-zero.fandom.com/api.php"

# --- Game metadata (used to build embeds generically) ---
GAME_CONFIG = {
    "wuwa": {
        "display_name": "Wuthering Waves",
        "api_url": API_URL_WUWA,
        "category": "Events",
        "color": discord.Color.blue(),
        "emoji": "🌊",
        "thumbnail_path": "images/WutheringWavesThumbnail.jpeg",
        "thumbnail_filename": "WuWaThumbnail.png",
    },
    "zzz": {
        "display_name": "Zenless Zone Zero",
        "api_url": API_URL_ZZZ,
        "category": "In-Game_Events",
        "color": discord.Color.orange(),
        "emoji": "⚡",
        "thumbnail_path": "images/ZenlessZoneZeroThumbnail.png",
        "thumbnail_filename": "ZZZThumbnail.png",
    },
}