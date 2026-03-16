# commands/game_commands.py
# User-facing slash commands: /events_wuwa, /events_zzz, /events_all, /events_timed
from __future__ import annotations

import asyncio
import time
import discord

from config import GUILD_OBJECT, GAME_CONFIG
from embeds import build_events_embed, build_error_embed, send_error
from wiki_api import WikiAPI, get_wuwa_events_async, get_zzz_events_async


def _make_game_embed(
    game_key: str,
    events: list,
    *,
    extra_footer: str = "",
) -> tuple[discord.Embed, discord.File]:
    """
    Build the standard per-game embed + thumbnail File for a given game key.
    Returns (embed, file) so callers can pass both to followup.send().
    """
    cfg = GAME_CONFIG[game_key]

    footer = f"Found {len(events)} active events • Data from {cfg['display_name']} Wiki"
    if extra_footer:
        footer += f" • {extra_footer}"

    embed = build_events_embed(
        title=f"Current {cfg['display_name']} Events",
        events=events,
        footer=footer,
        color=cfg["color"],
        show_dates=True,
    )

    thumbnail = discord.File(cfg["thumbnail_path"], filename=cfg["thumbnail_filename"])
    embed.set_thumbnail(url=f"attachment://{cfg['thumbnail_filename']}")

    return embed, thumbnail


def register_game_commands(client: discord.ext.commands.Bot) -> None:  # type: ignore[name-defined]
    """Register all user-facing game commands onto the bot's command tree."""

    # ------------------------------------------------------------------ #
    #  /events_wuwa                                                        #
    # ------------------------------------------------------------------ #
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

            embed, thumbnail = _make_game_embed("wuwa", events)
            await interaction.followup.send(embed=embed, file=thumbnail)

        except Exception as exc:
            print(f"[events_wuwa] {exc}")
            await send_error(interaction, str(exc)[:100])

    # ------------------------------------------------------------------ #
    #  /events_zzz                                                         #
    # ------------------------------------------------------------------ #
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

            embed, thumbnail = _make_game_embed("zzz", events)
            await interaction.followup.send(embed=embed, file=thumbnail)

        except Exception as exc:
            print(f"[events_zzz] {exc}")
            await send_error(interaction, str(exc)[:100])

    # ------------------------------------------------------------------ #
    #  /events_all                                                         #
    # ------------------------------------------------------------------ #
    @client.tree.command(
        name="events_all",
        description="Get current events from all supported games",
        guild=GUILD_OBJECT,
    )
    async def events_all(interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer()

            wuwa_events, zzz_events = await asyncio.gather(
                get_wuwa_events_async(debug=False),
                get_zzz_events_async(debug=False),
            )

            embed = discord.Embed(
                title="Current Events – All Games",
                color=discord.Color.purple(),
            )

            sections = []
            for game_key, events in (("wuwa", wuwa_events), ("zzz", zzz_events)):
                cfg = GAME_CONFIG[game_key]
                if events:
                    lines = [f"**{e['title']}** - {e['time_remaining']}" for e in events]
                    sections.append(
                        f"**{cfg['emoji']} {cfg['display_name']} ({len(events)} events)**\n"
                        + "\n".join(lines)
                    )
                else:
                    sections.append(f"**{cfg['emoji']} {cfg['display_name']}**\nNo ongoing events")

            embed.description = "\n\n".join(sections)
            total = len(wuwa_events) + len(zzz_events)
            embed.set_footer(text=f"Total: {total} active events across all games")

            await interaction.followup.send(embed=embed)

        except Exception as exc:
            print(f"[events_all] {exc}")
            await send_error(interaction, str(exc)[:100])

    # ------------------------------------------------------------------ #
    #  /events_timed  (shows WUWA events + fetch timing stats)            #
    # ------------------------------------------------------------------ #
    @client.tree.command(
        name="events_timed",
        description="Get Wuthering Waves events with detailed timing stats",
        guild=GUILD_OBJECT,
    )
    async def events_timed(interaction: discord.Interaction) -> None:
        overall_start = time.time()
        try:
            await interaction.response.defer()

            cfg = GAME_CONFIG["wuwa"]
            wiki_api = WikiAPI(cfg["api_url"], cfg["category"])

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
                footer="",          # footer set below with timing info
                color=discord.Color.gold(),
                show_dates=True,
            )
            process_time = round(time.time() - process_start, 3)
            total_time   = round(time.time() - overall_start, 2)

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
            await send_error(interaction, f"Failed after {elapsed}s: {str(exc)[:80]}")