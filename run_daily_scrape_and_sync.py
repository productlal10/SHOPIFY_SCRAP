#!/usr/bin/env python3
"""
Master Daily Shopify Scraper & Google Sheets Sync Runner
========================================================
Runs full inventory scrapers for Cava Athleisure and Musclemind,
saves timestamped daily snapshot files, and uploads data into Google Sheets.
"""

import sys
import os
import time
import argparse
from datetime import datetime

# Import local scraper modules
from cava import scrape_all_cava_products
from musclemind import scrape_all_musclemind_products
from upload_to_google_sheets import upload_csv_to_sheet

def run_daily_automation(sheet_identifier: str = None):
    today_str = datetime.now().strftime("%Y-%m-%d")
    print("="*60)
    print(f"      STARTING DAILY SHOPIFY SCRAPE & SYNC [{today_str}]")
    print("="*60)

    # 1. Scrape Cava Athleisure
    print("\n--- [1/2] Scraping Cava Athleisure ---")
    cava_rows, _ = scrape_all_cava_products()
    cava_csv = "cava_exact_inventory.csv"
    cava_snapshot = f"cava_inventory_{today_str}.csv"
    
    if cava_rows:
        import csv
        fieldnames = list(cava_rows[0].keys())
        with open(cava_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(cava_rows)
            
        with open(cava_snapshot, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(cava_rows)
            
        print(f"[✓] Saved Cava data ({len(cava_rows)} variants) to '{cava_csv}' and snapshot '{cava_snapshot}'")

    # 2. Scrape Musclemind
    print("\n--- [2/2] Scraping Musclemind ---")
    musclemind_rows = scrape_all_musclemind_products()
    musclemind_csv = "musclemind_exact_inventory.csv"
    musclemind_snapshot = f"musclemind_inventory_{today_str}.csv"
    
    if musclemind_rows:
        import csv
        fieldnames = list(musclemind_rows[0].keys())
        with open(musclemind_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(musclemind_rows)
            
        with open(musclemind_snapshot, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(musclemind_rows)
            
        print(f"[✓] Saved Musclemind data ({len(musclemind_rows)} variants) to '{musclemind_csv}' and snapshot '{musclemind_snapshot}'")

    # 3. Upload to Google Sheets if --sheet provided
    if sheet_identifier:
        print("\n--- [Google Sheets Sync] Uploading to Google Sheets ---")
        try:
            upload_csv_to_sheet(sheet_identifier, cava_csv, tab_name="Cava_Inventory")
            upload_csv_to_sheet(sheet_identifier, musclemind_csv, tab_name="Musclemind_Inventory")
            print("[✓] All datasets successfully synced to Google Sheets!")
        except Exception as e:
            print(f"[!] Google Sheets Upload Error: {e}")

    print("\n" + "="*60)
    print("      DAILY AUTOMATION COMPLETED SUCCESSFULLY")
    print("="*60 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Run daily Shopify inventory scrapers and sync to Google Sheets.")
    parser.add_argument("--sheet", type=str, help="Google Sheet URL, ID, or Name to upload daily data to.")
    args = parser.parse_args()

    run_daily_automation(sheet_identifier=args.sheet)

if __name__ == "__main__":
    main()
