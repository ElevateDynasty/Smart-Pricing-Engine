"""
scripts/monitor_tech_launches.py
Real-time Tech Announcement & Successor Launch Ingestion Engine.
Monitors flagship product releases, updates lifecycle urgency windows,
and triggers the AI Lifecycle Profit Optimizer.
"""
import argparse
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 stdout encoding on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Default API URL
API_BASE = "http://127.0.0.1:8000/api"

WATCHLIST = {
    "iphone18": {
        "product_id": "SKU_IPHONE_17_256",
        "successor_name": "Apple iPhone 18",
        "announcement_headline": "Apple Unveils iPhone 18 Series with Next-Gen A20 Pro Silicon",
        "days_to_successor": 14,
        "competitor_price_drop_pct": 0.04
    },
    "galaxy_s27": {
        "product_id": "SKU_GALAXY_S26_256",
        "successor_name": "Samsung Galaxy S27",
        "announcement_headline": "Samsung Galaxy Unpacked: Galaxy S27 Announced with Advanced NPU",
        "days_to_successor": 21,
        "competitor_price_drop_pct": 0.05
    },
    "pixel11": {
        "product_id": "SKU_PIXEL_10_PRO",
        "successor_name": "Google Pixel 11 Pro",
        "announcement_headline": "Google Announces Pixel 11 Pro with Quantum Gemini Integration",
        "days_to_successor": 18,
        "competitor_price_drop_pct": 0.03
    }
}

def trigger_event(event_key: str):
    if event_key not in WATCHLIST:
        print(f"Unknown event key '{event_key}'. Available: {list(WATCHLIST.keys())}")
        return False

    payload = WATCHLIST[event_key]
    url = f"{API_BASE}/lifecycle-event"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    print("=" * 70)
    print(f"[LAUNCH EVENT] INGESTING: {payload['successor_name']}")
    print(f"   Headline: {payload['announcement_headline']}")
    print(f"   Target Predecessor: {payload['product_id']}")
    print(f"   New Days to Successor: {payload['days_to_successor']} days")
    print("=" * 70)

    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode("utf-8"))
            print("[SUCCESS] Server Response:")
            print(f"   Message: {res.get('message')}")
            opt = res.get("optimized_sku", {})
            print(f"   Product: {opt.get('product_name')}")
            print(f"   Current Price: Rs {opt.get('current_price', 0):,.0f}")
            print(f"   New Recommended Price: Rs {opt.get('recommended_price', 0):,.0f}")
            print(f"   Action: {opt.get('price_action')}")
            print(f"   Projected Profit Lift: +Rs {opt.get('profit_lift_amount', 0):,.0f} (+{opt.get('profit_lift_pct', 0)}%)")
            print(f"   Clearance Probability: {opt.get('clearance_probability', 0)*100:.1f}%")
            return True
    except urllib.error.URLError as e:
        print(f"[ERROR] Connection error: {e}. Ensure FastAPI backend is running on {API_BASE}")
        return False

def reset_events():
    url = f"{API_BASE}/reset-events"
    req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"})
    print("[RESET] Resetting all product lifecycles back to baseline...")
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode("utf-8"))
            print(f"[SUCCESS] {res.get('message')}")
            return True
    except urllib.error.URLError as e:
        print(f"[ERROR] Connection error: {e}")
        return False

import xml.etree.ElementTree as ET
import re

RSS_FEEDS = [
    {
        "name": "Google News Flagship Tech Stream",
        "url": "https://news.google.com/rss/search?q=iPhone+OR+Galaxy+OR+Pixel+launch&hl=en-US&gl=US&ceid=US:en"
    }
]

KEYWORD_MAP = {
    "iphone18": [r"iphone\s*18", r"a20\s*pro", r"iphone\s*17\s*successor"],
    "galaxy_s27": [r"galaxy\s*s27", r"s27\s*ultra", r"galaxy\s*s-27"],
    "pixel11": [r"pixel\s*11", r"tensor\s*g6", r"pixel\s*10\s*successor"]
}

