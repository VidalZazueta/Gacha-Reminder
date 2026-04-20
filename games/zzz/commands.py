from __future__ import annotations

import re
import aiohttp
import discord
from datetime import datetime, timezone

from config import GUILD_OBJECT
from embeds import build_events_embed, build_error_embed, send_error
from api import WikiAPI
from .api import get_zzz_events_async
from .config import ZZZ_CONFIG


# ------------------------------------------------------------------ #
#  Shared helpers                                                      #
# ------------------------------------------------------------------ #

def _event_status_text(today_aware: datetime, start_aware: datetime, end_aware: datetime) -> str:
    if today_aware.date() < start_aware.date():
        return "🔮 Future event"
    if today_aware.date() > end_aware.date():
        return "🏁 Past event (ended)"
    return "✅ Currently ongoing!"


def _make_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def _fetch_page_content(session: aiohttp.ClientSession, title: str) -> str | None:
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": title,
        "rvprop": "content",
        "rvslots": "main",
    }
    async with session.get(ZZZ_CONFIG["api_url"], params=params) as resp:
        data = await resp.json()

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None

    page_data = next(iter(pages.values()))
    if "missing" in page_data:
        return None

    revisions = page_data.get("revisions", [])
    if not revisions:
        return None

    return revisions[0].get("slots", {}).get("main", {}).get("*", "")


async def _fetch_category_members(
    session: aiohttp.ClientSession,
    category: str,
    limit: int = 100,
) -> list[dict]:
    params = {
        "action": "query",
        "format": "json",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": str(limit),
    }
    async with session.get(ZZZ_CONFIG["api_url"], params=params) as resp:
        data = await resp.json()
    return data.get("query", {}).get("categorymembers", [])


def _make_zzz_embed(events: list, *, extra_footer: str = "") -> tuple[discord.Embed, discord.File]:
    footer = f"Found {len(events)} active events • Data from {ZZZ_CONFIG['display_name']} Wiki"
    if extra_footer:
        footer += f" • {extra_footer}"
    embed = build_events_embed(
        title=f"Current {ZZZ_CONFIG['display_name']} Events",
        events=events,
        footer=footer,
        color=ZZZ_CONFIG["color"],
        show_dates=True,
    )
    thumbnail = discord.File(ZZZ_CONFIG["thumbnail_path"], filename=ZZZ_CONFIG["thumbnail_filename"])
    embed.set_thumbnail(url=f"attachment://{ZZZ_CONFIG['thumbnail_filename']}")
    return embed, thumbnail


# ------------------------------------------------------------------ #
#  User-facing commands                                                #
# ------------------------------------------------------------------ #

