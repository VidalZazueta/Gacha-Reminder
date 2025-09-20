import requests
import re
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import json

class OptimizedWikiAPI:
    
    def __init__(self, API_URL: str):
        self.API_URL = API_URL
        self.session = requests.Session()  # Reuse connections
    
    def get_category_members_with_content(self, category: str, limit: int = 250) -> List[Dict]:
        """Get category members with their content in batches to avoid URL limits"""
        
        # Get all page titles first
        parameters = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": str(limit)
        }
        
        try:
            response = self.session.get(self.API_URL, params=parameters)
            response.raise_for_status()
            data = response.json()
            members = data.get("query", {}).get("categorymembers", [])
            
            print(f"Found {len(members)} total members in category")
            
            if not members:
                return []
            
            # Process in batches of 50 to avoid URL length limits
            batch_size = 50
            all_results = []
            
            for i in range(0, len(members), batch_size):
                batch = members[i:i + batch_size]
                titles = "|".join([member["title"] for member in batch])
                
                print(f"Processing batch {i//batch_size + 1}: {len(batch)} pages")
                
                content_params = {
                    "action": "query",
                    "format": "json",
                    "prop": "revisions",
                    "titles": titles,
                    "rvprop": "content",
                    "rvslots": "main"
                }
                
                content_response = self.session.get(self.API_URL, params=content_params)
                content_response.raise_for_status()
                content_data = content_response.json()
                
                pages = content_data.get("query", {}).get("pages", {})
                print(f"Retrieved content for {len(pages)} pages in this batch")
                
                # Combine title info with content for this batch
                for member in batch:
                    title = member["title"]
                    content_found = False
                    
                    # Find matching page content
                    for page_id, page_data in pages.items():
                        if page_data.get("title") == title:
                            content = ""
                            revisions = page_data.get("revisions", [])
                            if revisions:
                                slots = revisions[0].get("slots", {})
                                main_slot = slots.get("main", {})
                                content = main_slot.get("*", "")
                            
                            all_results.append({
                                "title": title,
                                "content": content
                            })
                            content_found = True
                            break
                    
                    if not content_found:
                        print(f"No content found for: {title}")
                        # Still add it with empty content for debugging
                        all_results.append({
                            "title": title,
                            "content": ""
                        })
            
            print(f"Total results with content: {len(all_results)}")
            return all_results
            
        except requests.RequestException as e:
            print(f"Error getting category members with content: {e}")
            return []
    
    async def get_category_members_async(self, category: str, limit: int = 250) -> List[Dict]:
        """Async version for even better performance"""
        
        async with aiohttp.ClientSession() as session:
            # Get category members
            params = {
                "action": "query",
                "format": "json",
                "list": "categorymembers",
                "cmtitle": f"Category:{category}",
                "cmlimit": str(limit)
            }
            
            try:
                async with session.get(self.API_URL, params=params) as response:
                    data = await response.json()
                    members = data.get("query", {}).get("categorymembers", [])
                    
                    if not members:
                        return []
                    
                    # Batch get content for all pages
                    titles = "|".join([member["title"] for member in members])
                    
                    content_params = {
                        "action": "query",
                        "format": "json",
                        "prop": "revisions",
                        "titles": titles,
                        "rvprop": "content",
                        "rvslots": "main"
                    }
                    
                    async with session.get(self.API_URL, params=content_params) as content_response:
                        content_data = await content_response.json()
                        pages = content_data.get("query", {}).get("pages", {})
                        
                        # Combine data
                        result = []
                        for member in members:
                            title = member["title"]
                            for page_id, page_data in pages.items():
                                if page_data.get("title") == title:
                                    content = ""
                                    revisions = page_data.get("revisions", [])
                                    if revisions:
                                        slots = revisions[0].get("slots", {})
                                        main_slot = slots.get("main", {})
                                        content = main_slot.get("*", "")
                                    
                                    result.append({
                                        "title": title,
                                        "content": content
                                    })
                                    break
                        
                        return result
                        
            except Exception as e:
                print(f"Error in async request: {e}")
                return []
    
    def parse_datetime_from_wiki_format(self, date_str: str) -> Optional[datetime]:
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
    
    def process_event_fast(self, event_data: Dict, today: datetime, debug: bool = False) -> Optional[Dict]:
        """Process a single event quickly"""
        try:
            title = event_data["title"]
            content = event_data["content"]
            
            if debug:
                print(f"Processing: {title}")
                print(f"Content length: {len(content)}")
            
            if not content:
                if debug:
                    print(f"No content for {title}")
                return None
            
            date_info = self.parse_event_dates(content, title)
            if not date_info:
                if debug:
                    print(f"No valid dates found for {title}")
                    # Show some content for debugging
                    content_preview = content[:200].replace('\n', ' ')
                    print(f"Content preview: {content_preview}")
                return None
            
            start_date, end_date = date_info
            
            if debug:
                print(f"Dates: {start_date} to {end_date}")
            
            # Check if event is ongoing
            today_aware = today.replace(tzinfo=timezone.utc) if today.tzinfo is None else today
            start_aware = start_date.replace(tzinfo=timezone.utc) if start_date.tzinfo is None else start_date
            end_aware = end_date.replace(tzinfo=timezone.utc) if end_date.tzinfo is None else end_date
            
            is_ongoing = start_aware.date() <= today_aware.date() <= end_aware.date()
            
            if debug:
                print(f"Is ongoing: {is_ongoing} (today: {today_aware.date()})")
            
            if is_ongoing:
                clean_name = self.get_clean_event_name(content, title)
                time_remaining = self.get_time_remaining(end_date)
                
                return {
                    "title": clean_name,
                    "time_remaining": time_remaining,
                    "start_date": start_date,
                    "end_date": end_date,
                    "date_range_str": f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d') if end_date.year != 2030 else 'Permanent'}"
                }
        except Exception as e:
            if debug:
                print(f"Error processing event {event_data.get('title', 'unknown')}: {e}")
            
        return None
    
    def get_ongoing_events_fast(self, today: Optional[datetime] = None, debug: bool = False) -> List[Dict]:
        """Faster version using batched requests and parallel processing"""
        if today is None:
            today = datetime.now(timezone.utc)
        
        if debug:
            print(f"Looking for events on date: {today}")
        
        # Get all events with their content in batches
        events_with_content = self.get_category_members_with_content("Events")
        if not events_with_content:
            if debug:
                print("No events with content found")
            return []
        
        if debug:
            print(f"Processing {len(events_with_content)} events...")
        
        # Process events in parallel using ThreadPoolExecutor
        current_events = []
        processed_count = 0
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all processing tasks
            futures = [
                executor.submit(self.process_event_fast, event_data, today, debug) 
                for event_data in events_with_content
            ]
            
            # Collect results
            for future in futures:
                result = future.result()
                processed_count += 1
                if result:
                    current_events.append(result)
                    if debug:
                        print(f"Found ongoing event: {result['title']}")
        
        if debug:
            print(f"Processed {processed_count} events, found {len(current_events)} ongoing")
        
        # Sort by end date
        current_events.sort(key=lambda x: x['end_date'] if x['end_date'].year != 2030 else datetime.max)
        
        return current_events
    
    async def get_ongoing_events_async(self, today: Optional[datetime] = None) -> List[Dict]:
        """Async version for maximum speed"""
        if today is None:
            today = datetime.now(timezone.utc)
        
        events_with_content = await self.get_category_members_async("Events")
        if not events_with_content:
            return []
        
        # Process events
        current_events = []
        for event_data in events_with_content:
            result = self.process_event_fast(event_data, today)
            if result:
                current_events.append(result)
        
        current_events.sort(key=lambda x: x['end_date'] if x['end_date'].year != 2030 else datetime.max)
        return current_events

# Convenience functions
def get_ongoing_events_fast(API_URL: str, debug: bool = False) -> List[Dict]:
    """Fast synchronous version"""
    wiki = OptimizedWikiAPI(API_URL)
    return wiki.get_ongoing_events_fast(debug=debug)

async def get_ongoing_events_async(API_URL: str) -> List[Dict]:
    """Async version for maximum performance"""
    wiki = OptimizedWikiAPI(API_URL)
    return await wiki.get_ongoing_events_async()