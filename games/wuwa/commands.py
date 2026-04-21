from __future__ import annotations

import time
import discord

from config import GUILD_OBJECT
from embeds import build_events_embed, send_error
from api import WikiAPI
from .api import get_wuwa_events_async
from .config import WUWA_CONFIG


def _make_wuwa_embed(events: list, *, extra_footer: str = "") -> tuple[discord.Embed, discord.File]:
    footer = f"Found {len(events)} active events • Data from {WUWA_CONFIG['display_name']} Wiki"
    if extra_footer:
        footer += f" • {extra_footer}"
    embed = build_events_embed(
        title=f"Current {WUWA_CONFIG['display_name']} Events",
        events=events,
        footer=footer,
        color=WUWA_CONFIG["color"],
        show_dates=True,
    )
    thumbnail = discord.File(WUWA_CONFIG["thumbnail_path"], filename=WUWA_CONFIG["thumbnail_filename"])
    embed.set_thumbnail(url=f"attachment://{WUWA_CONFIG['thumbnail_filename']}")
    return embed, thumbnail


def register_wuwa_commands(client) -> None:
    @client.tree.command(
        name="events_wuwa",
        description="Get the current events for Wuthering Waves",
        guild=GUILD_OBJECT,
    )
    async def events_wuwa(interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer()
            events = await get_wuwa_events_async(debug=True)
            if not events:
                await interaction.followup.send("No ongoing events right now.")
                return
            embed, thumbnail = _make_wuwa_embed(events)
            await interaction.followup.send(embed=embed, file=thumbnail)
        except Exception as exc:
            print(f"[events_wuwa] {exc}")
            await send_error(interaction, "Failed to fetch events. Please try again later.")

    @client.tree.command(
        name="events_timed",
        description="Get Wuthering Waves events with detailed timing stats",
        guild=GUILD_OBJECT,
    )
    async def events_timed(interaction: discord.Interaction) -> None:
        overall_start = time.time()
        try:
            await interaction.response.defer()
            wiki_api = WikiAPI(WUWA_CONFIG["api_url"], WUWA_CONFIG["category"])

            fetch_start = time.time()
            events = await wiki_api.get_ongoing_events_async(debug=True)
            fetch_time = round(time.time() - fetch_start, 2)

            if not events:
                await interaction.followup.send("No ongoing events right now.")
                return

            process_start = time.time()
            embed = build_events_embed(
                title="Current Wuthering Waves Events (Timed)",
                events=events,
                footer="",
                color=discord.Color.gold(),
                show_dates=True,
            )
            process_time = round(time.time() - process_start, 3)
            total_time = round(time.time() - overall_start, 2)
            embed.set_footer(
                text=(
                    f"Found {len(events)} events • "
                    f"Fetch: {fetch_time}s • "
                    f"Process: {process_time}s • "
                    f"Total: {total_time}s"
                )
            )
            send_start = time.time()
            await interaction.followup.send(embed=embed)
            print(f"[TIMING] Send: {round(time.time() - send_start, 3)}s | Total: {total_time}s")
        except Exception as exc:
            elapsed = round(time.time() - overall_start, 2)
            print(f"[events_timed] Failed after {elapsed}s: {exc}")
            await send_error(interaction, f"Failed after {elapsed}s. Please try again later.")