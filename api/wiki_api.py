"""
MediaWiki API client and event-processing logic for the Gacha Reminder bot.

Provides the :class:`WikiAPI` class for fetching page content from any
MediaWiki-based wiki using the MediaWiki Action API, plus parsing
utilities for extracting and normalizing event start/end dates from
wikitext templates.

Module-level convenience functions wrap :class:`WikiAPI` for the two
supported games:

* :func:`get_wuwa_events_async` – Wuthering Waves
* :func:`get_zzz_events_async`  – Zenless Zone Zero
"""
import re
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
import time

class WikiAPI:
    """Async client for fetching and parsing game events from a MediaWiki wiki.

    Uses the MediaWiki Action API (``api.php``) to list a category's
    member pages and retrieve their wikitext content in batches. Parsed
    events are filtered to only those currently ongoing and returned
    sorted by end date.

    Attributes:
        API_URL (str): The ``api.php`` endpoint for the target wiki.
        category_name (str): Default wiki category to query for events.
    """

    def __init__(self, API_URL: str, category_name: str = "Events"):
        """Initialize the WikiAPI client.

        Args:
            API_URL (str): Full URL to the wiki's ``api.php`` endpoint
                (e.g. ``"https://wutheringwaves.fandom.com/api.php"``).
            category_name (str): Wiki category to query for event pages.
                Defaults to ``"Events"``.
        """
        self.API_URL = API_URL
        self.category_name = category_name
    
    async def get_category_members_async(self, category: Optional[str] = None, limit: int = 250) -> List[Dict]:
        """Fetch all members of a wiki category along with their wikitext content.

        Uses concurrent batch requests (batch size 20) to minimize total
        round-trip time. Each batch is fetched in parallel via
        :func:`asyncio.gather`.

        Args:
            category (Optional[str]): Category name to query. Falls back
                to :attr:`category_name` when ``None``.
            limit (int): Maximum number of category members to retrieve
                from the API (default ``250``).

        Returns:
            List[Dict]: List of dicts with keys:

            * ``"title"`` (str) – page title.
            * ``"content"`` (str) – raw wikitext of the page's main slot.

            Returns an empty list on any fatal network or API error.
        """
        # Use provided category or fall back to instance default
        category_to_use = category or self.category_name
        
        # Longer timeout and connection pooling
        timeout = aiohttp.ClientTimeout(total=60, connect=10)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            try:
                step_start = time.time()
                
                # Get category members
                params = {
                    "action": "query",
                    "format": "json",
                    "list": "categorymembers",
                    "cmtitle": f"Category:{category_to_use}",
                    "cmlimit": str(limit)
                }
                
                async with session.get(self.API_URL, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    members = data.get("query", {}).get("categorymembers", [])
                
                step_end = time.time()
                print(f"[FETCH] Got {len(members)} category members from '{category_to_use}' in {round(step_end - step_start, 2)}s")
                
                if not members:
                    return []
                
                # More aggressive batching - process multiple batches concurrently
                batch_size = 20  # Smaller batches for better parallelization
                all_results = []
                
                # Create tasks for all batches
                batch_tasks = []
                for i in range(0, len(members), batch_size):
                    batch = members[i:i + batch_size]
                    task = self._fetch_batch_content(session, batch)
                    batch_tasks.append(task)
                
                print(f"[FETCH] Created {len(batch_tasks)} batch tasks")
                
                # Execute all batches concurrently
                concurrent_start = time.time()
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                concurrent_end = time.time()
                
                print(f"[FETCH] Concurrent batches completed in {round(concurrent_end - concurrent_start, 2)}s")
                
                # Combine all results
                for result in batch_results:
                    if isinstance(result, list):
                        all_results.extend(result)
                    elif isinstance(result, Exception):
                        print(f"[ERROR] Batch failed: {result}")
                
                print(f"[FETCH] Total results with content: {len(all_results)}")
                return all_results
                    
            except Exception as e:
                print(f"[ERROR] Fatal error in get_category_members_async: {e}")
                return []
    
    async def _fetch_batch_content(self, session: aiohttp.ClientSession, batch: List[Dict]) -> List[Dict]:
        """Fetch wikitext content for a single batch of pages in one API call.

        Joins page titles with ``|`` to perform a multi-page ``revisions``
        query, then maps the results back to the original member order.

        Args:
            session (aiohttp.ClientSession): An open aiohttp session to
                reuse for the request.
            batch (List[Dict]): A subset of category-member dicts, each
                containing at least a ``"title"`` key.

        Returns:
            List[Dict]: Dicts with ``"title"`` and ``"content"`` for each
            page in the batch that was found. Pages with no revisions get
            an empty string for ``"content"``. Returns ``[]`` on error.
        """
        try:
            titles = "|".join([member["title"] for member in batch])
            
            content_params = {
                "action": "query",
                "format": "json",
                "prop": "revisions",
                "titles": titles,
                "rvprop": "content",
                "rvslots": "main"
            }
            
            async with session.get(self.API_URL, params=content_params) as content_response:
                content_response.raise_for_status()
                content_data = await content_response.json()
                pages = content_data.get("query", {}).get("pages", {})
                
                # Process results for this batch
                batch_results = []
                for member in batch:
                    title = member["title"]
                    for page_id, page_data in pages.items():
                        if page_data.get("title") == title:
                            content = ""
                            revisions = page_data.get("revisions", [])
                            if revisions:
                                slots = revisions[0].get("slots", {})
                                main_slot = slots.get("main", {})
                                content = main_slot.get("*", "")
                            
                            batch_results.append({
                                "title": title,
                                "content": content
                            })
                            break
                
                return batch_results
                
        except Exception as e:
            print(f"[ERROR] Batch content fetch failed: {e}")
            return []
    
    def parse_datetime_from_wiki_format(self, date_str: str) -> Optional[datetime]:
        """Parse a datetime from one of several wiki date string formats.

        Tries each supported format in order from most specific to least
        specific. The returned datetime is **naive** (no timezone info).

        Supported formats (in priority order):

        * ``YYYY-MM-DD HH:MM:SS`` — e.g. ``"2024-11-16 10:00:00"`` (ZZZ)
        * ``YYYY-MM-DD HH:MM``    — e.g. ``"2024-11-16 10:00"``
        * ``YYYY/MM/DD HH:MM:SS`` — slash variant with time
        * ``YYYY/MM/DD HH:MM``    — slash variant with time (short)
        * ``YYYY-MM-DD``          — date only
        * ``YYYY/MM/DD``          — date only, slash variant
        * ``Month DD, YYYY``      — e.g. ``"November 16, 2024"``
        * ``Mon DD, YYYY``        — e.g. ``"Nov 16, 2024"``

        Args:
            date_str (str): Raw date string extracted from wiki content.

        Returns:
            Optional[datetime]: Parsed naive datetime, or ``None`` if the
            string is empty, ``"none"``/``"null"``/``"n/a"``, or does not
            match any known format.
        """
        if not date_str or date_str.strip().lower() in ['none', '', 'null', 'n/a']:
            return None
        
        date_str = date_str.strip()
        
        # Enhanced formats including seconds - try most specific first
        formats = [
            "%Y-%m-%d %H:%M:%S",  # 2024-11-16 10:00:00 (ZZZ format) 
            "%Y-%m-%d %H:%M",     # 2024-11-16 10:00
            "%Y/%m/%d %H:%M:%S",  # Alternative with slashes
            "%Y/%m/%d %H:%M", 
            "%Y-%m-%d",           # Date only
            "%Y/%m/%d",           # Date only with slashes
            "%B %d, %Y",          # November 16, 2024
            "%b %d, %Y"           # Nov 16, 2024
        ]
        
        for format_str in formats:
            try:
                parsed_date = datetime.strptime(date_str, format_str)
                return parsed_date
            except ValueError:
                continue
        
        # If no format worked, let's log what we tried to parse
        print(f"[DEBUG] Failed to parse date: '{date_str}' with any known format")
        return None
    
    def get_clean_event_name(self, content: str, title: str) -> str:
        """Extract a clean display name for an event from its wikitext.

        Attempts to read the ``| name = `` field from the wikitext
        template. If that field is absent or identical to the page title,
        falls back to the title with any trailing date suffix (e.g.
        ``/2024-11-16`` or `` 2024-11-16``) stripped.

        Args:
            content (str): Raw wikitext of the event page.
            title (str): Fallback page title used when no ``name`` field
                is found.

        Returns:
            str: Human-readable event name suitable for embed display.
        """
        name_match = re.search(r'\|\s*name\s*=\s*([^\n|]+)', content)
        if name_match:
            name = name_match.group(1).strip()
            if name and name != title:
                return name
        
        clean_title = re.sub(r'/\d{4}-\d{2}-\d{2}$', '', title)
        clean_title = re.sub(r'\s*\d{4}-\d{2}-\d{2}$', '', clean_title)
        
        return clean_title
    
    def get_time_remaining(self, end_date: datetime) -> str:
        """Calculate human-readable time remaining until an event ends.

        Treats any end date in the year ``2030`` as a sentinel for a
        permanent/indefinite event.

        Args:
            end_date (datetime): The event's end datetime. May be naive
                (assumed UTC) or timezone-aware.

        Returns:
            str: One of the following formats:

            * ``"Permanent"`` — end year is 2030.
            * ``"Ended"``     — the end date has already passed.
            * ``"Xd Yh"``    — days and hours remaining.
            * ``"Xh Ym"``    — hours and minutes remaining (< 1 day).
            * ``"Xm"``       — minutes remaining (< 1 hour).
        """
        if end_date.year == 2030: 
            return "Permanent"
        
        now = datetime.now(timezone.utc)
        
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        time_difference = end_date - now
        
        if time_difference.total_seconds() <= 0:
            return "Ended"
        
        days = time_difference.days
        hours = time_difference.seconds // 3600
        
        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            minutes = (time_difference.seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            minutes = time_difference.seconds // 60
            return f"{minutes}m"
    
    def parse_event_dates(self, text: str, title: str = "") -> Optional[Tuple[datetime, datetime]]:
        """Extract and normalize start/end datetimes from a wiki event page.

        Reads ``| time_start =``, ``| time_end =``, and optionally
        ``| time_start_offset =`` fields from the wikitext. When a
        ``GMT+8`` / ``UTC+8`` offset is found, both dates are shifted
        back by 8 hours to convert to UTC.

        If ``time_end`` is absent or explicitly ``"none"``, the end date
        is set to ``datetime(2030, 12, 31)`` which
        :meth:`get_time_remaining` treats as permanent.

        Args:
            text (str): Raw wikitext of the event page.
            title (str): Page title used for debug logging (default ``""``).

        Returns:
            Optional[Tuple[datetime, datetime]]: A ``(start, end)`` tuple
            of naive datetimes (already offset-adjusted), or ``None`` if
            no valid ``time_start`` could be parsed.
        """
        start_match = re.search(r'\|\s*time_start\s*=\s*([^\n|]+)', text)
        end_match = re.search(r'\|\s*time_end\s*=\s*([^\n|]+)', text)
        
        # Also look for timezone offset (ZZZ format) - but it's optional
        offset_match = re.search(r'\|\s*time_start_offset\s*=\s*([^\n|]+)', text)
        
        start_date = None
        end_date = None
        
        if start_match:
            start_str = start_match.group(1).strip()
            start_date = self.parse_datetime_from_wiki_format(start_str)
            
            # Apply timezone offset ONLY if both date parsing succeeded AND offset exists
            if start_date and offset_match:
                offset_str = offset_match.group(1).strip()
                if "GMT+8" in offset_str or "UTC+8" in offset_str:
                    # Convert from GMT+8 to UTC by subtracting 8 hours
                    start_date = start_date - timedelta(hours=8)
                elif "GMT-" in offset_str or "UTC-" in offset_str:
                    # Handle negative offsets if needed
                    pass  # Add handling for other timezones as needed
            # If no offset_match, leave the date as-is (assume it's already in the correct timezone)
        
        if end_match:
            end_str = end_match.group(1).strip()
            end_date = self.parse_datetime_from_wiki_format(end_str)
            
            # Apply same timezone offset to end date ONLY if offset exists
            if end_date and offset_match:
                offset_str = offset_match.group(1).strip()
                if "GMT+8" in offset_str or "UTC+8" in offset_str:
                    end_date = end_date - timedelta(hours=8)
            # If no offset_match, leave the date as-is
        
        if start_date and end_date:
            return (start_date, end_date)
        
        if start_date and (not end_match or end_match.group(1).strip().lower() == 'none'):
            return (start_date, datetime(2030, 12, 31))
        
        return None
    
    async def process_event_async(self, event_data: Dict, today: datetime, debug: bool = False) -> Optional[Dict]:
        """Process a single raw event dict into a display-ready event dict.

        Parses dates via :meth:`parse_event_dates`, checks whether the
        event is currently ongoing, and assembles the result dict used by
        embed builders.

        Args:
            event_data (Dict): A dict with ``"title"`` and ``"content"``
                keys as returned by :meth:`get_category_members_async`.
            today (datetime): Reference datetime for the "is ongoing"
                check. May be naive (assumed UTC) or timezone-aware.
            debug (bool): When ``True``, prints processing steps to
                stdout (default ``False``).

        Returns:
            Optional[Dict]: A dict with the following keys if the event
            is currently ongoing, otherwise ``None``:

            * ``"title"`` (str)          – clean display name.
            * ``"time_remaining"`` (str) – human-readable countdown.
            * ``"start_date"`` (datetime) – parsed start datetime.
            * ``"end_date"`` (datetime)   – parsed end datetime.
            * ``"date_range_str"`` (str)  – e.g. ``"11/16 - 12/01"``.
        """
        try:
            title = event_data["title"]
            content = event_data["content"]
            
            if not content:
                if debug:
                    print(f"[PROCESS] No content for {title}")
                return None
            
            date_info = self.parse_event_dates(content, title)
            if not date_info:
                if debug:
                    print(f"[PROCESS] No valid dates found for {title}")
                return None
            
            start_date, end_date = date_info
            
            # Check if event is ongoing
            today_aware = today.replace(tzinfo=timezone.utc) if today.tzinfo is None else today
            start_aware = start_date.replace(tzinfo=timezone.utc) if start_date.tzinfo is None else start_date
            end_aware = end_date.replace(tzinfo=timezone.utc) if end_date.tzinfo is None else end_date
            
            is_ongoing = start_aware.date() <= today_aware.date() <= end_aware.date()
            
            if is_ongoing:
                clean_name = self.get_clean_event_name(content, title)
                time_remaining = self.get_time_remaining(end_date)
                
                if debug:
                    print(f"[PROCESS] Found ongoing event: {clean_name}")
                
                return {
                    "title": clean_name,
                    "time_remaining": time_remaining,
                    "start_date": start_date,
                    "end_date": end_date,
                    "date_range_str": f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d') if end_date.year != 2030 else 'Permanent'}"
                }
        except Exception as e:
            if debug:
                print(f"[ERROR] Error processing event {event_data.get('title', 'unknown')}: {e}")
            
        return None
    
    async def get_ongoing_events_async(self, today: Optional[datetime] = None, debug: bool = False) -> List[Dict]:
        """Fetch, parse, and return all currently ongoing events.

        Orchestrates the full pipeline:

        1. Calls :meth:`get_category_members_async` to retrieve all pages
           in the configured category.
        2. Processes every page concurrently via
           :meth:`process_event_async`.
        3. Filters out non-ongoing events and exceptions.
        4. Sorts remaining events by end date (permanent events last).

        Args:
            today (Optional[datetime]): Reference date for filtering.
                Defaults to :func:`datetime.now` in UTC.
            debug (bool): When ``True``, emits timing and count info to
                stdout throughout the pipeline (default ``False``).

        Returns:
            List[Dict]: Ongoing event dicts sorted by ``end_date``,
            each matching the shape described in
            :meth:`process_event_async`. Returns ``[]`` if the category
            has no members or all events have ended.
        """
        if today is None:
            today = datetime.now(timezone.utc)
        
        total_start = time.time()
        if debug:
            print(f"[START] Looking for events on date: {today}")
        
        # Get events with content using async HTTP
        fetch_start = time.time()
        events_with_content = await self.get_category_members_async()
        fetch_end = time.time()
        
        if debug:
            print(f"[FETCH] Retrieved {len(events_with_content)} events in {round(fetch_end - fetch_start, 2)}s")
        
        if not events_with_content:
            if debug:
                print("[FETCH] No events with content found")
            return []
        
        # Process all events concurrently
        process_start = time.time()
        tasks = [
            self.process_event_async(event_data, today, debug) 
            for event_data in events_with_content
        ]
        
        # Wait for all processing to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        process_end = time.time()
        
        # Filter out None results and exceptions
        current_events = [
            result for result in results 
            if result is not None and not isinstance(result, Exception)
        ]
        
        # Sort by end date
        #! Currently there are errors here but the code still works
        current_events.sort(key=lambda x: x['end_date'] if x['end_date'].year != 2030 else datetime.max) # type: ignore
        
        total_end = time.time()
        if debug:
            print(f"[PROCESS] Processed events in {round(process_end - process_start, 2)}s")
            print(f"[RESULT] Found {len(current_events)} ongoing events")
            print(f"[TOTAL] Complete operation took {round(total_end - total_start, 2)}s")
        
        #! Error here but the code still works
        return current_events # type: ignore

# Modularized functions to use in main

#* There are different functions for each game as the API call is different for each game.
#* Notice how WuWa has the Category "events" while ZZZ has Category "In-Game_Events"

async def get_ongoing_events_async(API_URL: str, debug: bool = False, category: str = "Events") -> List[Dict]:
    """Convenience wrapper that creates a :class:`WikiAPI` and fetches ongoing events.

    Prefer the game-specific helpers (:func:`get_wuwa_events_async`,
    :func:`get_zzz_events_async`) for typical usage; use this function
    when targeting an arbitrary wiki or category.

    Args:
        API_URL (str): Full ``api.php`` URL of the target wiki.
        debug (bool): Forward debug flag to :meth:`WikiAPI.get_ongoing_events_async`
            (default ``False``).
        category (str): Wiki category name to query (default ``"Events"``).

    Returns:
        List[Dict]: Ongoing event dicts; see :meth:`WikiAPI.process_event_async`
        for the dict shape.
    """
    wiki = WikiAPI(API_URL, category)
    return await wiki.get_ongoing_events_async(debug=debug)

# Function to get the events for the game wuthering waves
async def get_wuwa_events_async(debug: bool = False) -> List[Dict]:
    """Fetch currently ongoing events for Wuthering Waves.

    Targets the Wuthering Waves Fandom wiki (``"Events"`` category).

    Args:
        debug (bool): When ``True``, prints timing and parsing details
            to stdout (default ``False``).

    Returns:
        List[Dict]: Ongoing event dicts sorted by end date.
    """
    API_URL_WUWA = "https://wutheringwaves.fandom.com/api.php"
    return await get_ongoing_events_async(API_URL_WUWA, debug=debug, category="Events")

# Function to get the events for the game Zenless Zone Zero
async def get_zzz_events_async(debug: bool = False) -> List[Dict]:
    """Fetch currently ongoing events for Zenless Zone Zero.

    Targets the Zenless Zone Zero Fandom wiki (``"In-Game_Events"``
    category), which uses a different category name than Wuthering Waves.

    Args:
        debug (bool): When ``True``, prints timing and parsing details
            to stdout (default ``False``).

    Returns:
        List[Dict]: Ongoing event dicts sorted by end date.
    """
    API_URL_ZZZ = "https://zenless-zone-zero.fandom.com/api.php"
    return await get_ongoing_events_async(API_URL_ZZZ, debug=debug, category="In-Game_Events")