# commands/__init__.py
from .game_commands import register_game_commands
from .dev_commands  import register_dev_commands

__all__ = ["register_game_commands", "register_dev_commands"]