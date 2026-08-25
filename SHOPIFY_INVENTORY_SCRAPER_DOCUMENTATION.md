# 🛒 Universal Shopify Exact Inventory Scraper & Daily Analytics Documentation

## 📌 Executive Overview
This repository contains an end-to-end, production-grade universal e-commerce web scraping, exact inventory extraction, and automated Google Sheets sync pipeline designed specifically for Shopify-powered storefronts.

Target Brands & Live Automated Tabs:
1. **Cava Athleisure** (`https://cavaathleisure.com`) $\rightarrow$ Tab: `Cava_Inventory` (4,652 rows)
2. **Musclemind** (`https://musclemind.com`) $\rightarrow$ Tab: `Musclemind_Inventory` (555 rows)
3. **Kosher Casual** (`http://koshercasual.com`) $\rightarrow$ Tab: `Koshercasual_Inventory` (5,826 rows)
4. **Prekies** (`https://prekies.com`) $\rightarrow$ Tab: `Prekies_Inventory` (225 rows)
5. **boAt Lifestyle** (`https://www.boat-lifestyle.com`) $\rightarrow$ Tab: `Boat-lifestyle_Inventory` (2,727 rows)
6. **Crep Dog Crew** (`https://crepdogcrew.com`) $\rightarrow$ Tab: `Crepdogcrew_Inventory` (57,051 rows)

Google Sheet URL: [https://docs.google.com/spreadsheets/d/1PLX9H5c3WA_vvM8HJQoK35ZHLBubLudHephx7T2lGjE/edit](https://docs.google.com/spreadsheets/d/1PLX9H5c3WA_vvM8HJQoK35ZHLBubLudHephx7T2lGjE/edit)

---

## 🛠️ Python Command Reference Guide

### 1. Interactive Universal Scraper (Accepts ANY Shopify URL)
```bash
cd /Users/turbom/Desktop/Alan/SHOPIFY_SCRAP
python3 universal_scraper.py
```
*Prompts the user interactively to enter any Shopify store domain URL.*

---

### 2. Scrape ANY Shopify Store via CLI `--url`
```bash
python3 universal_scraper.py --url "https://any-shopify-store.com"
```

---

### 3. Fast Starting Batch Mode (`--limit N`)
```bash
# Scrape starting 50 products in 3 seconds:
python3 universal_scraper.py --url "https://prekies.com" --limit 50

# Scrape starting 100 products:
python3 universal_scraper.py --url "https://www.boat-lifestyle.com" --limit 100
```

---

### 4. Scrape ANY Shopify Store & Sync to Google Sheets
```bash
python3 universal_scraper.py --url "https://musclemind.com" --sheet "https://docs.google.com/spreadsheets/d/1PLX9H5c3WA_vvM8HJQoK35ZHLBubLudHephx7T2lGjE/edit"
```

---

### 5. Run Master Daily Automated Pipeline
```bash
python3 daily_automation_master.py
```
*Executes exact inventory scraping across Cava, Musclemind, and Kosher Casual, saves daily timestamped snapshots in `daily_snapshots/YYYY-MM-DD/`, calculates units sold & estimated revenue, and syncs all tabs to Google Sheets.*

---

## ⚙️ Architecture & Multi-Tier Exact Stock Extraction Engines

`universal_scraper.py` implements a 5-tier hybrid stock extraction strategy:

1. **Tier 1: Embedded Cava JS Engine (`window.inventories`)**
   - Parses `window.inventories['product_id'][variant_id] = {'quantity': X}` embedded in theme scripts.
2. **Tier 2: Embedded Globo Preorder Engine (`window.GloboPreorderParams`)**
   - Parses Globo Preorder app variables `variants[i].inventory_quantity = Y`.
3. **Tier 3: Embedded GrowWave Engine (`window.gwProductInventoryQuantity`)**
   - Parses GrowWave app dictionary `window.gwProductInventoryQuantity[variant_id] = "Z"`.
4. **Tier 4: Multiline Script Block JSON Engine**
   - Scans DOM `<script>` blocks for JSON variant arrays containing `"inventory_quantity": N`.
5. **Tier 5: Paced Cart Add Probe Engine (`/cart/add.js`)**
   - Sends automated probes with `quantity: 999` to `/cart/add.js`. Parses status 422 error messages:
     `{"status":422,"message":"Only X items were added to your cart due to availability."}`

---

## ☁️ Automated Daily Schedule (Local & GitHub Actions)

- **Execution Time:** Daily at **1:55 PM IST**
- **GitHub Actions Workflow:** `.github/workflows/daily_scraper.yml` (Runs 100% in the cloud)
- **Local Mac Cron:** `55 13 * * * cd /Users/turbom/Desktop/Alan/SHOPIFY_SCRAP && /usr/local/bin/python3 daily_automation_master.py >> /Users/turbom/Desktop/Alan/SHOPIFY_SCRAP/daily_cron.log 2>&1`
