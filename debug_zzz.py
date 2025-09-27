import requests
import json
from datetime import datetime

# ZZZ API URL
API_URL_ZZZ = "https://zenless-zone-zero.fandom.com/api.php"

def test_zzz_events():
    """Debug function to see what's actually in the ZZZ wiki"""
    
    print("=== TESTING ZZZ EVENTS DEBUG ===\n")
    
    # First, let's see what's in the In-Game_Events category
    print("1. Fetching category members from 'In-Game_Events'...")
    
    params = {
        "action": "query",
        "format": "json",
        "list": "categorymembers",
        "cmtitle": "Category:In-Game_Events",
        "cmlimit": "50"
    }
    
    try:
        response = requests.get(API_URL_ZZZ, params=params)
        response.raise_for_status()
        data = response.json()
        
        members = data.get("query", {}).get("categorymembers", [])
        print(f"Found {len(members)} category members:")
        
        for i, member in enumerate(members[:10], 1):  # Show first 10
            print(f"  {i}. {member['title']}")
        
        if len(members) > 10:
            print(f"  ... and {len(members) - 10} more")
            
        if not members:
            print("❌ No members found in Category:In-Game_Events")
            
            # Let's try some alternative category names
            alternative_cats = [
                "Events", 
                "Event", 
                "Game_Events",
                "Activities",
                "Limited_Events"
            ]
            
            print("\n2. Trying alternative category names...")
            for cat_name in alternative_cats:
                print(f"\nTrying Category:{cat_name}...")
                alt_params = {
                    "action": "query",
                    "format": "json", 
                    "list": "categorymembers",
                    "cmtitle": f"Category:{cat_name}",
                    "cmlimit": "20"
                }
                
                try:
                    alt_response = requests.get(API_URL_ZZZ, params=alt_params)
                    alt_data = alt_response.json()
                    alt_members = alt_data.get("query", {}).get("categorymembers", [])
                    
                    if alt_members:
                        print(f"  ✅ Found {len(alt_members)} members in Category:{cat_name}")
                        for member in alt_members[:5]:
                            print(f"    - {member['title']}")
                    else:
                        print(f"  ❌ No members in Category:{cat_name}")
                        
                except Exception as e:
                    print(f"  ❌ Error checking Category:{cat_name}: {e}")
            
            return
        
        # Now let's examine the content of a few events
        print(f"\n3. Examining content of first few events...")
        
        test_events = members[:3]  # Test first 3 events
        
        for event in test_events:
            print(f"\n--- Examining: {event['title']} ---")
            
            # Get page content
            content_params = {
                "action": "query",
                "format": "json",
                "prop": "revisions",
                "titles": event['title'],
                "rvprop": "content",
                "rvslots": "main"
            }
            
            try:
                content_response = requests.get(API_URL_ZZZ, params=content_params)
                content_data = content_response.json()
                
                pages = content_data.get("query", {}).get("pages", {})
                page_data = list(pages.values())[0]
                
                revisions = page_data.get("revisions", [])
                if revisions:
                    slots = revisions[0].get("slots", {})
                    main_slot = slots.get("main", {})
                    content = main_slot.get("*", "")
                    
                    if content:
                        print(f"Content length: {len(content)} characters")
                        print("First 500 characters:")
                        print(content[:500])
                        print("\n" + "."*50)
                        
                        # Look for date-related patterns
                        import re
                        
                        # Look for various date patterns
                        date_patterns = [
                            r'\|\s*time_start\s*=\s*([^\n|]+)',
                            r'\|\s*time_end\s*=\s*([^\n|]+)',
                            r'\|\s*start\s*=\s*([^\n|]+)',
                            r'\|\s*end\s*=\s*([^\n|]+)',
                            r'\|\s*date_start\s*=\s*([^\n|]+)',
                            r'\|\s*date_end\s*=\s*([^\n|]+)',
                            r'\|\s*start_date\s*=\s*([^\n|]+)',
                            r'\|\s*end_date\s*=\s*([^\n|]+)',
                            r'\|\s*duration\s*=\s*([^\n|]+)',
                            r'(20\d{2}[-/]\d{1,2}[-/]\d{1,2})',  # YYYY-MM-DD or YYYY/MM/DD
                        ]
                        
                        print("Looking for date patterns:")
                        found_dates = False
                        
                        for pattern in date_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            if matches:
                                found_dates = True
                                print(f"  Pattern '{pattern}': {matches}")
                        
                        if not found_dates:
                            print("  ❌ No recognizable date patterns found")
                            
                        # Look for template usage
                        template_matches = re.findall(r'\{\{([^}]+)\}\}', content)
                        if template_matches:
                            print(f"\nTemplates used: {template_matches[:5]}")  # Show first 5
                            
                    else:
                        print("❌ No content found")
                else:
                    print("❌ No revisions found")
                    
            except Exception as e:
                print(f"❌ Error fetching content: {e}")
                
    except Exception as e:
        print(f"❌ Error fetching category members: {e}")

if __name__ == "__main__":
    test_zzz_events()