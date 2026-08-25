#!/usr/bin/env python3
"""
Flipkart Modular Extractor
==========================
Extracts product attributes, pricing, MRP, discount percentage, seller info,
and variant availability from Flipkart product pages.
"""

import re
import json
import urllib.parse
from typing import Dict, Any, List
from bs4 import BeautifulSoup

from backend.core.scraper_base import BaseScraper
from backend.core.http_client import get_http_session
from backend.core.normalizer import normalize_product_data

FLIPKART_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}

class FlipkartScraper(BaseScraper):
    """Production Flipkart product & inventory extractor."""

    @property
    def platform_name(self) -> str:
        return "flipkart"

    def can_handle(self, url: str) -> bool:
        """Determines if URL belongs to Flipkart."""
        parsed = urllib.parse.urlparse(url.lower())
        return "flipkart.com" in parsed.netloc

    def extract_product_id(self, url: str) -> str:
        """Extract Flipkart PID from URL path or query params."""
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        if "pid" in query:
            return query["pid"][0]
        m = re.search(r'/p/(itm[a-zA-Z0-9]+)', parsed.path)
        if m:
            return m.group(1)
        return ""

    def scrape_product(self, url: str) -> Dict[str, Any]:
        """Scrape Flipkart product URL and return normalized JSON data."""
        data = self.create_empty_normalized_schema(url)
        pid = self.extract_product_id(url)
        data["product_id"] = pid
        session = get_http_session()

        try:
            r = session.get(url, headers=FLIPKART_HEADERS, timeout=12)
            if r.status_code != 200:
                return normalize_product_data(data)

            html = r.text
            if "Are you a human?" in html or "captcha" in html.lower():
                data["stock_status"] = "UNKNOWN"
                data["stock_source"] = "not_publicly_available"
                return normalize_product_data(data)

            soup = BeautifulSoup(html, "html.parser")

            # Extract Title
            title_el = (
                soup.find("span", {"class": re.compile(r"B_NuOD|VU-LmN|_35KyFi")}) or 
                soup.find("h1")
            )
            if title_el:
                data["product_name"] = title_el.text.strip()
                # Brand extraction heuristic
                words = data["product_name"].split()
                if words:
                    data["brand"] = words[0]

            # Extract Price
            price_el = soup.find("div", {"class": re.compile(r"_30jeq3|_16Jk6d")})
            if price_el:
                price_text = re.sub(r"[^\d.]", "", price_el.text)
                if price_text:
                    data["selling_price"] = float(price_text)

            # Extract MRP
            mrp_el = soup.find("div", {"class": re.compile(r"_3I9_wc|_2yty84")})
            if mrp_el:
                mrp_text = re.sub(r"[^\d.]", "", mrp_el.text)
                if mrp_text:
                    data["mrp"] = float(mrp_text)

            if not data.get("mrp") and data.get("selling_price"):
                data["mrp"] = data["selling_price"]

            # Extract Images
            imgs = [img.get("src") for img in soup.find_all("img", src=re.compile(r"flipkart\.com/image")) if img.get("src")]
            data["images"] = list(set(imgs))

            # Seller
            seller_el = soup.find("div", id="sellerName") or soup.find("span", {"class": re.compile(r"_1RLif")})
            if seller_el:
                data["seller"] = seller_el.text.replace("Seller", "").strip()

            # Stock Availability Status
            out_of_stock_el = soup.find("div", {"class": re.compile(r"_16P22y|_1KAQL")})
            if out_of_stock_el and "sold out" in out_of_stock_el.text.lower():
                data["available"] = False
                data["stock_status"] = "OUT_OF_STOCK"
            else:
                data["available"] = True
                data["stock_status"] = "IN_STOCK"

            data["exact_stock"] = None
            data["stock_source"] = "not_publicly_available"

        except Exception:
            pass

        return normalize_product_data(data)
