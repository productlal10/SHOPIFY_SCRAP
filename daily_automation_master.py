#!/usr/bin/env python3
"""
Master Daily Automated Inventory Scraping & Sales Analytics Pipeline
=====================================================================
Automates daily inventory scraping, exact stock tracking, sales delta analytics,
and Google Sheets synchronization for target e-commerce brands:
  1. Cava Athleisure (cavaathleisure.com)
  2. Musclemind (musclemind.com)
  3. Kosher Casual (koshercasual.com)

Features:
  - Scrapes exact inventory for all 3 brands.
  - Syncs raw datasets to Google Sheets tabs:
      * Cava_Inventory
      * Musclemind_Inventory
      * Koshercasual_Inventory
  - Archives daily timestamped CSV snapshots in daily_snapshots/YYYY-MM-DD/
  - Calculates daily units sold (Stock_T1 - Stock_T2), restocks, and estimated revenue.
  - Uploads date-wise sales analytics report to Google Sheets tab 'Sales_Report_YYYY-MM-DD'.
  - Uploads consolidated brand performance summary to tab 'Executive_Sales_Summary'.

Usage:
  python3 daily_automation_master.py
  python3 daily_automation_master.py --sheet "https://docs.google.com/spreadsheets/d/1PLX9H5c3WA_vvM8HJQoK35ZHLBubLudHephx7T2lGjE/edit"
"""

import os
import sys
import json
import csv
import glob
import time
import argparse
from datetime import datetime
import pandas as pd

from universal_scraper import scrape_universal_shopify_store
from upload_to_google_sheets import upload_csv_to_sheet

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1PLX9H5c3WA_vvM8HJQoK35ZHLBubLudHephx7T2lGjE/edit"

TARGET_STORES = [
    {"name": "Cava Athleisure", "url": "https://cavaathleisure.com", "tab": "Cava_Inventory", "slug": "cavaathleisure"},
    {"name": "Musclemind", "url": "https://musclemind.com", "tab": "Musclemind_Inventory", "slug": "musclemind"},
    {"name": "Kosher Casual", "url": "http://koshercasual.com", "tab": "Koshercasual_Inventory", "slug": "koshercasual"}
]

def save_csv(file_path, rows):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def save_json(file_path, rows):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

