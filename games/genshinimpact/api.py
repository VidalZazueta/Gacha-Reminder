from typing import List, Dict
from api.wiki_api import get_ongoing_events_async
from .config import GENSHINIMPACT_CONFIG

async def get_genshinimpact_events_async(debug: bool = False) -> List[Dict]:
    return await get_ongoing_events_async(
        GENSHINIMPACT_CONFIG["api_url"], debug=debug, category=GENSHINIMPACT_CONFIG["category"]
    )
    
# URL that is queried
# https://genshin-impact.fandom.com/api.php?action=query&format=json&list=categorymembers&cmtitle=Category:In-Game_Events&cmlimit=500