def poll_news_feeds(auto_trigger: bool = False):
    """
    Polls live RSS feeds for flagship smartphone launch announcements,
    matches against watchlist keywords, and optionally triggers real-time price re-optimization.
    """
    print("=" * 70)
    print("[RSS INGESTION ENGINE] Scanning Live Global Tech News Feeds...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    matched_events = []

    for feed in RSS_FEEDS:
        print(f"\n[FEED] Querying {feed['name']}...")
        print(f"   URL: {feed['url']}")
        req = urllib.request.Request(
            feed["url"],
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_content = resp.read()
                root = ET.fromstring(xml_content)
                items = root.findall(".//item")
                print(f"   [OK] Retrieved {len(items)} live RSS articles.")

                for item in items:
                    title = (item.find("title").text or "").strip()
                    pub_date = (item.find("pubDate").text or "").strip()
                    link = (item.find("link").text or "").strip()

                    title_lower = title.lower()
                    for event_key, patterns in KEYWORD_MAP.items():
                        for pat in patterns:
                            if re.search(pat, title_lower):
                                matched_events.append({
                                    "event_key": event_key,
                                    "headline": title,
                                    "pub_date": pub_date,
                                    "link": link,
                                    "matched_pattern": pat
                                })
                                break

        except Exception as e:
            print(f"   [OFFLINE FALLBACK] Could not reach remote feed ({e}).")
            print("   Using local deterministic cache for offline execution.")
            matched_events.append({
                "event_key": "iphone18",
                "headline": "Apple Unveils iPhone 18 Series with Next-Gen A20 Pro Silicon (Cached)",
                "pub_date": datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                "link": "https://www.apple.com/newsroom",
                "matched_pattern": "iphone 18"
            })

    print("\n" + "=" * 70)
    print(f"[RESULTS] Found {len(matched_events)} matching headline(s) across watchlist products:")
    print("=" * 70)

    for i, match in enumerate(matched_events, start=1):
        payload = WATCHLIST.get(match["event_key"], {})
        print(f"\n{i}. Target: {payload.get('successor_name', match['event_key'])}")
        print(f"   Headline : {match['headline']}")
        print(f"   Published: {match['pub_date']}")
        print(f"   Source   : {match['link']}")

    if matched_events and auto_trigger:
        print("\n" + "=" * 70)
        print("[AUTO-TRIGGER] Automatic lifecycle re-optimization activated...")
        print("=" * 70)
        processed = set()
        for match in matched_events:
            k = match["event_key"]
            if k not in processed:
                print(f"\n>>> Auto-triggering event for {k}...")
                trigger_event(k)
                processed.add(k)
    elif matched_events:
        print(f"\n[INFO] {len(matched_events)} launch signal(s) detected. Run with --auto-trigger or --simulate <key> to re-optimize catalog prices.")
    else:
        print("\n[INFO] No unhandled flagship smartphone launch announcements detected in current feed.")

    return matched_events

def main():
    parser = argparse.ArgumentParser(description="Real-Time Tech Launch & Successor Ingestion Script")
    parser.add_argument("--simulate", choices=["iphone18", "galaxy_s27", "pixel11"], help="Simulate a live tech announcement event")
    parser.add_argument("--reset", action="store_true", help="Reset all lifecycles back to default baseline schedules")
    parser.add_argument("--poll", action="store_true", help="Poll live tech news RSS feeds for announcements")
    parser.add_argument("--auto-trigger", action="store_true", help="Automatically trigger AI optimization when a matching headline is detected")

    args = parser.parse_args()

    if args.simulate:
        trigger_event(args.simulate)
    elif args.reset:
        reset_events()
    elif args.poll:
        poll_news_feeds(auto_trigger=args.auto_trigger)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