def register_zzz_commands(client) -> None:
    @client.tree.command(
        name="events_zzz",
        description="Get the current events for Zenless Zone Zero",
        guild=GUILD_OBJECT,
    )
    async def events_zzz(interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer()
            events = await get_zzz_events_async(debug=True)
            if not events:
                await interaction.followup.send("No ongoing events right now.")
                return
            embed, thumbnail = _make_zzz_embed(events)
            await interaction.followup.send(embed=embed, file=thumbnail)
        except Exception as exc:
            print(f"[events_zzz] {exc}")
            await send_error(interaction, "Failed to fetch events. Please try again later.")


# ------------------------------------------------------------------ #
#  Dev commands                                                        #
# ------------------------------------------------------------------ #

def register_zzz_dev_commands(client) -> None:
    @client.tree.command(
        name="events_debug_zzz",
        description="[DEV] Get Zenless Zone Zero events with debug output",
        guild=GUILD_OBJECT,
    )
    async def events_debug_zzz(interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer()
            events = await get_zzz_events_async(debug=True)
            if not events:
                await interaction.followup.send("No ongoing ZZZ events right now.")
                return
            embed = build_events_embed(
                title="Current Zenless Zone Zero Events (Debug)",
                events=events,
                footer=f"Found {len(events)} active ZZZ events • Debug mode enabled",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)
        except Exception as exc:
            print(f"[events_debug_zzz] {exc}")
            await interaction.followup.send(
                embed=build_error_embed(description="Failed to fetch events. Check console for details.")
            )

    @client.tree.command(
        name="diagnose_zzz",
        description="[DEV] Diagnose ZZZ wiki category structure and content",
        guild=GUILD_OBJECT,
    )
    async def diagnose_zzz(interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer()
            embed = discord.Embed(title="ZZZ Wiki Diagnosis", color=discord.Color.gold())
            categories_to_test = ["In-Game_Events", "Events", "Event", "Activities", "Limited_Events"]

            async with aiohttp.ClientSession() as session:
                lines = []
                first_hit: str | None = None

                for cat in categories_to_test:
                    try:
                        members = await _fetch_category_members(session, cat, limit=10)
                        if members:
                            sample = ", ".join(m["title"] for m in members[:3])
                            lines.append(f"**{cat}**: {len(members)} pages\n  Sample: {sample}")
                            if first_hit is None:
                                first_hit = cat
                        else:
                            lines.append(f"**{cat}**: No pages found")
                    except Exception as exc:
                        print(f"[diagnose_zzz] {cat}: {exc}")
                        lines.append(f"**{cat}**: Error – {type(exc).__name__}")

                embed.add_field(name="Category Analysis", value="\n".join(lines), inline=False)

                if first_hit:
                    members = await _fetch_category_members(session, first_hit, limit=1)
                    if members:
                        test_page = members[0]["title"]
                        content = await _fetch_page_content(session, test_page)
                        if content:
                            preview = content[:500]
                            embed.add_field(
                                name=f"Sample Content: {test_page}",
                                value=f"```{preview}```",
                                inline=False,
                            )
                            date_patterns = re.findall(
                                r'\|\s*\w*(?:time|date|start|end)\w*\s*=\s*([^\n|]+)',
                                content,
                                re.IGNORECASE,
                            )
                            if date_patterns:
                                embed.add_field(
                                    name="Found Date Fields",
                                    value=f"```{', '.join(date_patterns[:5])}```",
                                    inline=False,
                                )
                            else:
                                embed.add_field(
                                    name="Date Fields",
                                    value="❌ No date fields found with standard patterns",
                                    inline=False,
                                )

            await interaction.followup.send(embed=embed)
        except Exception as exc:
            print(f"[diagnose_zzz] {exc}")
            await interaction.followup.send(
                embed=build_error_embed("Diagnosis Failed", "Diagnosis encountered an error. Check console for details.")
            )

    @client.tree.command(
        name="test_zzz_parsing",
        description='[DEV] Test date parsing for the ZZZ event "En-Nah" Assistant Program',
        guild=GUILD_OBJECT,
    )
    async def test_zzz_parsing(interaction: discord.Interaction) -> None:
        TEST_EVENT = '"En-Nah" Assistant Program'
        try:
            await interaction.response.defer()
            wiki_api = WikiAPI(ZZZ_CONFIG["api_url"], ZZZ_CONFIG["category"])

            async with aiohttp.ClientSession() as session:
                content = await _fetch_page_content(session, TEST_EVENT)

            embed = discord.Embed(
                title=f"Parsing Test: {TEST_EVENT}",
                color=discord.Color.blue(),
            )

            if not content:
                embed.description = "❌ Page not found or has no content."
                await interaction.followup.send(embed=embed)
                return

            start_match  = re.search(r'\|\s*time_start\s*=\s*([^\n|]+)', content)
            end_match    = re.search(r'\|\s*time_end\s*=\s*([^\n|]+)', content)
            offset_match = re.search(r'\|\s*time_start_offset\s*=\s*([^\n|]+)', content)

            raw = [
                f"time_start:        '{start_match.group(1).strip() if start_match else 'Not found'}'",
                f"time_end:          '{end_match.group(1).strip() if end_match else 'Not found'}'",
                f"time_start_offset: '{offset_match.group(1).strip() if offset_match else 'Not found'}'",
            ]
            embed.add_field(name="1. Raw Field Extraction", value="```" + "\n".join(raw) + "```", inline=False)

            if start_match:
                start_str    = start_match.group(1).strip()
                start_parsed = wiki_api.parse_datetime_from_wiki_format(start_str)
                embed.add_field(
                    name="2. Start Date Parsing",
                    value=f"Input: `{start_str}`\nResult: `{start_parsed}`",
                    inline=False,
                )
            if end_match:
                end_str    = end_match.group(1).strip()
                end_parsed = wiki_api.parse_datetime_from_wiki_format(end_str)
                embed.add_field(
                    name="3. End Date Parsing",
                    value=f"Input: `{end_str}`\nResult: `{end_parsed}`",
                    inline=False,
                )

            date_result = wiki_api.parse_event_dates(content, TEST_EVENT)
            if date_result:
                start_date, end_date = date_result
                today = datetime.now(timezone.utc)
                embed.add_field(
                    name="4. Final Parsed Results",
                    value=f"Start: `{start_date}`\nEnd: `{end_date}`\nToday: `{today.date()}`",
                    inline=False,
                )
                status = _event_status_text(
                    _make_aware(today), _make_aware(start_date), _make_aware(end_date)
                )
                embed.add_field(name="5. Status Check", value=status, inline=False)
            else:
                embed.add_field(name="4. Final Result", value="❌ parse_event_dates() returned None", inline=False)
                found = re.findall(r'\|\s*\w*(?:time|date|start|end)\w*\s*=\s*([^\n|]+)', content, re.IGNORECASE)
                if found:
                    embed.add_field(
                        name="Found Date Patterns",
                        value=f"```{', '.join(found[:5])}```",
                        inline=False,
                    )

            await interaction.followup.send(embed=embed)
        except Exception as exc:
            print(f"[test_zzz_parsing] {exc}")
            await interaction.followup.send(
                embed=build_error_embed("Parsing Test Failed", "Parsing test encountered an error. Check console for details.")
            )

    @client.tree.command(
        name="test_2025_event",
        description='[DEV] Verify date parsing for the 2025 ZZZ event "En-Nah" Into Your Lap',
        guild=GUILD_OBJECT,
    )
    async def test_2025_event(interaction: discord.Interaction) -> None:
        TEST_EVENT = '"En-Nah" Into Your Lap/2025-09-24'
        try:
            await interaction.response.defer()
            wiki_api = WikiAPI(ZZZ_CONFIG["api_url"], ZZZ_CONFIG["category"])

            async with aiohttp.ClientSession() as session:
                content = await _fetch_page_content(session, TEST_EVENT)

            embed = discord.Embed(
                title=f"2025 Event Test: {TEST_EVENT}",
                color=discord.Color.green(),
            )

            if not content:
                embed.description = "❌ Page not found or has no content."
                await interaction.followup.send(embed=embed)
                return

            embed.add_field(
                name="Content Preview",
                value=f"```{content[:300]}```",
                inline=False,
            )

            date_result = wiki_api.parse_event_dates(content, TEST_EVENT)
            if date_result:
                start_date, end_date = date_result
                today = datetime.now(timezone.utc)
                embed.add_field(
                    name="Parsed Dates",
                    value=f"Start: {start_date}\nEnd: {end_date}\nToday: {today.date()}",
                    inline=False,
                )
                status = _event_status_text(
                    _make_aware(today), _make_aware(start_date), _make_aware(end_date)
                )
                embed.add_field(name="Status", value=status, inline=False)
            else:
                embed.add_field(name="Parsing Result", value="❌ Could not parse dates", inline=False)
                found = re.findall(
                    r'\|\s*\w*(?:time|date|start|end)\w*\s*=\s*([^\n|]+)', content, re.IGNORECASE
                )
                if found:
                    embed.add_field(
                        name="Found Date Patterns",
                        value=f"```{', '.join(found[:5])}```",
                        inline=False,
                    )

            await interaction.followup.send(embed=embed)
        except Exception as exc:
            print(f"[test_2025_event] {exc}")
            await interaction.followup.send(
                embed=build_error_embed("Test Failed", "Test encountered an error. Check console for details.")
            )

    @client.tree.command(
        name="search_recent_zzz",
        description="[DEV] Search and browse recent ZZZ events from the wiki",
        guild=GUILD_OBJECT,
    )
    async def search_recent_zzz(interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer()

            async with aiohttp.ClientSession() as session:
                members = await _fetch_category_members(session, "In-Game_Events", limit=100)

            embed = discord.Embed(title="ZZZ Event Search Results", color=discord.Color.purple())

            if not members:
                embed.description = "No events found in In-Game_Events category."
                await interaction.followup.send(embed=embed)
                return

            buckets: dict[str, list[str]] = {}
            for m in members:
                title = m["title"]
                year = next((y for y in ("2025", "2024") if y in title), "other")
                buckets.setdefault(year, []).append(title)

            for year, label, emoji in (("2025", "2025 Events", "🎉"), ("2024", "2024 Events", "📅"), ("other", "Other Events", "❓")):
                items = buckets.get(year, [])
                if not items:
                    continue
                cap = 10 if year == "2025" else 5
                value = "\n".join(items[:cap])
                if len(items) > cap:
                    value += f"\n... and {len(items) - cap} more"
                embed.add_field(
                    name=f"{emoji} {label} ({len(items)})",
                    value=value,
                    inline=False,
                )

            embed.set_footer(text=f"Total events found: {len(members)}")
            await interaction.followup.send(embed=embed)
        except Exception as exc:
            print(f"[search_recent_zzz] {exc}")
            await interaction.followup.send(
                embed=build_error_embed("Search Failed", "Search encountered an error. Check console for details.")
            )