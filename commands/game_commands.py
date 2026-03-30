# commands/game_commands.py
"""
User-facing slash commands for displaying game events.

Registers the following commands on the bot's application command tree:

* ``/events_wuwa``  — current Wuthering Waves events with thumbnail.
* ``/events_zzz``   — current Zenless Zone Zero events with thumbnail.
* ``/events_all``   — events from all supported games in one embed.
* ``/events_timed`` — Wuthering Waves events with fetch/process timing stats.
"""
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
    """Build the standard per-game embed and thumbnail file.

    Looks up game metadata from :data:`config.GAME_CONFIG` and delegates
    to :func:`embeds.build_events_embed` to produce a consistently styled
    embed. The thumbnail image is loaded from disk as a
    :class:`discord.File` and attached via ``attachment://`` URL so it
    renders inline.

    Args:
        game_key (str): Key into :data:`config.GAME_CONFIG`
            (``"wuwa"`` or ``"zzz"``).
        events (list): List of ongoing event dicts as returned by the
            wiki API.
        extra_footer (str): Optional text appended to the embed footer
            after the standard event count and source credit
            (default ``""``).

    Returns:
        tuple[discord.Embed, discord.File]: The configured embed and the
        thumbnail file object. Both must be passed to
        ``interaction.followup.send()`` together.
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
    """Register all user-facing game slash commands onto the bot's command tree.

    Defines and registers the following guild-scoped slash commands:

    * ``/events_wuwa``  — fetches and displays current Wuthering Waves events.
    * ``/events_zzz``   — fetches and displays current Zenless Zone Zero events.
    * ``/events_all``   — fetches both games concurrently and shows a combined embed.
    * ``/events_timed`` — like ``/events_wuwa`` but includes fetch/process timing in the footer.

    Args:
        client (discord.ext.commands.Bot): The bot instance whose
            ``tree`` the commands are added to.
    """

    # ------------------------------------------------------------------ #
    #  /events_wuwa                                                        #
    # ------------------------------------------------------------------ #
    @client.tree.command(
        name="events_wuwa",
        description="Get the current events for Wuthering Waves",
        guild=GUILD_OBJECT,
    )
    async def events_wuwa(interaction: discord.Interaction) -> None:
        """Slash command: display current Wuthering Waves events.

        Defers the response, fetches events via :func:`wiki_api.get_wuwa_events_async`,
        and sends a styled embed with a game thumbnail attached.

        Args:
            interaction (discord.Interaction): The invoking Discord interaction.
        """
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
        """Slash command: display current Zenless Zone Zero events.

        Defers the response, fetches events via :func:`wiki_api.get_zzz_events_async`,
        and sends a styled embed with a game thumbnail attached.

        Args:
            interaction (discord.Interaction): The invoking Discord interaction.
        """
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
        """Slash command: display current events from all supported games.

        Fetches Wuthering Waves and Zenless Zone Zero events concurrently
        via :func:`asyncio.gather`, then builds a single combined embed
        with a section per game.

        Args:
            interaction (discord.Interaction): The invoking Discord interaction.
        """
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
        """Slash command: display Wuthering Waves events with fetch/process timing.

        Same output as ``/events_wuwa`` but includes fetch time, embed
        build time, and total elapsed time in the embed footer. Useful
        for performance monitoring.

        Args:
            interaction (discord.Interaction): The invoking Discord interaction.
        """
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