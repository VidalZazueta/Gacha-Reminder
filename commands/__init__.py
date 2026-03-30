# commands/__init__.py
"""
Command registration package for the Gacha Reminder bot.

Exports the two registration functions that attach all slash commands
to the bot's application command tree:

* :func:`register_game_commands` — user-facing event commands.
* :func:`register_dev_commands`  — developer/diagnostic commands.
"""
from .game_commands import register_game_commands
from .dev_commands  import register_dev_commands

__all__ = ["register_game_commands", "register_dev_commands"]