# embeds.py - Reusable Discord embed builders
from __future__ import annotations
from typing import List, Dict, Optional
import discord


def build_event_list(events: List[Dict], show_dates: bool = True) -> List[str]:
    """Format a list of event dicts into display strings."""
    lines = []
    for event in events:
        name      = event["title"]
        time_left = event["time_remaining"]
        if show_dates:
            dates = event["date_range_str"]
            lines.append(f"**{name}**\nTime left: {time_left} | {dates}")
        else:
            lines.append(f"**{name}** - {time_left}")
    return lines


def build_events_embed(
    title: str,
    events: List[Dict],
    footer: str,
    color: discord.Color,
    show_dates: bool = True,
) -> discord.Embed:
    """Build a standard events embed."""
    embed = discord.Embed(title=title, color=color)
    if events:
        embed.description = "\n\n".join(build_event_list(events, show_dates=show_dates))
    else:
        embed.description = "No ongoing events right now."
    embed.set_footer(text=footer)
    return embed


def build_error_embed(title: str = "Error", description: str = "") -> discord.Embed:
    """Build a standard error embed."""
    return discord.Embed(title=title, description=description, color=discord.Color.red())


async def send_error(interaction: discord.Interaction, message: str) -> None:
    """Send an error message regardless of whether the response has been deferred."""
    if interaction.response.is_done():
        await interaction.followup.send(f"Error: {message}")
    else:
        await interaction.response.send_message(f"Error: {message}")