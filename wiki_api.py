import re
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
import time

class OptimizedWikiAPI:
    
    def __init__(self, API_URL: str):
        self.API_URL = API_URL
    
    async def get_category_members_async(self, category: str, limit: int = 250) -> List[Dict]:
        """Highly optimized version with better batching and concurrent requests"""
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
                    "cmtitle": f"Category:{category}",
                    "cmlimit": str(limit)
                }
                
                async with session.get(self.API_URL, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    members = data.get("query", {}).get("categorymembers", [])
                
                step_end = time.time()
                print(f"[FETCH] Got {len(members)} category members in {round(step_end - step_start, 2)}s")
                
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
        """Fetch content for a single batch of pages"""
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
        """Parse datetime from various wiki formats"""
        if not date_str or date_str.strip().lower() in ['none', '', 'null', 'n/a']:
            return None
        
        date_str = date_str.strip()
        
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M", 
            "%Y-%m-%d",
            "%Y/%m/%d"
        ]
        
        for format in formats:
            try:
                return datetime.strptime(date_str, format)
            except ValueError:
                continue
        
        return None
    
    def get_clean_event_name(self, content: str, title: str) -> str:
        """Get a clean event name for display"""
        name_match = re.search(r'\|\s*name\s*=\s*([^\n|]+)', content)
        if name_match:
            name = name_match.group(1).strip()
            if name and name != title:
                return name
        
        clean_title = re.sub(r'/\d{4}-\d{2}-\d{2}$', '', title)
        clean_title = re.sub(r'\s*\d{4}-\d{2}-\d{2}$', '', clean_title)
        
        return clean_title
    
    def get_time_remaining(self, end_date: datetime) -> str:
        """Calculate time remaining in a readable format"""
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
        """Parse start and end dates from wiki content"""
        start_match = re.search(r'\|\s*time_start\s*=\s*([^\n|]+)', text)
        end_match = re.search(r'\|\s*time_end\s*=\s*([^\n|]+)', text)
        
        start_date = None
        end_date = None
        
        if start_match:
            start_str = start_match.group(1).strip()
            start_date = self.parse_datetime_from_wiki_format(start_str)
        
        if end_match:
            end_str = end_match.group(1).strip()
            end_date = self.parse_datetime_from_wiki_format(end_str)
        
        if start_date and end_date:
            return (start_date, end_date)
        
        if start_date and (not end_match or end_match.group(1).strip().lower() == 'none'):
            return (start_date, datetime(2030, 12, 31))
        
        return None
    
    async def process_event_async(self, event_data: Dict, today: datetime, debug: bool = False) -> Optional[Dict]:
        """Process a single event asynchronously"""
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
        """Get all ongoing events asynchronously with detailed timing"""
        if today is None:
            today = datetime.now(timezone.utc)
        
        total_start = time.time()
        if debug:
            print(f"[START] Looking for events on date: {today}")
        
        # Get events with content using async HTTP
        fetch_start = time.time()
        events_with_content = await self.get_category_members_async("Events")
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
        current_events.sort(key=lambda x: x['end_date'] if x['end_date'].year != 2030 else datetime.max)
        
        total_end = time.time()
        if debug:
            print(f"[PROCESS] Processed events in {round(process_end - process_start, 2)}s")
            print(f"[RESULT] Found {len(current_events)} ongoing events")
            print(f"[TOTAL] Complete operation took {round(total_end - total_start, 2)}s")
        
        return current_events

# Convenience function for easy usage
async def get_ongoing_events_async(API_URL: str, debug: bool = False) -> List[Dict]:
    """Convenience function - creates instance and calls async method"""
    wiki = OptimizedWikiAPI(API_URL)
    return await wiki.get_ongoing_events_async(debug=debug)