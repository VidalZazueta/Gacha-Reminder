import discord
from discord.ext import commands
from discord import app_commands
import logging
from dotenv import load_dotenv
import os
import time

#Testing changes from on sub branch to a primary branch


# Import from modularized wiki_api file
from wiki_api import get_ongoing_events_async, WikiAPI

# Harcoded URL, will change when scaling the application
API_URL = "https://wutheringwaves.fandom.com/api.php"

# Grab the discord token from the secure file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')

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
# Check if GUILD_ID is set
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
@client.tree.command(name="hello", description="Says hello!", guild=GUILD_OBJECT)
async def sayHello(interaction: discord.Interaction):
    await interaction.response.send_message(f'Hello!')

# Main slash command to get the events for Wuthering Waves (async only)
@client.tree.command(name="events", description="Get the current events for Wuthering Waves", guild=GUILD_OBJECT)
async def list_events(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        
        # Use the async convenience function from wiki_api
        ongoing_events = await get_ongoing_events_async(API_URL, debug=True)
        
        if not ongoing_events:
            await interaction.followup.send("No ongoing events right now.")
            return
        
        # Create a simple embed
        embed = discord.Embed(
            title="Current Wuthering Waves Events",
            color=discord.Color.blue(),
        )
        
        # Format events simply
        event_list = []
        for event in ongoing_events:
            name = event['title']
            time_left = event['time_remaining'] 
            dates = event['date_range_str']
            
            event_list.append(f"**{name}**\nTime left: {time_left} | {dates}")
        
        # Add events to embed
        embed.description = "\n\n".join(event_list)
        embed.set_footer(text=f"Found {len(ongoing_events)} active events • Data from Wuthering Waves Wiki")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Error in events command: {e}")
        error_msg = f"Error fetching events: {str(e)[:100]}..."
        
        if interaction.response.is_done():
            await interaction.followup.send(f"Error: {error_msg}")
        else:
            await interaction.response.send_message(f"Error: {error_msg}")


# Command to test the speed when getting events        
@client.tree.command(name="events_timed", description="Get events with detailed timing", guild=GUILD_OBJECT)
async def list_events_timed(interaction: discord.Interaction):
    overall_start = time.time()
    
    try:
        await interaction.response.defer()
        defer_time = time.time()
        
        print(f"[TIMING] Defer took: {round(defer_time - overall_start, 2)}s")
        
        # Create WikiAPI instance
        wiki_start = time.time()
        wiki_api = WikiAPI(API_URL)
        wiki_created = time.time()
        print(f"[TIMING] WikiAPI creation took: {round(wiki_created - wiki_start, 3)}s")
        
        # Get events with detailed timing
        fetch_start = time.time()
        ongoing_events = await wiki_api.get_ongoing_events_async(debug=True)
        fetch_end = time.time()
        
        fetch_time = round(fetch_end - fetch_start, 2)
        print(f"[TIMING] Event fetching took: {fetch_time}s")
        
        # Process results
        process_start = time.time()
        
        if not ongoing_events:
            await interaction.followup.send("No ongoing events right now.")
            return
        
        # Create embed
        embed = discord.Embed(
            title="Current Wuthering Waves Events (Timed)",
            color=discord.Color.gold(),
        )
        
        event_list = []
        for event in ongoing_events:
            name = event['title']
            time_left = event['time_remaining'] 
            dates = event['date_range_str']
            event_list.append(f"**{name}**\nTime left: {time_left} | {dates}")
        
        embed.description = "\n\n".join(event_list)
        
        process_end = time.time()
        process_time = round(process_end - process_start, 3)
        
        # Send response
        send_start = time.time()
        
        total_time = round(fetch_end - overall_start, 2)
        embed.set_footer(text=f"Found {len(ongoing_events)} events • Fetch: {fetch_time}s • Process: {process_time}s • Total: {total_time}s")
        
        await interaction.followup.send(embed=embed)
        
        send_end = time.time()
        send_time = round(send_end - send_start, 3)
        
        final_time = round(send_end - overall_start, 2)
        print(f"[TIMING] Send response took: {send_time}s")
        print(f"[TIMING] TOTAL command time: {final_time}s")
        
    except Exception as e:
        error_time = time.time()
        total_error_time = round(error_time - overall_start, 2)
        
        print(f"[ERROR] Command failed after {total_error_time}s: {e}")
        error_msg = f"Error fetching events after {total_error_time}s: {str(e)[:100]}..."
        
        if interaction.response.is_done():
            await interaction.followup.send(f"Error: {error_msg}")
        else:
            await interaction.response.send_message(f"Error: {error_msg}")


#! Developer testing commands
# Test the network when connecting to the MediaWiki API          
@client.tree.command(name="test_network", description="Test network connectivity to wiki API", guild=GUILD_OBJECT)
async def test_network(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        import aiohttp
        start_time = time.time()
        
        # Simple test request
        async with aiohttp.ClientSession() as session:
            test_params = {
                "action": "query",
                "format": "json",
                "meta": "siteinfo"
            }
            
            async with session.get(API_URL, params=test_params) as response:
                data = await response.json()
                
        end_time = time.time()
        response_time = round(end_time - start_time, 3)
        
        embed = discord.Embed(
            title="Network Test Results",
            color=discord.Color.green(),
        )
        
        embed.add_field(name="API URL", value=API_URL, inline=False)
        embed.add_field(name="Response Time", value=f"{response_time}s", inline=True)
        embed.add_field(name="Status", value="✅ Connected", inline=True)
        
        if 'query' in data:
            embed.add_field(name="API Response", value="✅ Valid", inline=True)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        embed = discord.Embed(
            title="Network Test Results",
            color=discord.Color.red(),
        )
        embed.add_field(name="Status", value="❌ Failed", inline=False)
        embed.add_field(name="Error", value=str(e)[:500], inline=False)
        
        await interaction.followup.send(embed=embed)
        
# Alternative command using the class directly for more control
@client.tree.command(name="events_debug", description="Get events with debug output", guild=GUILD_OBJECT)
async def list_events_debug(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        
        # Create your own instance for more control
        wiki_api = WikiAPI(API_URL)
        ongoing_events = await wiki_api.get_ongoing_events_async(debug=True)
        
        if not ongoing_events:
            await interaction.followup.send("No ongoing events right now.")
            return
        
        embed = discord.Embed(
            title="Current Wuthering Waves Events (Debug Mode)",
            color=discord.Color.orange(),
        )
        
        event_list = []
        for event in ongoing_events:
            name = event['title']
            time_left = event['time_remaining'] 
            dates = event['date_range_str']
            event_list.append(f"**{name}**\nTime left: {time_left} | {dates}")
        
        embed.description = "\n\n".join(event_list)
        embed.set_footer(text=f"Found {len(ongoing_events)} active events • Debug mode enabled")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Error in debug events command: {e}")
        error_msg = f"Error fetching events: {str(e)[:100]}..."
        
        if interaction.response.is_done():
            await interaction.followup.send(f"Error: {error_msg}")
        else:
            await interaction.response.send_message(f"Error: {error_msg}")

client.run(TOKEN)  # type: ignore - get a warning about str but this works

# TODO: Add a command to have the user specify the gacha game they want to see 
# then run backend code to get the event data for that specific game