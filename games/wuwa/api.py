from typing import List, Dict
from api.wiki_api import get_ongoing_events_async
from .config import WUWA_CONFIG


async def get_wuwa_events_async(debug: bool = False) -> List[Dict]:
    return await get_ongoing_events_async(
        WUWA_CONFIG["api_url"], debug=debug, category=WUWA_CONFIG["category"]
    )