def run_sales_delta_analytics(today_str, snapshot_dir, sheet_url):
    print("\n[+] Running Daily Sales Delta & Revenue Analytics...", flush=True)
    all_deltas = []
    summary_rows = []
    
    for store in TARGET_STORES:
        slug = store["slug"]
        store_name = store["name"]
        
        # Find snapshot files for this store
        pattern = os.path.join(snapshot_dir, "*", f"{slug}_exact_inventory.csv")
        files = sorted(glob.glob(pattern))
        
        if len(files) < 2:
            print(f"    [*] {store_name}: Need at least 2 snapshot days to compute sales delta (Found {len(files)}). Skipping delta.")
            continue
            
        t1_file = files[-2]  # Yesterday / Prior
        t2_file = files[-1]  # Today
        
        t1_date = os.path.basename(os.path.dirname(t1_file))
        t2_date = os.path.basename(os.path.dirname(t2_file))
        
        print(f"    Analyzing {store_name}: {t1_date} vs {t2_date}...")
        
        try:
            df1 = pd.read_csv(t1_file)
            df2 = pd.read_csv(t2_file)
            
            # Standardize stock column
            for df in [df1, df2]:
                if "exact_quantity_left" in df.columns:
                    df["stock_qty"] = pd.to_numeric(df["exact_quantity_left"], errors="coerce").fillna(0)
                elif "stock_qty" in df.columns:
                    df["stock_qty"] = pd.to_numeric(df["stock_qty"], errors="coerce").fillna(0)
                else:
                    df["stock_qty"] = 0
            
            merged = pd.merge(
                df1[["variant_id", "product_name", "size", "sku", "price", "stock_qty", "product_url"]],
                df2[["variant_id", "stock_qty"]],
                on="variant_id",
                how="inner",
                suffixes=("_prior", "_current")
            )
            
            merged["stock_delta"] = merged["stock_qty_prior"] - merged["stock_qty_current"]
            merged["units_sold"] = merged["stock_delta"].apply(lambda x: int(x) if x > 0 else 0)
            merged["units_restocked"] = merged["stock_delta"].apply(lambda x: int(abs(x)) if x < 0 else 0)
            merged["price_numeric"] = pd.to_numeric(merged["price"], errors="coerce").fillna(0)
            merged["estimated_revenue"] = merged["units_sold"] * merged["price_numeric"]
            merged["store_name"] = store_name
            merged["date"] = today_str
            merged["stock_remaining_today"] = merged["stock_qty_current"]
            
            # Reorder columns for clean reporting
            cols = [
                "date", "store_name", "product_name", "size", "sku", "price",
                "units_sold", "units_restocked", "estimated_revenue",
                "stock_remaining_today", "product_url"
            ]
            merged = merged[cols]
            
            # Filter for items with activity (sold or restocked)
            activity = merged[(merged["units_sold"] > 0) | (merged["units_restocked"] > 0)].copy()
            if not activity.empty:
                all_deltas.append(activity)
                total_sold = int(activity["units_sold"].sum())
                total_restocked = int(activity["units_restocked"].sum())
                total_rev = float(activity["estimated_revenue"].sum())
                
                print(f"        [✓] {store_name}: {total_sold:,} Units Sold | Estimated Revenue: ₹{total_rev:,.2f}")
                
                summary_rows.append({
                    "date": today_str,
                    "store_name": store_name,
                    "total_units_sold": total_sold,
                    "total_units_restocked": total_restocked,
                    "total_estimated_revenue": round(total_rev, 2),
                    "items_with_sales": len(activity[activity["units_sold"] > 0])
                })
            else:
                print(f"        [*] {store_name}: No inventory changes detected between snapshots.")
                
        except Exception as e:
            print(f"        [!] Delta calculation error for {store_name}: {e}")
            
    if all_deltas:
        combined = pd.concat(all_deltas, ignore_index=True)
        analytics_file = os.path.join(snapshot_dir, today_str, f"sales_report_{today_str}.csv")
        combined.to_csv(analytics_file, index=False)
        print(f"\n[✓] Daily Detailed Sales Report saved to: {analytics_file}")
        
        # Upload date-wise report tab to Google Sheets
        if sheet_url:
            date_tab = f"Sales_Report_{today_str}"
            try:
                print(f"[+] Syncing Date-Wise Sales Report to Google Sheets tab '{date_tab}'...", flush=True)
                upload_csv_to_sheet(sheet_url, analytics_file, tab_name=date_tab)
            except Exception as e:
                print(f"[!] Date-wise sheet upload error: {e}")
                
    if summary_rows and sheet_url:
        summary_df = pd.DataFrame(summary_rows)
        summary_file = os.path.join(snapshot_dir, today_str, f"executive_sales_summary_{today_str}.csv")
        summary_df.to_csv(summary_file, index=False)
        try:
            print(f"[+] Syncing Executive Sales Summary to Google Sheets tab 'Executive_Sales_Summary'...", flush=True)
            upload_csv_to_sheet(sheet_url, summary_file, tab_name="Executive_Sales_Summary")
        except Exception as e:
            print(f"[!] Executive summary sheet upload error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Master Daily Automated Inventory Scraping & Analytics Pipeline.")
    parser.add_argument("--sheet", type=str, default=DEFAULT_SHEET_URL, help="Target Google Sheet URL.")
    args = parser.parse_args()

    today_str = datetime.now().strftime("%Y-%m-%d")
    snapshot_dir = "daily_snapshots"
    today_folder = os.path.join(snapshot_dir, today_str)
    os.makedirs(today_folder, exist_ok=True)

    print("\n" + "="*70)
    print(f"       MASTER DAILY INVENTORY & SALES PIPELINE ({today_str})       ")
    print("="*70)
    print(f" Target Google Sheet: {args.sheet}\n")

    scraped_files = {}

    for store in TARGET_STORES:
        store_name = store["name"]
        store_url = store["url"]
        tab_name = store["tab"]
        slug = store["slug"]
        
        print(f"\n[=== Phase 1: Scraping {store_name} ({store_url}) ===]", flush=True)
        rows, _ = scrape_universal_shopify_store(store_url)
        
        if rows:
            # 1. Save standard CSV & JSON
            csv_file = f"{slug}_exact_inventory.csv"
            json_file = f"{slug}_exact_inventory.json"
            save_csv(csv_file, rows)
            save_json(json_file, rows)
            
            # 2. Archive daily timestamped snapshot
            daily_csv = os.path.join(today_folder, f"{slug}_exact_inventory.csv")
            daily_json = os.path.join(today_folder, f"{slug}_exact_inventory.json")
            save_csv(daily_csv, rows)
            save_json(daily_json, rows)
            
            scraped_files[slug] = csv_file
            
            print(f"[✓] Saved {len(rows):,} size variants for {store_name} to {csv_file} & {daily_csv}")
            
            # 3. Sync raw dataset to Google Sheets
            if args.sheet:
                try:
                    upload_csv_to_sheet(args.sheet, csv_file, tab_name=tab_name)
                except Exception as e:
                    print(f"[!] Google Sheets sync error for {store_name}: {e}")
        else:
            print(f"[!] Warning: No rows scraped for {store_name}.")

    # Run Daily Sales Delta & Revenue Analytics
    run_sales_delta_analytics(today_str, snapshot_dir, args.sheet)

    print("\n" + "="*70)
    print(f"       DAILY INVENTORY PIPELINE COMPLETED SUCCESSFULLY       ")
    print("="*70 + "\n", flush=True)

if __name__ == "__main__":
    main()
