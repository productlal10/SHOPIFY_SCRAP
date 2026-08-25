#!/usr/bin/env python3
"""
Universal Shopify Exact Inventory & Stock Scraper Engine
=========================================================
Universal e-commerce scraper that accepts ANY Shopify website URL and extracts full product catalog
and EXACT numeric inventory stock quantities per size variant using a multi-tiered extraction strategy.

Features:
  - Multi-tiered extraction (window.inventories, GloboPreorder, GrowWave, DOM script JSON, Cart Probing).
  - Resilient Catalog Engine with dual fallback (/products.json & /collections/all/products.json).
  - Fast starting batch limit (--limit N) for instant testing vs full catalog mode.
  - Automatic Google Sheets sync.

Usage:
  python3 universal_scraper.py
  python3 universal_scraper.py --url "https://www.boat-lifestyle.com" --limit 50
  python3 universal_scraper.py --url "https://prekies.com"
  python3 universal_scraper.py --url "http://koshercasual.com"
  python3 universal_scraper.py --url "https://musclemind.com" --sheet "https://docs.google.com/spreadsheets/d/1PLX9H5c3WA_vvM8HJQoK35ZHLBubLudHephx7T2lGjE/edit"

Outputs:
  - CSV file: <store_name>_exact_inventory.csv
  - JSON file: <store_name>_exact_inventory.json
  - Google Sheet tab: <Store_Name>_Inventory (if --sheet or default sheet configured)
"""

import json
import csv
import re
import sys
import os
import time
import random
import argparse
import urllib.parse
import threading
import concurrent.futures

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

import requests

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1PLX9H5c3WA_vvM8HJQoK35ZHLBubLudHephx7T2lGjE/edit"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
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

def clean_url(url: str) -> str:
    """Normalize input URL to base scheme + domain."""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def get_store_slug(base_url: str) -> str:
    """Extract clean store identifier from domain."""
    domain = urllib.parse.urlparse(base_url).netloc
    slug = domain.replace("www.", "").split(".")[0]
    return slug if slug else "shopify_store"

