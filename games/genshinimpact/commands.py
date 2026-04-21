from __future__ import annotations

import time
import discord

from config import GUILD_OBJECT
from embeds import build_events_embed, send_error
from api import WikiAPI
from .api import get_genshinimpact_events_async
from .config import GENSHINIMPACT_CONFIG

def _make_genshinimpact_embed(events: list, *, extra_footer: str = "") -> tuple[discord.Embed, discord.File]:
    footer = f"Found {len(events)} active events • Data from {GENSHINIMPACT_CONFIG['display_name']} Wiki"
    if extra_footer:
        footer += f" • {extra_footer}"
    embed = build_events_embed(
        title=f"Current {GENSHINIMPACT_CONFIG['display_name']} Events",
        events=events,
        footer=footer,
        color=GENSHINIMPACT_CONFIG["color"],
        show_dates=True,
    )
    thumbnail = discord.File(GENSHINIMPACT_CONFIG["thumbnail_path"], filename=GENSHINIMPACT_CONFIG["thumbnail_filename"])
    embed.set_thumbnail(url=f"attachment://{GENSHINIMPACT_CONFIG['thumbnail_filename']}")
    return embed, thumbnail

def register_genshinimpact_commands(client) -> None:
    @client.tree.command(
        name="events_genshinimpact",
        description="Get the current events for Genshin Impact",
        guild=GUILD_OBJECT,
    )
    async def events_genshinimpact(interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer()
            events = await get_genshinimpact_events_async(debug=True)
            if not events:
                await interaction.followup.send("No ongoing events right now.")
                return
            embed, thumbnail = _make_genshinimpact_embed(events)
            await interaction.followup.send(embed=embed, file=thumbnail)
        except Exception as exc:
            print(f"[events_genshinimpact] {exc}")
            await send_error(interaction, "Failed to fetch events. Please try again later.")