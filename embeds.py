# embeds.py - Reusable Discord embed builders
"""
Reusable Discord embed factory functions for the Gacha Reminder bot.

Provides helpers for formatting event lists, building styled embeds,
and sending error responses that work regardless of interaction state.
"""
from __future__ import annotations
from typing import List, Dict, Optional
import discord


def build_event_list(events: List[Dict], show_dates: bool = True) -> List[str]:
    """Format a list of event dicts into human-readable display strings.

    Each event is rendered as a bolded title followed by its time
    remaining and, optionally, its date range.

    Args:
        events (List[Dict]): List of event dictionaries. Each dict must
            contain the keys ``"title"``, ``"time_remaining"``, and
            (when ``show_dates`` is ``True``) ``"date_range_str"``.
        show_dates (bool): When ``True`` (default), appends the date
            range to each entry. When ``False``, only the title and
            time remaining are shown.

    Returns:
        List[str]: Formatted markdown strings, one per event.
    """
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
    """Build a standard Discord embed for displaying a list of game events.

    The embed description is populated with the formatted event list
    produced by :func:`build_event_list`. If no events are provided the
    description falls back to a "No ongoing events" message.

    Args:
        title (str): The embed title shown at the top of the card.
        events (List[Dict]): List of event dicts to display (see
            :func:`build_event_list` for expected keys).
        footer (str): Text placed in the embed footer.
        color (discord.Color): Accent color for the embed side-bar.
        show_dates (bool): Passed through to :func:`build_event_list`;
            controls whether date ranges are included (default ``True``).

    Returns:
        discord.Embed: A fully configured embed ready to be sent.
    """
    embed = discord.Embed(title=title, color=color)
    if events:
        embed.description = "\n\n".join(build_event_list(events, show_dates=show_dates))
    else:
        embed.description = "No ongoing events right now."
    embed.set_footer(text=footer)
    return embed


def build_error_embed(title: str = "Error", description: str = "") -> discord.Embed:
    """Build a standard red error embed.

    Args:
        title (str): The embed title (default ``"Error"``).
        description (str): A short description of the error
            (default empty string).

    Returns:
        discord.Embed: An embed with :attr:`discord.Color.red` styling.
    """
    return discord.Embed(title=title, description=description, color=discord.Color.red())


async def send_error(interaction: discord.Interaction, message: str) -> None:
    """Send an error message that works regardless of interaction state.

    Uses :meth:`discord.InteractionResponse.followup` when the
    interaction has already been deferred or responded to, and falls
    back to :meth:`discord.InteractionResponse.send_message` otherwise.

    Args:
        interaction (discord.Interaction): The active Discord interaction.
        message (str): The error text to display to the user.
    """
    if interaction.response.is_done():
        await interaction.followup.send(f"Error: {message}")
    else:
        await interaction.response.send_message(f"Error: {message}")