def fetch_catalog_products(base_url: str, limit_products: int = None):
    """Fetch full catalog products via Shopify /products.json or /collections/all/products.json APIs."""
    all_products = []
    page = 1
    limit = 250
    
    print(f"[+] Fetching catalog from {base_url}...", flush=True)
    
    endpoints = [
        f"{base_url}/products.json",
        f"{base_url}/collections/all/products.json"
    ]
    
    selected_endpoint = endpoints[0]
    
    while True:
        url = f"{selected_endpoint}?limit={limit}&page={page}"
        print(f"    Fetching catalog page {page}...", flush=True)
        
        success = False
        prods = []
        
        for attempt in range(3):
            try:
                scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'darwin', 'desktop': True}) if cloudscraper else requests.Session()
                scraper.headers.update(HEADERS)
                r = scraper.get(url, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    prods = data.get("products", [])
                    if not prods:
                        success = True
                        break
                    all_products.extend(prods)
                    success = True
                    break
                elif r.status_code == 429 and selected_endpoint == endpoints[0]:
                    print(f"    [!] Endpoint {selected_endpoint} returned 429. Switching to collection API fallback...", flush=True)
                    selected_endpoint = endpoints[1]
                    url = f"{selected_endpoint}?limit={limit}&page={page}"
                    time.sleep(1)
            except Exception:
                time.sleep(1.5)
        
        if not success or not prods:
            break
            
        if limit_products and len(all_products) >= limit_products:
            all_products = all_products[:limit_products]
            break
            
        page += 1
        time.sleep(0.3)
            
    print(f"[✓] Total products fetched from {base_url}: {len(all_products)}", flush=True)
    return all_products

def probe_cart_add_exact_stock(base_url: str, v_id: int) -> int:
    """Probe /cart/add.js endpoint to extract exact available stock count."""
    scraper = get_thread_scraper()
    url = f"{base_url}/cart/add.js"
    payload = {"items": [{"id": int(v_id), "quantity": 999}]}

    try:
        r = scraper.post(url, json=payload, timeout=8)
        if r.status_code == 422:
            text = r.text
            m = re.search(r'Only\s+(\d+)\s+items?\s+were\s+added', text)
            if m:
                return int(m.group(1))
            m2 = re.search(r'You\s+can\s+only\s+add\s+(\d+)', text)
            if m2:
                return int(m2.group(1))
            return 0
        elif r.status_code == 200:
            return 999
    except Exception:
        pass
    return None

def parse_hybrid_product_stock(product_url: str, base_url: str) -> dict:
    """
    Hybrid multi-tiered stock extraction engine:
      Tier 1: window.inventories (Cava pattern)
      Tier 2: GloboPreorderParams (Musclemind pattern)
      Tier 3: GrowWave gwProductInventoryQuantity (Kosher Casual pattern)
      Tier 4: Multiline Script Block JSON Engine (Prekies & theme script tags)
      Tier 5: Direct Variant Regex Matcher
    """
    try:
        scraper = get_thread_scraper()
        r = scraper.get(product_url, timeout=12)
        if r.status_code != 200:
            return {}
        html = r.text

        stock_dict = {}

        # Tier 1: Cava pattern (window.inventories)
        if "window.inventories" in html:
            matches = re.findall(r"window\.inventories\['\d+'\]\[(\d+)\]\s*=\s*\{\s*'quantity':\s*(-?\d+)", html)
            if matches:
                return {int(v_id): int(qty) for v_id, qty in matches}

        # Tier 2: Globo Preorder pattern (Musclemind)
        if "GloboPreorderParams" in html:
            v_matches = re.findall(r'variants\[(\d+)\]\s*=\s*(\{.*?\});', html)
            q_matches = re.findall(r'variants\[(\d+)\]\.inventory_quantity\s*=\s*(-?\d+);', html)
            qty_map = {int(idx): int(qty) for idx, qty in q_matches}
            
            for idx_str, v_json in v_matches:
                try:
                    v_data = json.loads(v_json)
                    v_id = v_data.get("id")
                    idx = int(idx_str)
                    if v_id and idx in qty_map:
                        stock_dict[int(v_id)] = qty_map[idx]
                except Exception:
                    pass
            if stock_dict:
                return stock_dict

        # Tier 3: GrowWave gwProductInventoryQuantity pattern (Kosher Casual)
        if "gwProductInventoryQuantity" in html:
            gw_matches = re.findall(r'window\.gwProductInventoryQuantity\[(\d+)\]\s*=\s*\"?(-?\d+)\"?;', html)
            if gw_matches:
                return {int(v_id): int(qty) for v_id, qty in gw_matches}

        # Tier 4: Multiline Script Block JSON Engine (Prekies & theme script tags)
        if "inventory_quantity" in html:
            script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
            for s_content in script_blocks:
                if "inventory_quantity" in s_content:
                    v_matches = re.findall(r'\{\s*"id"\s*:\s*(\d+)[\s\S]*?"inventory_quantity"\s*:\s*(-?\d+)', s_content)
                    for v_id, qty in v_matches:
                        stock_dict[int(v_id)] = int(qty)
                    
                    inv_matches = re.findall(r'"inventory_quantity"\s*:\s*(-?\d+)[\s\S]*?"id"\s*:\s*(\d+)', s_content)
                    for qty, v_id in inv_matches:
                        stock_dict[int(v_id)] = int(qty)
            if stock_dict:
                return stock_dict

        # Tier 5: Direct variant inventory quantity regex fallback
        direct_matches = re.findall(r'"id"\s*:\s*(\d+)\s*,.*?"inventory_quantity"\s*:\s*\"?(-?\d+)\"?', html)
        if direct_matches:
            return {int(v_id): int(qty) for v_id, qty in direct_matches}

    except Exception:
        pass

    return {}

def extract_size(variant: dict, options: list) -> str:
    """Extract size parameter from variant options."""
    for i, opt in enumerate(options):
        if opt.get("name", "").lower() in ["size", "sizes"]:
            opt_key = f"option{i + 1}"
            if variant.get(opt_key):
                return str(variant.get(opt_key))
    
    if variant.get("option1") and variant.get("option1") != "Default Title":
        return str(variant.get("option1"))
    
    return str(variant.get("title", "Default"))

def process_product_hybrid(p, base_url: str):
    prod_title = p.get("title")
    prod_handle = p.get("handle")
    prod_type = p.get("product_type", "")
    vendor = p.get("vendor", "")
    p_url = f"{base_url}/products/{prod_handle}"
    options = p.get("options", [])

    # Always parse exact stock map from HTML
    stock_map = parse_hybrid_product_stock(p_url, base_url)

    rows = []
    for v in p.get("variants", []):
        v_id = v.get("id")
        size_name = extract_size(v, options)
        price = v.get("price")
        available = v.get("available", False)
        sku = v.get("sku", "")

        if v_id in stock_map:
            exact_qty = stock_map[v_id]
        elif available:
            # Probe backend cart validator for exact stock (boAt & cart probe stores)
            cart_qty = probe_cart_add_exact_stock(base_url, v_id)
            exact_qty = cart_qty if cart_qty is not None else 1
        else:
            exact_qty = 0

        avail_str = "Available" if available and exact_qty > 0 else "Sold Out"

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
            "available": available and exact_qty > 0,
            "availability_status": avail_str,
            "exact_quantity_left": exact_qty,
            "product_url": p_url
        }
        rows.append(row)
    return rows

