import requests
import re
from datetime import datetime, timezone, timedelta

API_URL = "https://wutheringwaves.fandom.com/api.php"

def parse_datetime_from_wiki_format(date_str: str):
    """Parse datetime from various wiki template formats"""
    if not date_str or date_str.strip().lower() in ['none', '', 'null', 'n/a']:
        return None
        
    date_str = date_str.strip()
    
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

def parse_event_dates(text: str, title: str = ""):
    """Parse event dates from wiki template format"""
    
    print(f"Parsing dates for: {title}")
    
    # Extract time_start and time_end from wiki template
    start_match = re.search(r'\|\s*time_start\s*=\s*([^\n|]+)', text)
    end_match = re.search(r'\|\s*time_end\s*=\s*([^\n|]+)', text)
    
    print(f"Start match: {start_match.group(1).strip() if start_match else 'None'}")
    print(f"End match: {end_match.group(1).strip() if end_match else 'None'}")
    
    start_date = None
    end_date = None
    
    if start_match:
        start_str = start_match.group(1).strip()
        start_date = parse_datetime_from_wiki_format(start_str)
        print(f"Parsed start date: {start_date}")
    
    if end_match:
        end_str = end_match.group(1).strip()
        end_date = parse_datetime_from_wiki_format(end_str)
        print(f"Parsed end date: {end_date}")
    
    # If we have both dates, return them
    if start_date and end_date:
        print(f"✓ Found date range: {start_date.date()} to {end_date.date()}")
        return (start_date, end_date)
    
    # If we only have start date and end is "none", check for permanent events
    if start_date and (not end_match or end_match.group(1).strip().lower() == 'none'):
        print(f"✓ Permanent event starting: {start_date.date()}")
        return (start_date, datetime(2030, 12, 31))  # Far future date
    
    print("✗ No valid date range found")
    return None

# Test with some sample events that should be ongoing
test_events = [
    "Bountiful Crescendo/2025-09-11",  # Should be ongoing since it runs until 2025-09-18
]

for event_title in test_events:
    print(f"\n=== Testing {event_title} ===")
    
    # Get page content
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": event_title,
        "rvprop": "content",
        "rvslots": "main"
    }
    
    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        pages = data.get("query", {}).get("pages", {})
        if pages:
            page_data = list(pages.values())[0]
            revisions = page_data.get("revisions", [])
            if revisions:
                slots = revisions[0].get("slots", {})
                main_slot = slots.get("main", {})
                content = main_slot.get("*", "")
                
                if content:
                    print(f"Content length: {len(content)} characters")
                    print(f"First 500 chars:\n{content[:500]}...")
                    
                    # Parse dates
                    date_result = parse_event_dates(content, event_title)
                    
                    if date_result:
                        start_date, end_date = date_result
                        today = datetime(2025, 9, 18)  # Test date
                        is_ongoing = start_date.date() <= today.date() <= end_date.date()
                        
                        print(f"Is ongoing on {today.date()}: {is_ongoing}")
                        if is_ongoing:
                            print("🎉 This event should show up as ongoing!")
                        else:
                            print("❌ This event will not show as ongoing")
                    else:
                        print("❌ Failed to parse dates")
                else:
                    print("❌ No content found")
        else:
            print("❌ No pages found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "="*50)
print("If the Bountiful Crescendo/2025-09-11 event shows as ongoing,")
print("then the fix is working correctly!")