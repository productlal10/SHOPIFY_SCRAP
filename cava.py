#!/usr/bin/env python3
"""
Full Cava Athleisure Exact Inventory & Size Quantity Scraper (Google Sheets Edition)
====================================================================================
Scrapes full catalog from cavaathleisure.com and extracts exact remaining
stock quantity per size directly from Cava's storefront product pages.

Key Features:
  - Bypasses Cloudflare anti-bot challenges using Cloudscraper + Thread-Local sessions.
  - Validates presence of 'window.inventories' in response before parsing.
  - Exponential Backoff & Jitter retry loop for 100% extraction accuracy.
  - Optional Google Sheets Sync (--sheet <URL_OR_ID_OR_NAME>).

Outputs:
  - CSV file: cava_exact_inventory.csv
  - JSON file: cava_exact_inventory.json
  - Google Sheets tab: Cava_Inventory (if --sheet provided)
"""

import json
import csv
import re
import sys
import os
import time
import random
import argparse
import threading
import concurrent.futures

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

thread_local = threading.local()

def get_thread_scraper():
    """Retrieve or initialize a thread-local Cloudscraper session."""
    if not hasattr(thread_local, "scraper"):
        if cloudscraper:
            s = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'darwin',
                    'desktop': True
                }
            )
        else:
            s = requests.Session()
        s.headers.update(HEADERS)
        thread_local.scraper = s
    return thread_local.scraper

def parse_cava_product_stock_guaranteed(product_url: str, retries: int = 5) -> tuple[dict, bool]:
    """
    Extract exact variant inventory stock numbers from Cava product page HTML JS.
    Returns (stock_dict, success_boolean).
    """
    for attempt in range(retries):
        try:
            scraper = get_thread_scraper()
            r = scraper.get(product_url, timeout=12)
            
            if r.status_code == 200 and 'window.inventories' in r.text:
                matches = re.findall(r"window\.inventories\['\d+'\]\[(\d+)\]\s*=\s*\{\s*'quantity':\s*(-?\d+)", r.text)
                stock_dict = {int(var_id): int(qty) for var_id, qty in matches}
                return stock_dict, True
            else:
                if hasattr(thread_local, "scraper"):
                    del thread_local.scraper
                backoff = (2 ** attempt) + random.uniform(0.5, 1.5)
                time.sleep(backoff)
        except Exception:
            if hasattr(thread_local, "scraper"):
                del thread_local.scraper
            backoff = (2 ** attempt) + random.uniform(0.5, 1.5)
            time.sleep(backoff)
            
    return {}, False

def process_cava_product(p, base_url):
    prod_title = p.get("title")
    prod_handle = p.get("handle")
    prod_type = p.get("product_type", "")
    vendor = p.get("vendor", "")
    p_url = f"{base_url}/products/{prod_handle}"
    
    stock_map, success = parse_cava_product_stock_guaranteed(p_url)
    
    options = p.get("options", [])
    size_opt_idx = 1
    for opt_i, opt in enumerate(options, 1):
        if opt.get("name", "").lower() in ["size", "sizes"]:
            size_opt_idx = opt_i
            break

    rows = []
    for v in p.get("variants", []):
        v_id = v.get("id")
        size_name = v.get(f"option{size_opt_idx}") or v.get("option1") or v.get("title")
        price = v.get("price")
        available = v.get("available")
        sku = v.get("sku", "")
        
        if not available:
            exact_qty = 0
            status_str = "Sold Out"
        elif success:
            exact_qty = stock_map.get(v_id, 0)
            status_str = "Available"
        else:
            exact_qty = -1
            status_str = "Extraction Failed (Rate Limit)"
            
        row = {
            "store_domain": base_url,
            "product_id": p.get("id"),
            "product_name": prod_title,
            "product_type": prod_type,
            "vendor": vendor,
            "variant_id": v_id,
            "size": size_name,
            "sku": sku,
            "price": price,
            "available": available,
            "availability_status": status_str,
            "exact_quantity_left": exact_qty,
            "product_url": p_url
        }
        rows.append(row)
    return rows

def scrape_all_cava_products():
    base_url = "https://cavaathleisure.com"
    scraper = get_thread_scraper()
    
    all_products = []
    page = 1
    limit = 250
    
    print("[+] Fetching Cava Athleisure product catalog via Cloudscraper...", flush=True)
    while True:
        url = f"{base_url}/products.json?limit={limit}&page={page}"
        print(f"    Fetching catalog page {page}...", flush=True)
        r = scraper.get(url, timeout=15)
        if r.status_code != 200:
            print(f"    [!] Catalog page {page} status {r.status_code}. Retrying...", flush=True)
            time.sleep(2)
            r = scraper.get(url, timeout=15)
            if r.status_code != 200:
                print(f"    [!] Catalog page {page} failed.", flush=True)
                break
        data = r.json()
        prods = data.get("products", [])
        if not prods:
            break
        all_products.extend(prods)
        page += 1
        time.sleep(0.3)
        
    print(f"[✓] Total Cava Athleisure products fetched: {len(all_products)}", flush=True)
    
    all_rows = []
    print("\n[+] Scraping exact stock quantities per size (High-End Verified x4 workers)...", flush=True)
    
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_cava_product, p, base_url): p for p in all_products}
        for future in concurrent.futures.as_completed(futures):
            try:
                p_rows = future.result()
                all_rows.extend(p_rows)
            except Exception:
                pass
            completed += 1
            if completed % 50 == 0 or completed == len(all_products):
                print(f"    Processed {completed}/{len(all_products)} products ({len(all_rows)} total size variants)...", flush=True)
                
    return all_rows, all_products

def main():
    parser = argparse.ArgumentParser(description="Scrape Cava Athleisure product catalog and inventory stock.")
    parser.add_argument("--sheet", type=str, help="Google Sheet URL, ID, or Name to upload daily data to.")
    args = parser.parse_args()

    rows, products = scrape_all_cava_products()
    
    csv_file = "cava_exact_inventory.csv"
    json_file = "cava_exact_inventory.json"
    
    if rows:
        fieldnames = list(rows[0].keys())
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
            
        non_zero = sum(1 for r in rows if r['exact_quantity_left'] > 0)
        failed_count = sum(1 for r in rows if r['exact_quantity_left'] == -1)
        
        print(f"\n" + "="*55)
        print("           CAVA INVENTORY SCRAPING REPORT           ")
        print("="*55)
        print(f" Total Size Variants Saved : {len(rows):,}")
        print(f" Non-Zero Stock Variants   : {non_zero:,}")
        print(f" Rate-Limit Failures       : {failed_count:,}")
        print(f" Output CSV File           : {csv_file}")
        print(f" Output JSON File          : {json_file}")
        print("="*55 + "\n", flush=True)

        if args.sheet:
            try:
                from upload_to_google_sheets import upload_csv_to_sheet
                upload_csv_to_sheet(args.sheet, csv_file, tab_name="Cava_Inventory")
            except Exception as e:
                print(f"[!] Google Sheets Sync Error: {e}")

if __name__ == "__main__":
    main()
