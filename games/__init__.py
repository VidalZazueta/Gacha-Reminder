from .wuwa import get_wuwa_events_async, WUWA_CONFIG
from .zzz import get_zzz_events_async, ZZZ_CONFIG

# Aggregated config — add new games here as you expand the project
GAME_CONFIG = {
    "wuwa": WUWA_CONFIG,
    "zzz": ZZZ_CONFIG,
}

__all__ = ["get_wuwa_events_async", "get_zzz_events_async", "GAME_CONFIG", "WUWA_CONFIG", "ZZZ_CONFIG"]