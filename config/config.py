# config.py - Centralized configuration and constants
"""
Centralized configuration and constants for the Gacha Reminder bot.

Loads Discord credentials from a ``.env`` file via :mod:`dotenv`.
Game-specific metadata (API URLs, categories, colors) lives in each
game's own module under ``games/``.

Attributes:
    TOKEN (str): Discord bot token read from the ``DISCORD_TOKEN``
        environment variable.
    GUILD_ID (str): Target guild/server ID read from the ``GUILD_ID``
        environment variable.
    GUILD_OBJECT (discord.Object): Pre-built Discord guild object
        constructed from :data:`GUILD_ID`.

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