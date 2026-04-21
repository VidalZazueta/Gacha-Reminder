from __future__ import annotations

import discord

from config import GUILD_OBJECT
from embeds import build_events_embed, build_error_embed
from .api import get_wuwa_events_async


def register_wuwa_dev_commands(client) -> None:
    @client.tree.command(
        name="events_debug",
        description="[DEV] Get Wuthering Waves events with debug output",
        guild=GUILD_OBJECT,
    )
    async def events_debug(interaction: discord.Interaction) -> None:
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
            await interaction.followup.send(
                embed=build_error_embed(description="Failed to fetch events. Check console for details.")
            )