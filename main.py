# main.py
import sys
print(sys.executable)
import logging
import discord
from discord.ext import commands

from config import TOKEN, GUILD_ID, GUILD_OBJECT
from commands import register_game_commands, register_dev_commands


# ------------------------------------------------------------------ #
#  Bot client                                                          #
# ------------------------------------------------------------------ #

class Client(commands.Bot):
    async def on_ready(self) -> None:
        print(f"Logged in as {self.user}")
        try:
            synced = await self.tree.sync(guild=GUILD_OBJECT)
            print(f"Synced {len(synced)} commands to guild {GUILD_OBJECT.id}")
        except Exception as exc:
            print(f"Error syncing commands: {exc}")


# ------------------------------------------------------------------ #
#  Setup                                                               #
# ------------------------------------------------------------------ #

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True

client = Client(command_prefix="!", intents=intents)

# Register all slash commands
register_game_commands(client)
register_dev_commands(client)

# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

client.run(TOKEN)  # type: ignore[arg-type]

# TODO: Add a command to let users pick which game they want to see events for,
#       then route to the appropriate backend function.