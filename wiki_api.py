import requests
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple

class WikiAPI:
    
    def __init__(self, API_URL: str):
        self.API_URL = API_URL
    
    # Note: Limit should be at 500 to get more events shown in the bot, but does take longer
    def get_category_members(self, category: str, limit: int = 500) -> List[Dict]:
        parameters = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": str(limit)
        }

        try:
            response = requests.get(self.API_URL, params=parameters)
            response.raise_for_status()
            data = response.json()
            
            return data.get("query", {}).get("categorymembers", [])
        except requests.RequestException as e:
            print(f"Error getting category members: {e}")
            return []
    
    def get_page_content(self, title: str) -> str:
        parameters = {
            "action": "query",
            "format": "json",
            "prop": "revisions",
            "titles": title,
            "rvprop": "content",
            "rvslots": "main"
        }
        
        try:
            response = requests.get(self.API_URL, params=parameters)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get("query", {}).get("pages", {})
            if pages:
                page_data = list(pages.values())[0]
                revisions = page_data.get("revisions", [])
                if revisions:
                    slots = revisions[0].get("slots", {})
                    main_slot = slots.get("main", {})
                    return main_slot.get("*", "")
                    
        except Exception as e:
            print(f"Error getting page content for {title}: {e}")
        
        return ""
    
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
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def get_clean_event_name(self, content: str, title: str) -> str:
        """Get a clean event name for display"""
        # Try to get the name from the wiki template
        name_match = re.search(r'\|\s*name\s*=\s*([^\n|]+)', content)
        if name_match:
            name = name_match.group(1).strip()
            if name and name != title:
                return name
        
        # Otherwise clean up the title
        clean_title = re.sub(r'/\d{4}-\d{2}-\d{2}$', '', title)
        clean_title = re.sub(r'\s*\d{4}-\d{2}-\d{2}$', '', clean_title)
        
        return clean_title
    
    def get_time_remaining(self, end_date: datetime) -> str:
        """Calculate time remaining in a readable format"""
        if end_date.year == 2030:  # Permanent event
            return "Permanent"
        
        # Make sure both datetimes are timezone-aware for comparison
        now = datetime.now(timezone.utc)
        
        # If end_date is naive (no timezone), assume it's UTC
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        time_diff = end_date - now
        
        if time_diff.total_seconds() <= 0:
            return "Ended"
        
        days = time_diff.days
        hours = time_diff.seconds // 3600
        
        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            minutes = (time_diff.seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            minutes = time_diff.seconds // 60
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
    
    def get_ongoing_events(self, today: Optional[datetime] = None) -> List[Dict]:
        if today is None:
            today = datetime.now(timezone.utc)
            
        events = self.get_category_members("Events")
        if not events:
            return []
        
        current_events = []
        
        for event in events:
            title = event["title"]
            
            try:
                content = self.get_page_content(title)
                if not content:
                    continue
                
                date_info = self.parse_event_dates(content, title)
                if not date_info:
                    continue
                
                start_date, end_date = date_info
                
                # Check if event is ongoing (make sure all dates are timezone-aware for comparison)
                today_aware = today.replace(tzinfo=timezone.utc) if today.tzinfo is None else today
                start_aware = start_date.replace(tzinfo=timezone.utc) if start_date.tzinfo is None else start_date
                end_aware = end_date.replace(tzinfo=timezone.utc) if end_date.tzinfo is None else end_date
                
                if start_aware.date() <= today_aware.date() <= end_aware.date():
                    clean_name = self.get_clean_event_name(content, title)
                    time_remaining = self.get_time_remaining(end_date)
                    
                    current_events.append({
                        "title": clean_name,
                        "time_remaining": time_remaining,
                        "start_date": start_date,
                        "end_date": end_date,
                        "date_range_str": f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d') if end_date.year != 2030 else 'Permanent'}"
                    })
            
            except Exception as e:
                print(f"Error processing event {title}: {e}")
                continue
        
        # Sort by end date (soonest ending first)
        current_events.sort(key=lambda x: x['end_date'] if x['end_date'].year != 2030 else datetime.max)
        
        return current_events

def get_ongoing_events_from_wiki(API_URL: str) -> List[Dict]:
    wiki = WikiAPI(API_URL)
    return wiki.get_ongoing_events()