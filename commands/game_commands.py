# commands/game_commands.py
"""
User-facing slash commands for displaying game events.

Per-game commands (/events_wuwa, /events_zzz, etc.) are registered
by each game's own module in games/. This file registers cross-game
commands and delegates per-game registration.

Registered commands:
* ``/events_wuwa``  — current Wuthering Waves events (via games.wuwa)
* ``/events_zzz``   — current Zenless Zone Zero events (via games.zzz)
* ``/events_all``   — events from all supported games in one embed.
* ``/events_timed`` — Wuthering Waves events with timing stats (via games.wuwa)
"""
from __future__ import annotations

import asyncio
import discord

from config import GUILD_OBJECT
from embeds import send_error
from games import get_wuwa_events_async, get_zzz_events_async, GAME_CONFIG
from games.wuwa.commands import register_wuwa_commands
from games.zzz.commands import register_zzz_commands



def register_game_commands(client) -> None:
    register_wuwa_commands(client)
    register_zzz_commands(client)

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
            await send_error(interaction, "Failed to fetch events. Please try again later.")