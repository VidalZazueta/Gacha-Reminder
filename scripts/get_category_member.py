# Python script to get all categories from a wiki

import requests
import json

# Testing variables
fandom = "honkaiimpact3rd"
API_URL = "http://{fandom}.fandom.com/api.php"

session = requests.Session()

# "list": "allcategories" list all categories in the wiki

# Parameters for the API request to get all categories starting with "Events"
PARAMS = {
    "action": "query",
    "format": "json",
    "list": "categorymembers",
    "cmtitle": "Category:Event",
    "cmlimit": 500,

}

request = session.get(url=API_URL.format(fandom=fandom), params=PARAMS)
data = request.json()


CATEGORIES = data["query"]["categorymembers"]

for category in CATEGORIES:
    print(category["title"])