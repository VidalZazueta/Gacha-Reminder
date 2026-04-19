# commands/dev_commands.py
"""
Developer and diagnostic slash commands for the Gacha Reminder bot.

These commands are intended for internal debugging and are not meant for
regular users. They expose low-level wiki API behaviour, raw parsing
results, and network connectivity checks.

Registered commands:

* ``/events_debug``      — WUWA events with verbose debug output.
* ``/events_debug_zzz``  — ZZZ events with verbose debug output.
* ``/test_network``      — Connectivity and latency check for all wiki APIs.
* ``/diagnose_zzz``      — Inspect ZZZ wiki category structure and sample content.
* ``/test_zzz_parsing``  — Step-by-step date parsing test for a known ZZZ event.
* ``/test_2025_event``   — Verify parsing for a specific 2025 ZZZ subpage.
* ``/search_recent_zzz`` — Browse ZZZ In-Game_Events category grouped by year.
"""
from __future__ import annotations

import re
import time
import aiohttp
import discord
from datetime import datetime, timezone

from config import GUILD_OBJECT, GAME_CONFIG, API_URL_WUWA, API_URL_ZZZ
from embeds import build_events_embed, build_error_embed
from api import WikiAPI, get_wuwa_events_async, get_zzz_events_async


# ------------------------------------------------------------------ #
#  Shared helpers                                                      #
# ------------------------------------------------------------------ #

def _event_status_text(
    today_aware: datetime,
    start_aware: datetime,
    end_aware: datetime,
) -> str:
    """Return a human-readable status emoji and label for an event.

    All three datetimes must be timezone-aware to ensure correct date
    comparisons across UTC offsets.

    Args:
        today_aware (datetime): Current UTC datetime (timezone-aware).
        start_aware (datetime): Event start datetime (timezone-aware).
        end_aware (datetime): Event end datetime (timezone-aware).

    Returns:
        str: One of:

        * ``"🔮 Future event"``        — event has not started yet.
        * ``"✅ Currently ongoing!"``  — event is active today.
        * ``"🏁 Past event (ended)"``  — event has already ended.
    """
    if today_aware.date() < start_aware.date():
        return "🔮 Future event"
    if today_aware.date() > end_aware.date():
        return "🏁 Past event (ended)"
    return "✅ Currently ongoing!"


