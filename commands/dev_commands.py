# commands/dev_commands.py
"""
Developer and diagnostic slash commands for the Gacha Reminder bot.

Per-game dev commands are registered by each game's module in games/.
This file registers cross-game dev commands and delegates per-game
dev command registration.

Registered commands:
* ``/events_debug``      — WUWA events with verbose debug output (via games.wuwa)
* ``/events_debug_zzz``  — ZZZ events with verbose debug output (via games.zzz)
* ``/diagnose_zzz``      — ZZZ wiki category diagnosis (via games.zzz)
* ``/test_zzz_parsing``  — ZZZ date parsing test (via games.zzz)
* ``/test_2025_event``   — ZZZ 2025 subpage test (via games.zzz)
* ``/search_recent_zzz`` — ZZZ event browser (via games.zzz)
* ``/test_network``      — Connectivity check for all wiki APIs.
"""
from __future__ import annotations

import time
import aiohttp
import discord

from config import GUILD_OBJECT
from embeds import build_error_embed
from games import GAME_CONFIG
from games.wuwa.commands import register_wuwa_dev_commands
from games.zzz.commands import register_zzz_dev_commands


def register_dev_commands(client) -> None:
    register_wuwa_dev_commands(client)
    register_zzz_dev_commands(client)

    @client.tree.command(
        name="test_network",
        description="[DEV] Test network connectivity to all wiki APIs",
        guild=GUILD_OBJECT,
    )
    async def test_network(interaction: discord.Interaction) -> None:
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
                        print(f"[test_network] {cfg['display_name']}: {exc}")
                        embed.add_field(
                            name=f"{cfg['emoji']} {cfg['display_name']}",
                            value=f"Status: ❌ Failed\nError: {type(exc).__name__}",
                            inline=True,
                        )
        except Exception as exc:
            print(f"[test_network] {exc}")
            embed = build_error_embed(
                title="Network Test Failed",
                description="Network test encountered an error. Check console for details.",
            )

        await interaction.followup.send(embed=embed)