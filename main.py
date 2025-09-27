import discord
from discord.ext import commands
from discord import app_commands
import logging
from dotenv import load_dotenv
import os
import time

#Testing changes from on sub branch to a primary branch


# Import from modularized wiki_api file
from wiki_api import get_ongoing_events_async, WikiAPI, get_wuwa_events_async, get_zzz_events_async

# Harcoded URL, will change when scaling the application
API_URL_WUWA = "https://wutheringwaves.fandom.com/api.php"
API_URL_ZZZ = "https://zenless-zone-zero.fandom.com/api.php"

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

# Main slash command to get the events for Wuthering Waves using the async function
@client.tree.command(name="events_wuwa", description="Get the current events for Wuthering Waves", guild=GUILD_OBJECT)
async def list_events_WUWA(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        
        # Use the new convenience function for WUWA
        ongoing_events = await get_wuwa_events_async(debug=True)
        
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
 
# Fixed ZZZ command using the correct category
@client.tree.command(name="events_zzz", description="Get the current events for Zenless Zone Zero", guild=GUILD_OBJECT)
async def list_events_ZZZ(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        
        # Use the new convenience function for ZZZ
        ongoing_events = await get_zzz_events_async(debug=True)
        
        if not ongoing_events:
            await interaction.followup.send("No ongoing events right now.")
            return
        
        # Create a simple embed
        embed = discord.Embed(
            title="Current Zenless Zone Zero Events",
            color=discord.Color.orange(),  # Changed color to differentiate from WUWA
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
        embed.set_footer(text=f"Found {len(ongoing_events)} active events • Data from Zenless Zone Zero Wiki")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Error in ZZZ events command: {e}")
        error_msg = f"Error fetching events: {str(e)[:100]}..."
        
        if interaction.response.is_done():
            await interaction.followup.send(f"Error: {error_msg}")
        else:
            await interaction.response.send_message(f"Error: {error_msg}")

# New combined command to get events from both games
@client.tree.command(name="events_all", description="Get current events from all supported games", guild=GUILD_OBJECT)
async def list_events_all(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        
        # Fetch events from both games concurrently
        import asyncio
        wuwa_task = get_wuwa_events_async(debug=False)
        zzz_task = get_zzz_events_async(debug=False)
        
        wuwa_events, zzz_events = await asyncio.gather(wuwa_task, zzz_task)
        
        # Create embed
        embed = discord.Embed(
            title="Current Events - All Games",
            color=discord.Color.purple(),
        )
        
        sections = []
        
        # Add WUWA section
        if wuwa_events:
            wuwa_list = []
            for event in wuwa_events:
                name = event['title']
                time_left = event['time_remaining']
                wuwa_list.append(f"**{name}** - {time_left}")
            sections.append(f"**🌊 Wuthering Waves ({len(wuwa_events)} events)**\n" + "\n".join(wuwa_list))
        else:
            sections.append("**🌊 Wuthering Waves**\nNo ongoing events")
        
        # Add ZZZ section
        if zzz_events:
            zzz_list = []
            for event in zzz_events:
                name = event['title']
                time_left = event['time_remaining']
                zzz_list.append(f"**{name}** - {time_left}")
            sections.append(f"**⚡ Zenless Zone Zero ({len(zzz_events)} events)**\n" + "\n".join(zzz_list))
        else:
            sections.append("**⚡ Zenless Zone Zero**\nNo ongoing events")
        
        embed.description = "\n\n".join(sections)
        total_events = len(wuwa_events) + len(zzz_events)
        embed.set_footer(text=f"Total: {total_events} active events across all games")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Error in events_all command: {e}")
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
        
        # Create WikiAPI instance for WUWA
        wiki_start = time.time()
        wiki_api = WikiAPI(API_URL_WUWA, "Events")
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
@client.tree.command(name="test_network", description="Test network connectivity to wiki APIs", guild=GUILD_OBJECT)
async def test_network(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        import aiohttp
        
        embed = discord.Embed(
            title="Network Test Results",
            color=discord.Color.blue(),
        )
        
        # Test both APIs
        apis_to_test = [
            ("WUWA", API_URL_WUWA),
            ("ZZZ", API_URL_ZZZ)
        ]
        
        async with aiohttp.ClientSession() as session:
            for game, api_url in apis_to_test:
                start_time = time.time()
                
                # Simple test request
                test_params = {
                    "action": "query",
                    "format": "json",
                    "meta": "siteinfo"
                }
                
                try:
                    async with session.get(api_url, params=test_params) as response:
                        data = await response.json()
                        
                    end_time = time.time()
                    response_time = round(end_time - start_time, 3)
                    
                    status = "✅ Connected" if 'query' in data else "⚠️ Partial"
                    embed.add_field(
                        name=f"{game} API", 
                        value=f"Status: {status}\nResponse: {response_time}s", 
                        inline=True
                    )
                    
                except Exception as e:
                    embed.add_field(
                        name=f"{game} API", 
                        value=f"Status: ❌ Failed\nError: {str(e)[:50]}...", 
                        inline=True
                    )
        
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
@client.tree.command(name="events_debug", description="Get events with debug output for the game wuthering waves", guild=GUILD_OBJECT)
async def list_events_debug(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        
        # Create your own instance for more control
        wiki_api = WikiAPI(API_URL_WUWA, "Events")
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

# New debug command for ZZZ
@client.tree.command(name="events_debug_zzz", description="Get ZZZ events with debug output", guild=GUILD_OBJECT)
async def list_events_debug_zzz(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        
        # Create your own instance for more control
        wiki_api = WikiAPI(API_URL_ZZZ, "In-Game_Events")
        ongoing_events = await wiki_api.get_ongoing_events_async(debug=True)
        
        if not ongoing_events:
            await interaction.followup.send("No ongoing ZZZ events right now.")
            return
        
        embed = discord.Embed(
            title="Current Zenless Zone Zero Events (Debug Mode)",
            color=discord.Color.red(),
        )
        
        event_list = []
        for event in ongoing_events:
            name = event['title']
            time_left = event['time_remaining'] 
            dates = event['date_range_str']
            event_list.append(f"**{name}**\nTime left: {time_left} | {dates}")
        
        embed.description = "\n\n".join(event_list)
        embed.set_footer(text=f"Found {len(ongoing_events)} active ZZZ events • Debug mode enabled")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Error in ZZZ debug events command: {e}")
        error_msg = f"Error fetching ZZZ events: {str(e)[:100]}..."
        
        if interaction.response.is_done():
            await interaction.followup.send(f"Error: {error_msg}")
        else:
            await interaction.response.send_message(f"Error: {error_msg}")

# Diagnostic command to inspect ZZZ wiki structure
@client.tree.command(name="diagnose_zzz", description="Diagnose ZZZ wiki structure and content", guild=GUILD_OBJECT)
async def diagnose_zzz(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            # Test different category names
            categories_to_test = [
                "In-Game_Events",
                "Events", 
                "Event",
                "Activities",
                "Limited_Events"
            ]
            
            embed = discord.Embed(
                title="ZZZ Wiki Diagnosis",
                color=discord.Color.gold(),
            )
            
            found_categories = []
            
            for category in categories_to_test:
                params = {
                    "action": "query",
                    "format": "json",
                    "list": "categorymembers", 
                    "cmtitle": f"Category:{category}",
                    "cmlimit": "10"
                }
                
                try:
                    async with session.get(API_URL_ZZZ, params=params) as response:
                        data = await response.json()
                        members = data.get("query", {}).get("categorymembers", [])
                        
                        if members:
                            found_categories.append(f"**{category}**: {len(members)} pages")
                            
                            # Show first few page titles
                            sample_titles = [m['title'] for m in members[:3]]
                            found_categories.append(f"  Sample: {', '.join(sample_titles)}")
                        else:
                            found_categories.append(f"**{category}**: No pages found")
                            
                except Exception as e:
                    found_categories.append(f"**{category}**: Error - {str(e)[:50]}")
            
            embed.add_field(
                name="Category Analysis", 
                value="\n".join(found_categories), 
                inline=False
            )
            
            # Now examine content of one event if we found any
            if "In-Game_Events" in str(found_categories[0]) and "No pages" not in str(found_categories[0]):
                # Get first event from In-Game_Events
                params = {
                    "action": "query",
                    "format": "json",
                    "list": "categorymembers",
                    "cmtitle": "Category:In-Game_Events", 
                    "cmlimit": "1"
                }
                
                async with session.get(API_URL_ZZZ, params=params) as response:
                    data = await response.json()
                    members = data.get("query", {}).get("categorymembers", [])
                    
                    if members:
                        test_page = members[0]['title']
                        
                        # Get content
                        content_params = {
                            "action": "query",
                            "format": "json",
                            "prop": "revisions",
                            "titles": test_page,
                            "rvprop": "content",
                            "rvslots": "main"
                        }
                        
                        async with session.get(API_URL_ZZZ, params=content_params) as content_response:
                            content_data = await content_response.json()
                            pages = content_data.get("query", {}).get("pages", {})
                            
                            if pages:
                                page_data = list(pages.values())[0]
                                revisions = page_data.get("revisions", [])
                                
                                if revisions:
                                    slots = revisions[0].get("slots", {})
                                    main_slot = slots.get("main", {})
                                    content = main_slot.get("*", "")
                                    
                                    # Extract first 500 chars for analysis
                                    preview = content[:500] if content else "No content"
                                    
                                    embed.add_field(
                                        name=f"Sample Content: {test_page}",
                                        value=f"```{preview}```",
                                        inline=False
                                    )
                                    
                                    # Look for date patterns
                                    import re
                                    date_patterns = re.findall(r'\|\s*\w*(?:time|date|start|end)\w*\s*=\s*([^\n|]+)', content, re.IGNORECASE)
                                    
                                    if date_patterns:
                                        embed.add_field(
                                            name="Found Date Fields",
                                            value=f"```{', '.join(date_patterns[:5])}```",
                                            inline=False
                                        )
                                    else:
                                        embed.add_field(
                                            name="Date Fields",
                                            value="❌ No date fields found with standard patterns",
                                            inline=False
                                        )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="Diagnosis Failed",
            description=f"Error: {str(e)[:500]}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed)

# Test specific event parsing for ZZZ
@client.tree.command(name="test_zzz_parsing", description="Test parsing of a specific ZZZ event", guild=GUILD_OBJECT)
async def test_zzz_parsing(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        
        import aiohttp
        from datetime import datetime, timezone
        
        # Test with a specific event we know exists
        test_event = '"En-Nah" Assistant Program'
        
        async with aiohttp.ClientSession() as session:
            # Get content of specific event
            content_params = {
                "action": "query",
                "format": "json",
                "prop": "revisions",
                "titles": test_event,
                "rvprop": "content",
                "rvslots": "main"
            }
            
            async with session.get(API_URL_ZZZ, params=content_params) as response:
                data = await response.json()
                pages = data.get("query", {}).get("pages", {})
                
                if pages:
                    page_data = list(pages.values())[0]
                    revisions = page_data.get("revisions", [])
                    
                    if revisions:
                        slots = revisions[0].get("slots", {})
                        main_slot = slots.get("main", {})
                        content = main_slot.get("*", "")
                        
                        # Extract raw date fields first
                        import re
                        start_match = re.search(r'\|\s*time_start\s*=\s*([^\n|]+)', content)
                        end_match = re.search(r'\|\s*time_end\s*=\s*([^\n|]+)', content)
                        offset_match = re.search(r'\|\s*time_start_offset\s*=\s*([^\n|]+)', content)
                        
                        embed = discord.Embed(
                            title=f"Detailed Parsing Test: {test_event}",
                            color=discord.Color.blue(),
                        )
                        
                        # Show raw extraction
                        raw_fields = []
                        start_str = start_match.group(1).strip() if start_match else "Not found"
                        end_str = end_match.group(1).strip() if end_match else "Not found"
                        offset_str = offset_match.group(1).strip() if offset_match else "Not found"
                        
                        raw_fields.append(f"time_start: '{start_str}'")
                        raw_fields.append(f"time_end: '{end_str}'")
                        raw_fields.append(f"time_start_offset: '{offset_str}'")
                        
                        embed.add_field(
                            name="1. Raw Field Extraction",
                            value="```" + "\n".join(raw_fields) + "```",
                            inline=False
                        )
                        
                        # Test individual date parsing
                        wiki_api = WikiAPI(API_URL_ZZZ, "In-Game_Events")
                        
                        if start_match:
                            start_parsed = wiki_api.parse_datetime_from_wiki_format(start_str)
                            embed.add_field(
                                name="2. Start Date Parsing",
                                value=f"Input: `{start_str}`\nResult: `{start_parsed}`",
                                inline=False
                            )
                        
                        if end_match:
                            end_parsed = wiki_api.parse_datetime_from_wiki_format(end_str)
                            embed.add_field(
                                name="3. End Date Parsing", 
                                value=f"Input: `{end_str}`\nResult: `{end_parsed}`",
                                inline=False
                            )
                        
                        # Test full parsing with timezone
                        date_result = wiki_api.parse_event_dates(content, test_event)
                        
                        if date_result:
                            start_date, end_date = date_result
                            today = datetime.now(timezone.utc)
                            
                            embed.add_field(
                                name="4. Final Parsed Results",
                                value=f"Start: `{start_date}`\nEnd: `{end_date}`\nToday: `{today.date()}`",
                                inline=False
                            )
                            
                            # Check if ongoing
                            today_aware = today.replace(tzinfo=timezone.utc) if today.tzinfo is None else today
                            start_aware = start_date.replace(tzinfo=timezone.utc) if start_date.tzinfo is None else start_date  
                            end_aware = end_date.replace(tzinfo=timezone.utc) if end_date.tzinfo is None else end_date
                            
                            is_ongoing = start_aware.date() <= today_aware.date() <= end_aware.date()
                            
                            status_text = []
                            if today_aware.date() < start_aware.date():
                                status_text.append("🔮 Future event")
                            elif today_aware.date() > end_aware.date():
                                status_text.append("🏁 Past event (ended)")
                            else:
                                status_text.append("✅ Currently ongoing!")
                                
                            embed.add_field(
                                name="5. Status Check",
                                value="\n".join(status_text),
                                inline=False
                            )
                        else:
                            embed.add_field(
                                name="4. Final Result",
                                value="❌ parse_event_dates() returned None",
                                inline=False
                            )
                            
                        await interaction.followup.send(embed=embed)
                        return
        
        await interaction.followup.send("❌ Failed to fetch test event")
        
    except Exception as e:
        error_embed = discord.Embed(
            title="Parsing Test Failed",
            description=f"Error: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed)

# Search for more recent ZZZ events
@client.tree.command(name="search_recent_zzz", description="Search for recent ZZZ events (2025)", guild=GUILD_OBJECT)
async def search_recent_zzz(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        
        import aiohttp
        from datetime import datetime
        
        async with aiohttp.ClientSession() as session:
            # Get more events from the category
            params = {
                "action": "query",
                "format": "json",
                "list": "categorymembers",
                "cmtitle": "Category:In-Game_Events", 
                "cmlimit": "100"  # Get more events
            }
            
            async with session.get(API_URL_ZZZ, params=params) as response:
                data = await response.json()
                members = data.get("query", {}).get("categorymembers", [])
                
                embed = discord.Embed(
                    title="ZZZ Event Search Results",
                    color=discord.Color.purple(),
                )
                
                if not members:
                    embed.description = "No events found in In-Game_Events category"
                    await interaction.followup.send(embed=embed)
                    return
                
                # Group events by year
                events_2024 = []
                events_2025 = []
                other_events = []
                
                for member in members:
                    title = member['title']
                    if '2024' in title:
                        events_2024.append(title)
                    elif '2025' in title:
                        events_2025.append(title)
                    else:
                        other_events.append(title)
                
                # Show results
                if events_2025:
                    embed.add_field(
                        name=f"🎉 2025 Events ({len(events_2025)})",
                        value="\n".join(events_2025[:10]) + (f"\n... and {len(events_2025)-10} more" if len(events_2025) > 10 else ""),
                        inline=False
                    )
                
                if events_2024:
                    embed.add_field(
                        name=f"📅 2024 Events ({len(events_2024)})",
                        value="\n".join(events_2024[:5]) + (f"\n... and {len(events_2024)-5} more" if len(events_2024) > 5 else ""),
                        inline=False
                    )
                    
                if other_events:
                    embed.add_field(
                        name=f"❓ Other Events ({len(other_events)})",
                        value="\n".join(other_events[:5]) + (f"\n... and {len(other_events)-5} more" if len(other_events) > 5 else ""),
                        inline=False
                    )
                
                embed.set_footer(text=f"Total events found: {len(members)}")
                
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="Search Failed", 
            description=f"Error: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed)

# Test parsing of a current 2025 ZZZ event
@client.tree.command(name="test_2025_event", description="Test parsing of a 2025 ZZZ event", guild=GUILD_OBJECT)
async def test_2025_event(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        
        import aiohttp
        from datetime import datetime, timezone
        
        # Test with a 2025 event that should be current
        test_event = '"En-Nah" Into Your Lap/2025-09-24'
        
        async with aiohttp.ClientSession() as session:
            # Get content of the 2025 event
            content_params = {
                "action": "query",
                "format": "json",
                "prop": "revisions",
                "titles": test_event,
                "rvprop": "content",
                "rvslots": "main"
            }
            
            async with session.get(API_URL_ZZZ, params=content_params) as response:
                data = await response.json()
                pages = data.get("query", {}).get("pages", {})
                
                if pages:
                    page_data = list(pages.values())[0]
                    
                    # Check if page exists
                    if 'missing' in page_data:
                        embed = discord.Embed(
                            title="Page Not Found",
                            description=f"The page '{test_event}' doesn't exist or has no content.",
                            color=discord.Color.red()
                        )
                        await interaction.followup.send(embed=embed)
                        return
                    
                    revisions = page_data.get("revisions", [])
                    
                    if revisions:
                        slots = revisions[0].get("slots", {})
                        main_slot = slots.get("main", {})
                        content = main_slot.get("*", "")
                        
                        embed = discord.Embed(
                            title=f"2025 Event Test: {test_event}",
                            color=discord.Color.green(),
                        )
                        
                        if content:
                            # Show first part of content
                            embed.add_field(
                                name="Content Preview",
                                value=f"```{content[:300]}```",
                                inline=False
                            )
                            
                            # Test parsing
                            wiki_api = WikiAPI(API_URL_ZZZ, "In-Game_Events")
                            date_result = wiki_api.parse_event_dates(content, test_event)
                            
                            if date_result:
                                start_date, end_date = date_result
                                today = datetime.now(timezone.utc)
                                
                                # Check if ongoing
                                today_aware = today.replace(tzinfo=timezone.utc) if today.tzinfo is None else today
                                start_aware = start_date.replace(tzinfo=timezone.utc) if start_date.tzinfo is None else start_date
                                end_aware = end_date.replace(tzinfo=timezone.utc) if end_date.tzinfo is None else end_date
                                
                                is_ongoing = start_aware.date() <= today_aware.date() <= end_aware.date()
                                
                                embed.add_field(
                                    name="Parsed Dates",
                                    value=f"Start: {start_date}\nEnd: {end_date}\nToday: {today.date()}",
                                    inline=False
                                )
                                
                                status = "✅ Currently ongoing!" if is_ongoing else ("🔮 Future event" if today_aware.date() < start_aware.date() else "🏁 Past event")
                                embed.add_field(name="Status", value=status, inline=False)
                                
                            else:
                                embed.add_field(name="Parsing Result", value="❌ Could not parse dates", inline=False)
                                
                                # Show what date patterns were found
                                import re
                                date_patterns = re.findall(r'\|\s*\w*(?:time|date|start|end)\w*\s*=\s*([^\n|]+)', content, re.IGNORECASE)
                                if date_patterns:
                                    embed.add_field(
                                        name="Found Date Patterns",
                                        value=f"```{', '.join(date_patterns[:5])}```",
                                        inline=False
                                    )
                        else:
                            embed.add_field(name="Issue", value="No content found in page", inline=False)
                            
                        await interaction.followup.send(embed=embed)
                        return
                        
                else:
                    embed = discord.Embed(
                        title="API Error",
                        description="No page data returned from API",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
        
    except Exception as e:
        error_embed = discord.Embed(
            title="Test Failed",
            description=f"Error: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed)

client.run(TOKEN)  # type: ignore - get a warning about str but this works

# TODO: Add a command to have the user specify the gacha game they want to see 
# then run backend code to get the event data for that specific game