#!/usr/bin/env python3
"""
Google Sheets Daily Sync Module
===============================
Connects via Google Service Account (shopify-scrapper@shopifyscrap.iam.gserviceaccount.com)
and uploads daily e-commerce inventory datasets into Google Sheets tabs.
"""

import os
import sys
import json
import csv
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

DEFAULT_CREDENTIALS_PATH = "/Users/turbom/Downloads/shopifyscrap-1fdcd0018d2e.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_gspread_client(credentials_path: str = None):
    """Authenticate and return gspread client with multi-environment fallback."""
    # 1. Environment variable path
    env_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
    if env_path and os.path.exists(env_path):
        return gspread.service_account(filename=env_path)

    # 2. Environment variable JSON string (GitHub Actions Secret)
    env_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if env_json:
        try:
            creds_dict = json.loads(env_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            return gspread.authorize(creds)
        except Exception as e:
            print(f"[!] Warning: Error parsing GOOGLE_CREDENTIALS_JSON: {e}")

    # 3. Passed credentials path or fallback files
    paths_to_check = [
        credentials_path,
        "shopifyscrap-key.json",
        DEFAULT_CREDENTIALS_PATH
    ]

    for path in paths_to_check:
        if path and os.path.exists(path):
            return gspread.service_account(filename=path)

    raise FileNotFoundError(
        "Service account credentials not found. Set GOOGLE_CREDENTIALS_JSON or provide valid json path."
    )

def upload_csv_to_sheet(sheet_identifier: str, csv_path: str, tab_name: str = "Daily_Inventory", credentials_path: str = None):
    """
    Uploads a CSV file to a specific Google Sheet tab.
    sheet_identifier: Can be Google Sheet URL, Sheet ID, or Sheet Name.
    """
    if not os.path.exists(csv_path):
        print(f"[!] CSV file not found: {csv_path}")
        return False
        
    client = get_gspread_client(credentials_path)
    
    # Open spreadsheet
    if "docs.google.com/spreadsheets" in sheet_identifier:
        spreadsheet = client.open_by_url(sheet_identifier)
    elif len(sheet_identifier) > 25 and not " " in sheet_identifier:
        try:
            spreadsheet = client.open_by_key(sheet_identifier)
        except Exception:
            spreadsheet = client.open(sheet_identifier)
    else:
        spreadsheet = client.open(sheet_identifier)
        
    print(f"[+] Connected to Google Sheet: '{spreadsheet.title}' ({spreadsheet.url})")
    
    # Read CSV
    df = pd.read_csv(csv_path)
    df = df.fillna("")
    
    # Get or create worksheet tab
    try:
        worksheet = spreadsheet.worksheet(tab_name)
        worksheet.clear()
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=tab_name, rows=len(df)+50, cols=len(df.columns)+5)
        
    # Convert dataframe to list of rows
    header = df.columns.tolist()
    values = df.astype(str).values.tolist()
    data = [header] + values
    
    # Upload data
    worksheet.update(data, "A1")
    
    print(f"[✓] Successfully uploaded {len(df)} rows to tab '{tab_name}' in Google Sheet!")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 upload_to_google_sheets.py <SHEET_URL_OR_ID_OR_NAME> <CSV_PATH> [TAB_NAME]")
        sys.exit(1)
        
    sheet_id = sys.argv[1]
    csv_file = sys.argv[2]
    tab = sys.argv[3] if len(sys.argv) > 3 else "Daily_Inventory"
    
    upload_csv_to_sheet(sheet_id, csv_file, tab)
