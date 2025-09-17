import discord
from discord.ext import commands
from discord import app_commands
import logging
from dotenv import load_dotenv
import os

# Grab the discord token from the secure file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')

# Placeholder for the API URL to get event data
#TODO
API_URL = ""


# Check if TOKEN is set
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable is not set.")
# Check if GUILD_ID is set
if GUILD_ID is None:
    raise ValueError("GUILD_ID environment variable is not set.")

# Define client function so that the bot can go online
class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        
        # Try catch block to handle any errors during command sync
        # This should sync the commands to the specified guild immediately
        try:
            # Check if GUILD_ID is set
            if GUILD_ID is None:
                raise ValueError("GUILD_ID environment variable is not set.")
            guild = discord.Object(id=int(GUILD_ID))
            sync = await self.tree.sync(guild=guild)
            print(f'Synced {len(sync)} commands to guild {guild.id}')
        except Exception as e:
            print(f"Error syncing commands: {e}")
            
# Unique server ID to test my bot commands
#Check if GUILD_ID is set
if GUILD_ID is None:
    raise ValueError("GUILD_ID environment variable is not set.")
GUILD_OBJECT = discord.Object(id=int(GUILD_ID))

# Set up logging for debugging purposes
logging.basicConfig(level=logging.INFO)

# Set up the bot client with command prefix and intents
intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix='!', intents=intents)

# Sample code to test the bot with commands
# Important to specify the guild for faster testing, as testing it globably can take up to an hour to update
# If you want to make the command global, just remove the guild=GUILD_ID part
@client.tree.command(name="hello", description="Says hello!", guild=GUILD_OBJECT)
async def sayHello(interaction: discord.Interaction):
    await interaction.response.send_message(f'Hello!')

client.run(TOKEN) # type: ignore - get a warning about str but this works

#TODO add a command to have the user specify the gacha game they want to see then run backend code to get the event data


# Found a website that has the event data for wuthering waves.
# It seems the user manually updates the event data.
# I can potentially scrape the data from the website and send it to a discord channel.
# Website: https://wutheringwaves.fandom.com/wiki/Events

# I can possibly use the Fandom Wiki API to get the data for the events
# Then what I can do is create a discord bot that will send a message to a channel when a new event is added
# Or when an event is about to start or end
#Also I can make it where it has a persistent countdown with the possibility of daily reminders
# Fandom Wiki API: https://www.mediawiki.org/wiki/API:Main_page