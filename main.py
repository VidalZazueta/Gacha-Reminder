# main.py
"""
Entry point for the Gacha Reminder Discord bot.

Initializes the bot client, configures logging, registers all slash
commands (game-facing and developer), and connects to Discord.
"""

import logging
import discord
from discord.ext import commands

from config import TOKEN, GUILD_ID, GUILD_OBJECT
from commands import register_game_commands, register_dev_commands


# ------------------------------------------------------------------ #
#  Bot client                                                        #
# ------------------------------------------------------------------ #

class Client(commands.Bot):
    """Custom Discord bot client for the Gacha Reminder bot.

    Inherits from :class:`discord.ext.commands.Bot` and overrides the
    ``on_ready`` event to sync the application command tree to the
    configured guild on startup.
    """

    async def on_ready(self) -> None:
        """Handle the ``on_ready`` event fired after a successful login.

        Prints the logged-in user to stdout and syncs all registered
        slash commands to the guild defined in :data:`config.GUILD_OBJECT`.

        Raises:
            Exception: Any error raised by ``tree.sync()`` is caught,
                logged to stdout, and swallowed so the bot stays online.
        """
        print(f"Logged in as {self.user}")
        try:
            synced = await self.tree.sync(guild=GUILD_OBJECT)
            print(f"Synced {len(synced)} commands to guild {GUILD_OBJECT.id}")
        except Exception as exc:
            print(f"Error syncing commands: {exc}")


# ------------------------------------------------------------------ #
#  Setup                                                             #
# ------------------------------------------------------------------ #

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True

client = Client(command_prefix="!", intents=intents)

# Register slash commands
register_game_commands(client)
register_dev_commands(client)

# ------------------------------------------------------------------ #
#  Entry point                                                       #
# ------------------------------------------------------------------ #

client.run(TOKEN)  # type: ignore[arg-type]
