from typing import List, Dict
from api.wiki_api import get_ongoing_events_async
from .config import ZZZ_CONFIG


async def get_zzz_events_async(debug: bool = False) -> List[Dict]:
    return await get_ongoing_events_async(
        ZZZ_CONFIG["api_url"], debug=debug, category=ZZZ_CONFIG["category"]
    )