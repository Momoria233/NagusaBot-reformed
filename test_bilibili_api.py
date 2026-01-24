# deprecated test

import os
import requests
import json
from dotenv import load_dotenv

# Load env
load_dotenv()
cookie = os.getenv("BILIBILI_COOKIE")

if not cookie:
    print("❌ Error: BILIBILI_COOKIE not found in .env")
    exit(1)

print(f"✅ Loaded Cookie (Length: {len(cookie)})")

# Test Target: UID 410532721 (Original problematic UID)
uid = "410532721"
url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={uid}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"https://space.bilibili.com/{uid}/dynamic",
    "Origin": "https://space.bilibili.com",
    "Cookie": cookie
}

print(f"\n🚀 Testing API for UID: {uid}")
try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"HTTP Status Code: {response.status_code}")
    
    try:
        data = response.json()
    except json.JSONDecodeError:
        print(f"❌ Failed to decode JSON. Response text:\n{response.text[:200]}")
        exit(1)

    code = data.get("code")
    message = data.get("message")
    
    print(f"Bilibili API Code: {code}")
    print(f"Bilibili API Message: {message}")
    
    if code == 0:
        data_obj = data.get("data", {})
        if not data_obj:
             print("❌ 'data' field is None or empty.")
        else:
            items = data_obj.get("items")
            if items is None:
                 print("❌ 'items' field is None inside data.")
                 print(f"Available keys in data: {list(data_obj.keys())}")
            else:
                print(f"✅ API Success. Found {len(items)} items.")
                if len(items) > 0:
                    first_item = items[0]
                    print(f"First Item ID: {first_item.get('id_str')}")
                    print(f"First Item Type: {first_item.get('type')}")
                    # Optional: Print raw first item to check structure
                    # print(json.dumps(first_item, indent=2, ensure_ascii=False))
    else:
        print(f"❌ API Failed.")
        # print(f"Raw Response: {json.dumps(data, ensure_ascii=False)}")

except Exception as e:
    print(f"❌ Exception: {e}")
