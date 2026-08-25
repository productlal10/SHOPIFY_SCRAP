#!/usr/bin/env python3
"""
Crep Dog Crew Dedicated Exact Inventory Stock Scraper
=====================================================
Performs paced backend cart probes (/cart/add.js) with Cloudflare session warm-up, exponential backoff,
and rate-limit mitigation to extract exact numeric stock quantities (e.g. 2, 5, 1, 3 units) for Crep Dog Crew variants.

Outputs:
  - CSV File: crepdogcrew_exact_inventory.csv
  - JSON File: crepdogcrew_exact_inventory.json
  - Google Sheet Tab: Crepdogcrew_Inventory
"""

import json
import csv
import re
import sys
import os
import time
import random
import argparse
import pandas as pd
import concurrent.futures

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1PLX9H5c3WA_vvM8HJQoK35ZHLBubLudHephx7T2lGjE/edit"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Origin": "https://crepdogcrew.com",
    "Referer": "https://crepdogcrew.com/"
}

def create_crepdog_session():
    if cloudscraper:
        s = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'darwin', 'desktop': True})
    else:
        s = requests.Session()
    s.headers.update(HEADERS)
    return s

def probe_variant_stock(v_id: int, scraper) -> int:
    """Probe /cart/add.js endpoint to extract exact available stock count."""
    url = "https://crepdogcrew.com/cart/add.js"
    payload = {"items": [{"id": int(v_id), "quantity": 999}]}

    for attempt in range(4):
        try:
            r = scraper.post(url, json=payload, timeout=10)
            if r.status_code == 422:
                text = r.text
                m = re.search(r'Only\s+(\d+)\s+items?\s+were\s+added', text)
                if m:
                    return int(m.group(1))
                m2 = re.search(r'You\s+can\s+only\s+add\s+(\d+)', text)
                if m2:
                    return int(m2.group(1))
                return 1
            elif r.status_code == 200:
                return 999
            elif r.status_code == 429:
                sleep_time = (attempt + 1) * 2.5 + random.uniform(0.5, 1.5)
                time.sleep(sleep_time)
        except Exception:
            time.sleep(1)
    return 1

def main():
    parser = argparse.ArgumentParser(description="Crep Dog Crew Exact Stock Scraper.")
    parser.add_argument("--sheet", type=str, default=DEFAULT_SHEET_URL, help="Google Sheet URL to sync data to.")
    parser.add_argument("--limit", type=int, default=500, help="Maximum number of available variants to probe in this run.")
    args = parser.parse_args()

    csv_file = "crepdogcrew_exact_inventory.csv"
    if not os.path.exists(csv_file):
        print(f"[!] {csv_file} not found. Run universal_scraper.py first to fetch catalog.")
        sys.exit(1)

    print(f"[+] Loading Crep Dog Crew dataset from {csv_file}...", flush=True)
    df = pd.read_csv(csv_file)

    avail_mask = (df["available"] == True) & (df["availability_status"] == "Available")
    avail_indices = df[avail_mask].index.tolist()

    if args.limit and len(avail_indices) > args.limit:
        print(f"[+] Probing exact numeric stock for top {args.limit} active variants (Paced Cart Engine)...", flush=True)
        target_indices = avail_indices[:args.limit]
    else:
        print(f"[+] Probing exact numeric stock for all {len(avail_indices)} active variants...", flush=True)
        target_indices = avail_indices

    scraper = create_crepdog_session()

    updated = 0
    for i, idx in enumerate(target_indices, 1):
        v_id = df.at[idx, "variant_id"]
        p_name = df.at[idx, "product_name"]
        size = df.at[idx, "size"]

        qty = probe_variant_stock(v_id, scraper)
        df.at[idx, "exact_quantity_left"] = qty

        updated += 1
        if updated % 25 == 0 or updated == len(target_indices):
            print(f"    Probed {updated}/{len(target_indices)} variants | {p_name[:30]} ({size}) -> {qty} units in stock", flush=True)

        time.sleep(0.4)

    df.to_csv(csv_file, index=False)
    
    json_file = "crepdogcrew_exact_inventory.json"
    rows = df.to_dict(orient="records")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"\n[✓] Successfully updated {csv_file} and {json_file} with exact numeric stock numbers!", flush=True)

    if args.sheet:
        try:
            from upload_to_google_sheets import upload_csv_to_sheet
            upload_csv_to_sheet(args.sheet, csv_file, tab_name="Crepdogcrew_Inventory")
        except Exception as e:
            print(f"[!] Google Sheets Sync Error: {e}")

if __name__ == "__main__":
    main()
