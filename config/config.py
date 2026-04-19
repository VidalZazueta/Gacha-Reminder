# config.py - Centralized configuration and constants
"""
Centralized configuration and constants for the Gacha Reminder bot.

Loads Discord credentials from a ``.env`` file via :mod:`dotenv`,
defines wiki API endpoints, and assembles per-game metadata used by
embed builders and command handlers.

Attributes:
    TOKEN (str): Discord bot token read from the ``DISCORD_TOKEN``
        environment variable.
    GUILD_ID (str): Target guild/server ID read from the ``GUILD_ID``
        environment variable.
    GUILD_OBJECT (discord.Object): Pre-built Discord guild object
        constructed from :data:`GUILD_ID`.
    API_URL_WUWA (str): MediaWiki API endpoint for the Wuthering Waves
        Fandom wiki.
    API_URL_ZZZ (str): MediaWiki API endpoint for the Zenless Zone Zero
        Fandom wiki.
    GAME_CONFIG (dict[str, dict]): Mapping of game keys (``"wuwa"``,
        ``"zzz"``) to metadata dicts. Each dict contains:
        ``display_name``, ``api_url``, ``category``, ``color``,
        ``emoji``, ``thumbnail_path``, and ``thumbnail_filename``.

Raises:
    ValueError: If ``DISCORD_TOKEN`` or ``GUILD_ID`` are not set in the
        environment.
"""
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

# --- Full PHP Links --- #
# Wuthering Waves: https://wutheringwaves.fandom.com/api.php?action=query&format=json&list=categorymembers&cmtitle=Category:Events&cmlimit=250
# Zenless Zone Zero: https://zenless-zone-zero.fandom.com/api.php?action=query&format=json&list=categorymembers&cmtitle=Category:In-Game_Events&cmlimit=250

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