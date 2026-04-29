from .wuwa import get_wuwa_events_async, WUWA_CONFIG
from .zzz import get_zzz_events_async, ZZZ_CONFIG
from .genshinimpact import get_genshinimpact_events_async, GENSHINIMPACT_CONFIG

# Aggregated config — add new games here as you expand the project
GAME_CONFIG = {
    "wuwa": WUWA_CONFIG,
    "zzz": ZZZ_CONFIG,
    "genshinimpact": GENSHINIMPACT_CONFIG,
}

__all__ = [ 
           "GAME_CONFIG", 
           "get_wuwa_events_async", "WUWA_CONFIG", 
           "get_zzz_events_async", "ZZZ_CONFIG", 
           "get_genshinimpact_events_async", "GENSHINIMPACT_CONFIG"
           ]