def scrape_universal_shopify_store(target_url: str, limit_products: int = None):
    base_url = clean_url(target_url)
    store_slug = get_store_slug(base_url)
    
    all_products = fetch_catalog_products(base_url, limit_products)
    if not all_products:
        print(f"[!] No products could be fetched from {base_url}. Verify Shopify domain URL.")
        return [], store_slug

    all_rows = []
    print(f"\n[+] Extracting exact numeric stock quantities across {len(all_products)} products (Workers x4)...", flush=True)

    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_product_hybrid, p, base_url): p for p in all_products}
        for future in concurrent.futures.as_completed(futures):
            try:
                p_rows = future.result()
                all_rows.extend(p_rows)
            except Exception:
                pass
            completed += 1
            if completed % 25 == 0 or completed == len(all_products):
                print(f"    Processed {completed}/{len(all_products)} products ({len(all_rows)} total size variants)...", flush=True)

    return all_rows, store_slug

def main():
    parser = argparse.ArgumentParser(description="Universal Shopify E-Commerce Inventory Scraper.")
    parser.add_argument("--url", type=str, help="Target Shopify website URL (e.g. https://www.boat-lifestyle.com, https://prekies.com)")
    parser.add_argument("--limit", type=int, help="Optional limit on total starting products to fetch (e.g. --limit 50 or --limit 100).")
    parser.add_argument("--sheet", type=str, default=DEFAULT_SHEET_URL, help="Google Sheet URL, ID, or Name to upload daily data to.")
    args = parser.parse_args()

    target_url = args.url
    if not target_url:
        print("\n" + "="*60)
        print("          UNIVERSAL SHOPIFY INVENTORY SCRAPER         ")
        print("="*60)
        target_url = input("Enter Shopify Website URL (e.g. https://www.boat-lifestyle.com): ").strip()
        if not target_url:
            print("[!] No website URL provided. Exiting.")
            sys.exit(1)

    rows, store_slug = scrape_universal_shopify_store(target_url, limit_products=args.limit)

    if rows:
        csv_file = f"{store_slug}_exact_inventory.csv"
        json_file = f"{store_slug}_exact_inventory.json"
        
        fieldnames = list(rows[0].keys())
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)

        non_zero = sum(1 for r in rows if r['exact_quantity_left'] > 0)

        print(f"\n" + "="*60)
        print(f"        UNIVERSAL SHOPIFY SCRAPING REPORT ({store_slug.upper()})        ")
        print("="*60)
        print(f" Target Domain             : {target_url}")
        print(f" Total Size Variants Saved : {len(rows):,}")
        print(f" Non-Zero Stock Variants   : {non_zero:,}")
        print(f" Output CSV File           : {csv_file}")
        print(f" Output JSON File          : {json_file}")
        print("="*60 + "\n", flush=True)

        if args.sheet:
            try:
                from upload_to_google_sheets import upload_csv_to_sheet
                tab_name = f"{store_slug.capitalize()}_Inventory"
                upload_csv_to_sheet(args.sheet, csv_file, tab_name=tab_name)
            except Exception as e:
                print(f"[!] Google Sheets Sync Error: {e}")

if __name__ == "__main__":
    main()
