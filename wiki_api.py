# Final fixed wiki_api.py file

import requests
import re
import html
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

class WikiAPI:
    
    def __init__(self, API_URL: str):
        self.API_URL = API_URL
    
    def get_category_members(self, category: str, limit: int = 50) -> List[Dict]:
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
        methods = [
            {
                "action": "query",
                "format": "json",
                "prop": "revisions",
                "titles": title,
                "rvprop": "content",
                "rvslots": "main"
            },
            {
                "action": "parse",
                "format": "json",
                "page": title,
                "prop": "text"
            }
        ]
        
        for params in methods:
            try:
                response = requests.get(self.API_URL, params=params)
                response.raise_for_status()
                data = response.json()
                
                content = ""
                
                if params["action"] == "query":
                    pages = data.get("query", {}).get("pages", {})
                    if pages:
                        page_data = list(pages.values())[0]
                        revisions = page_data.get("revisions", [])
                        if revisions:
                            slots = revisions[0].get("slots", {})
                            main_slot = slots.get("main", {})
                            content = main_slot.get("*", "")
                
                elif params["action"] == "parse":
                    if "parse" in data:
                        content = data["parse"].get("text", {}).get("*", "")
                        content = re.sub(r'<[^>]+>', '', content)
                        content = html.unescape(content)
                
                if content and len(content.strip()) > 0:
                    return content
                    
            except requests.RequestException:
                continue
            except Exception:
                continue
        
        return ""
    
    def parse_datetime_from_wiki_format(self, date_str: str) -> Optional[datetime]:
        """Parse datetime from various wiki template formats"""
        if not date_str or date_str.strip().lower() in ['none', '', 'null', 'n/a']:
            return None
            
        date_str = date_str.strip()
        
        # Common formats used in Wuthering Waves wiki
        formats = [
            "%Y-%m-%d %H:%M",     # 2025-09-11 04:00
            "%Y/%m/%d %H:%M",     # 2024/08/15 13:00
            "%Y-%m-%d",           # 2025-09-11
            "%Y/%m/%d",           # 2024/08/15
            "%B %d, %Y",          # September 11, 2025
            "%b %d, %Y",          # Sep 11, 2025
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def parse_event_dates(self, text: str, title: str = "") -> Optional[Tuple[datetime, datetime]]:
        """Parse event dates from wiki template format"""
        
        # Extract time_start and time_end from wiki template
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
        
        # If we have both dates, return them
        if start_date and end_date:
            return (start_date, end_date)
        
        # If we only have start date and end is "none", check for permanent events
        if start_date and (not end_match or end_match.group(1).strip().lower() == 'none'):
            # For permanent events or events with no end date, consider them ongoing
            return (start_date, datetime(2030, 12, 31))  # Far future date
        
        # Fallback: try to extract dates from title (like "Event/2024-09-16")
        title_date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', title)
        if title_date_match:
            try:
                year, month, day = map(int, title_date_match.groups())
                date_obj = datetime(year, month, day)
                # For title-based dates, assume it's a week-long event
                from datetime import timedelta
                return (date_obj, date_obj + timedelta(days=7))
            except ValueError:
                pass
        
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
            
            content = self.get_page_content(title)
            if not content:
                continue
            
            date_info = self.parse_event_dates(content, title)
            if not date_info:
                continue
            
            start_date, end_date = date_info
            
            # Check if event is ongoing
            if start_date.date() <= today.date() <= end_date.date():
                current_events.append({
                    "title": title,
                    "start_date": start_date,
                    "end_date": end_date,
                    "date_range_str": f"{start_date.strftime('%B %d, %Y')} → {end_date.strftime('%B %d, %Y')}"
                })
        
        return current_events

def get_ongoing_events_from_wiki(API_URL: str) -> List[Dict]:
    wiki = WikiAPI(API_URL)
    return wiki.get_ongoing_events()