def _make_aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware by attaching UTC if needed.

    Args:
        dt (datetime): A naive or aware datetime.

    Returns:
        datetime: The same datetime with :data:`datetime.timezone.utc`
        attached if it was naive, or unchanged if already aware.
    """
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def _fetch_page_content(
    session: aiohttp.ClientSession,
    api_url: str,
    title: str,
) -> str | None:
    """Fetch the raw wikitext for a single wiki page.

    Queries the MediaWiki ``revisions`` API for the main slot content of
    the given page title.

    Args:
        session (aiohttp.ClientSession): An open aiohttp session to reuse.
        api_url (str): Full ``api.php`` URL of the target wiki.
        title (str): Exact page title to fetch (case-sensitive).

    Returns:
        str | None: Raw wikitext string, or ``None`` if the page does not
        exist, is marked as missing, or has no revisions.
    """
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": title,
        "rvprop": "content",
        "rvslots": "main",
    }
    async with session.get(api_url, params=params) as resp:
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
    api_url: str,
    category: str,
    limit: int = 100,
) -> list[dict]:
    """Fetch the member pages of a MediaWiki category.

    Args:
        session (aiohttp.ClientSession): An open aiohttp session to reuse.
        api_url (str): Full ``api.php`` URL of the target wiki.
        category (str): Category name without the ``Category:`` prefix
            (e.g. ``"In-Game_Events"``).
        limit (int): Maximum number of members to return (default ``100``).

    Returns:
        list[dict]: List of member dicts as returned by the MediaWiki API.
        Each dict contains at least a ``"title"`` key. Returns ``[]`` if
        the category is empty or the request fails.
    """
    params = {
        "action": "query",
        "format": "json",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": str(limit),
    }
    async with session.get(api_url, params=params) as resp:
        data = await resp.json()
    return data.get("query", {}).get("categorymembers", [])


# ------------------------------------------------------------------ #
#  Registration                                                        #
# ------------------------------------------------------------------ #

def register_dev_commands(client) -> None:  # type: ignore[type-arg]
    """Register all developer and diagnostic slash commands onto the bot's command tree.

    All commands are prefixed with ``[DEV]`` in their description to
    signal they are for internal use. Commands are scoped to the guild
    defined in :data:`config.GUILD_OBJECT`.

    Args:
        client: The bot instance whose ``tree`` the commands are added to.
    """

    # ---------------------------------------------------------------- #
    #  /events_debug  –  WUWA debug mode                               #
    # ---------------------------------------------------------------- #
    @client.tree.command(
        name="events_debug",
        description="[DEV] Get Wuthering Waves events with debug output",
        guild=GUILD_OBJECT,
    )
    async def events_debug(interaction: discord.Interaction) -> None:
        """Slash command: display WUWA events fetched with debug logging enabled.

        Args:
            interaction (discord.Interaction): The invoking Discord interaction.
        """
        try:
            await interaction.response.defer()
            events = await get_wuwa_events_async(debug=True)
            if not events:
                await interaction.followup.send("No ongoing events right now.")
                return
            embed = build_events_embed(
                title="Current Wuthering Waves Events (Debug)",
                events=events,
                footer=f"Found {len(events)} active events • Debug mode enabled",
                color=discord.Color.orange(),
            )
            await interaction.followup.send(embed=embed)
        except Exception as exc:
            print(f"[events_debug] {exc}")
            await interaction.followup.send(embed=build_error_embed(description=str(exc)[:500]))

    # ---------------------------------------------------------------- #
    #  /events_debug_zzz  –  ZZZ debug mode                            #
    # ---------------------------------------------------------------- #
    @client.tree.command(
        name="events_debug_zzz",
        description="[DEV] Get Zenless Zone Zero events with debug output",
        guild=GUILD_OBJECT,
    )
    async def events_debug_zzz(interaction: discord.Interaction) -> None:
        """Slash command: display ZZZ events fetched with debug logging enabled.

        Args:
            interaction (discord.Interaction): The invoking Discord interaction.
        """
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
            await interaction.followup.send(embed=build_error_embed(description=str(exc)[:500]))

    # ---------------------------------------------------------------- #
    #  /test_network                                                    #
    # ---------------------------------------------------------------- #
    @client.tree.command(
        name="test_network",
        description="[DEV] Test network connectivity to all wiki APIs",
        guild=GUILD_OBJECT,
    )
    async def test_network(interaction: discord.Interaction) -> None:
        """Slash command: test connectivity and latency for all configured wiki APIs.

        Sends a lightweight ``siteinfo`` query to each game's API URL and
        reports response time and success status in an embed.

        Args:
            interaction (discord.Interaction): The invoking Discord interaction.
        """
        await interaction.response.defer()
        embed = discord.Embed(title="Network Test Results", color=discord.Color.blue())

        try:
            test_params = {"action": "query", "format": "json", "meta": "siteinfo"}
            async with aiohttp.ClientSession() as session:
                for game_key, cfg in GAME_CONFIG.items():
                    start = time.time()
                    try:
                        async with session.get(cfg["api_url"], params=test_params) as resp:
                            data = await resp.json()
                        elapsed = round(time.time() - start, 3)
                        status = "✅ Connected" if "query" in data else "⚠️ Partial"
                        embed.add_field(
                            name=f"{cfg['emoji']} {cfg['display_name']}",
                            value=f"Status: {status}\nResponse: {elapsed}s",
                            inline=True,
                        )
                    except Exception as exc:
                        embed.add_field(
                            name=f"{cfg['emoji']} {cfg['display_name']}",
                            value=f"Status: ❌ Failed\nError: {str(exc)[:50]}",
                            inline=True,
                        )
        except Exception as exc:
            embed = build_error_embed(title="Network Test Failed", description=str(exc)[:500])

        await interaction.followup.send(embed=embed)

    # ---------------------------------------------------------------- #
    #  /diagnose_zzz                                                    #
    # ---------------------------------------------------------------- #
    @client.tree.command(
        name="diagnose_zzz",
        description="[DEV] Diagnose ZZZ wiki category structure and content",
        guild=GUILD_OBJECT,
    )
    async def diagnose_zzz(interaction: discord.Interaction) -> None:
        """Slash command: probe ZZZ wiki category names and show a content sample.

        Tests a predefined list of candidate category names against the ZZZ
        wiki, reports how many pages each contains, and previews the wikitext
        of the first page found along with any detected date fields.

        Args:
            interaction (discord.Interaction): The invoking Discord interaction.
        """
        try:
            await interaction.response.defer()
            embed = discord.Embed(title="ZZZ Wiki Diagnosis", color=discord.Color.gold())
            categories_to_test = ["In-Game_Events", "Events", "Event", "Activities", "Limited_Events"]

            async with aiohttp.ClientSession() as session:
                lines = []
                first_hit: str | None = None

                for cat in categories_to_test:
                    try:
                        members = await _fetch_category_members(session, API_URL_ZZZ, cat, limit=10)
                        if members:
                            sample = ", ".join(m["title"] for m in members[:3])
                            lines.append(f"**{cat}**: {len(members)} pages\n  Sample: {sample}")
                            if first_hit is None:
                                first_hit = cat
                        else:
                            lines.append(f"**{cat}**: No pages found")
                    except Exception as exc:
                        lines.append(f"**{cat}**: Error – {str(exc)[:50]}")

                embed.add_field(name="Category Analysis", value="\n".join(lines), inline=False)

                # Show raw content preview of first available event
                if first_hit:
                    members = await _fetch_category_members(session, API_URL_ZZZ, first_hit, limit=1)
                    if members:
                        test_page = members[0]["title"]
                        content = await _fetch_page_content(session, API_URL_ZZZ, test_page)
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
            await interaction.followup.send(
                embed=build_error_embed("Diagnosis Failed", str(exc)[:500])
            )

    # ---------------------------------------------------------------- #
    #  /test_zzz_parsing  –  inspect one known ZZZ event               #
    # ---------------------------------------------------------------- #
    @client.tree.command(
        name="test_zzz_parsing",
        description='[DEV] Test date parsing for the ZZZ event "En-Nah" Assistant Program',
        guild=GUILD_OBJECT,
    )
    async def test_zzz_parsing(interaction: discord.Interaction) -> None:
        """Slash command: step-by-step date parsing inspection for a known ZZZ event.

        Fetches the page for ``"En-Nah" Assistant Program``, then displays:
        raw field extraction, individual date parse results, the final
        :meth:`WikiAPI.parse_event_dates` output, and the computed event status.

        Args:
            interaction (discord.Interaction): The invoking Discord interaction.
        """
        TEST_EVENT = '"En-Nah" Assistant Program'
        try:
            await interaction.response.defer()
            wiki_api = WikiAPI(API_URL_ZZZ, "In-Game_Events")

            async with aiohttp.ClientSession() as session:
                content = await _fetch_page_content(session, API_URL_ZZZ, TEST_EVENT)

            embed = discord.Embed(
                title=f"Parsing Test: {TEST_EVENT}",
                color=discord.Color.blue(),
            )

            if not content:
                embed.description = "❌ Page not found or has no content."
                await interaction.followup.send(embed=embed)
                return

            # Raw field extraction
            start_match  = re.search(r'\|\s*time_start\s*=\s*([^\n|]+)', content)
            end_match    = re.search(r'\|\s*time_end\s*=\s*([^\n|]+)', content)
            offset_match = re.search(r'\|\s*time_start_offset\s*=\s*([^\n|]+)', content)

            raw = [
                f"time_start:        '{start_match.group(1).strip() if start_match else 'Not found'}'",
                f"time_end:          '{end_match.group(1).strip() if end_match else 'Not found'}'",
                f"time_start_offset: '{offset_match.group(1).strip() if offset_match else 'Not found'}'",
            ]
            embed.add_field(name="1. Raw Field Extraction", value="```" + "\n".join(raw) + "```", inline=False)

            # Individual date parsing
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

            # Full parse + status
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
            await interaction.followup.send(
                embed=build_error_embed("Parsing Test Failed", str(exc))
            )

    # ---------------------------------------------------------------- #
    #  /test_2025_event  –  verify a specific 2025 ZZZ subpage         #
    # ---------------------------------------------------------------- #
    @client.tree.command(
        name="test_2025_event",
        description='[DEV] Verify date parsing for the 2025 ZZZ event "En-Nah" Into Your Lap',
        guild=GUILD_OBJECT,
    )
    async def test_2025_event(interaction: discord.Interaction) -> None:
        """Slash command: verify date parsing for a specific 2025 ZZZ wiki subpage.

        Targets ``"En-Nah" Into Your Lap/2025-09-24``, which uses the
        dated subpage naming convention. Shows a content preview, parsed
        dates, and event status.

        Args:
            interaction (discord.Interaction): The invoking Discord interaction.
        """
        TEST_EVENT = '"En-Nah" Into Your Lap/2025-09-24'
        try:
            await interaction.response.defer()
            wiki_api = WikiAPI(API_URL_ZZZ, "In-Game_Events")

            async with aiohttp.ClientSession() as session:
                content = await _fetch_page_content(session, API_URL_ZZZ, TEST_EVENT)

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
            await interaction.followup.send(
                embed=build_error_embed("Test Failed", str(exc))
            )

    # ---------------------------------------------------------------- #
    #  /search_recent_zzz  –  browse ZZZ In-Game_Events by year        #
    # ---------------------------------------------------------------- #
    @client.tree.command(
        name="search_recent_zzz",
        description="[DEV] Search and browse recent ZZZ events from the wiki",
        guild=GUILD_OBJECT,
    )
    async def search_recent_zzz(interaction: discord.Interaction) -> None:
        """Slash command: browse ZZZ In-Game_Events category grouped by year.

        Fetches up to 100 members from the ``In-Game_Events`` category and
        buckets them into 2025, 2024, and "other" groups. Displays the top
        10 entries from 2025 and top 5 from 2024.

        Args:
            interaction (discord.Interaction): The invoking Discord interaction.
        """
        try:
            await interaction.response.defer()

            async with aiohttp.ClientSession() as session:
                members = await _fetch_category_members(
                    session, API_URL_ZZZ, "In-Game_Events", limit=100
                )

            embed = discord.Embed(title="ZZZ Event Search Results", color=discord.Color.purple())

            if not members:
                embed.description = "No events found in In-Game_Events category."
                await interaction.followup.send(embed=embed)
                return

            # Group by year
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
            await interaction.followup.send(
                embed=build_error_embed("Search Failed", str(exc))
            )