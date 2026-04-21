from __future__ import annotations

import discord

from config import GUILD_OBJECT
from embeds import build_events_embed, send_error
from .api import get_zzz_events_async
from .config import ZZZ_CONFIG


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