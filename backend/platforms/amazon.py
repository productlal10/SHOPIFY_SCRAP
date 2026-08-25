#!/usr/bin/env python3
"""
Amazon India Modular Extractor
==============================
Extracts product attributes, ASIN, pricing, MRP, discount percentage, seller info,
images, color/size variants, and availability status from Amazon India product pages.
"""

import re
import json
import urllib.parse
from typing import Dict, Any, List
from bs4 import BeautifulSoup
import requests

from backend.core.scraper_base import BaseScraper
from backend.core.normalizer import normalize_product_data

AMAZON_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
}

class AmazonScraper(BaseScraper):
    """Production Amazon India product & inventory extractor."""

    @property
    def platform_name(self) -> str:
        return "amazon"

    def can_handle(self, url: str) -> bool:
        """Determines if URL belongs to Amazon India or Amazon."""
        parsed = urllib.parse.urlparse(url.lower())
        return "amazon.in" in parsed.netloc or "amazon.com" in parsed.netloc

    def extract_asin(self, url: str) -> str:
        """Extract 10-character ASIN from Amazon product URL."""
        parsed = urllib.parse.urlparse(url)
        m = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', parsed.path)
        if m:
            return m.group(1)
        m_query = re.search(r'([A-Z0-9]{10})', parsed.path)
        if m_query:
            return m_query.group(1)
        return ""

    def scrape_product(self, url: str) -> Dict[str, Any]:
        """Scrape Amazon India product URL and return normalized JSON data."""
        data = self.create_empty_normalized_schema(url)
        asin = self.extract_asin(url)
        data["asin"] = asin
        data["product_id"] = asin or url
        
        session = requests.Session()

        try:
            # 1. Obtain session cookies from Amazon India home
            session.get("https://www.amazon.in", headers=AMAZON_HEADERS, timeout=8)

            # 2. Fetch product page
            r = session.get(url, headers=AMAZON_HEADERS, timeout=12)
            if r.status_code != 200:
                return normalize_product_data(data)

            html = r.text
            if "captcha" in html.lower():
                data["stock_status"] = "UNKNOWN"
                data["stock_source"] = "not_publicly_available"
                return normalize_product_data(data)

            soup = BeautifulSoup(html, "html.parser")

            # Extract Title
            title_el = soup.find("span", id="productTitle")
            if title_el:
                data["product_name"] = title_el.text.strip()

            # Extract Brand
            brand_el = soup.find("a", id="bylineInfo") or soup.find("tr", {"class": "po-brand"})
            if brand_el:
                brand_str = brand_el.text.strip()
                brand_clean = re.sub(r'^(Visit the|Brand:|\s+)*', '', brand_str, flags=re.IGNORECASE)
                brand_clean = re.sub(r'\s+Store$', '', brand_clean, flags=re.IGNORECASE)
                data["brand"] = brand_clean.strip()

            # Extract Selling Price
            price_whole = soup.find("span", {"class": "a-price-whole"})
            if price_whole:
                price_text = re.sub(r"[^\d.]", "", price_whole.text.split(".")[0])
                if price_text:
                    data["selling_price"] = float(price_text)

            if not data.get("selling_price"):
                price_off = soup.find("span", id=re.compile(r"priceblock_|price"))
                if price_off:
                    p_text = re.sub(r"[^\d.]", "", price_off.text)
                    if p_text:
                        data["selling_price"] = float(p_text)

            # Extract MRP / List Price
            mrp_el = soup.find("span", {"class": re.compile(r"a-text-price")})
            if mrp_el:
                mrp_off = mrp_el.find("span", {"class": "a-offscreen"})
                if mrp_off:
                    mrp_text = re.sub(r"[^\d.]", "", mrp_off.text)
                    if mrp_text:
                        data["mrp"] = float(mrp_text)

            if not data.get("mrp") and data.get("selling_price"):
                data["mrp"] = data["selling_price"]

            # Extract Images
            imgs = []
            m_img = re.search(r'colorImages[\"\']?\s*:\s*(\{.*?\})\s*,', html, re.DOTALL)
            if m_img:
                try:
                    img_data = json.loads(m_img.group(1))
                    for category in img_data.values():
                        if isinstance(category, list):
                            for item in category:
                                if isinstance(item, dict) and "hiRes" in item and item["hiRes"]:
                                    imgs.append(item["hiRes"])
                                elif isinstance(item, dict) and "large" in item and item["large"]:
                                    imgs.append(item["large"])
                except Exception:
                    pass

            if not imgs:
                main_img = soup.find("img", id="landingImage")
                if main_img and main_img.get("src"):
                    imgs.append(main_img.get("src"))

            data["images"] = list(set(imgs))

            # Seller / Merchant
            merchant_el = soup.find("div", id="merchant-info") or soup.find("a", id="sellerProfileTriggerId")
            if merchant_el:
                data["seller"] = merchant_el.text.strip()

            # Availability & Stock Status
            avail_el = soup.find("div", id="availability")
            avail_text = avail_el.text.strip().lower() if avail_el else ""

            if "currently unavailable" in avail_text or "out of stock" in avail_text:
                data["available"] = False
                data["stock_status"] = "OUT_OF_STOCK"
                data["exact_stock"] = 0
                data["stock_source"] = "amazon_availability_text"
            else:
                data["available"] = True
                data["stock_status"] = "IN_STOCK"
                
                m_stock = re.search(r'only\s+(\d+)\s+left\s+in\s+stock', avail_text)
                if m_stock:
                    data["exact_stock"] = int(m_stock.group(1))
                    data["stock_source"] = "amazon_public_availability_text"
                else:
                    data["exact_stock"] = None
                    data["stock_source"] = "not_publicly_available"

        except Exception:
            pass

        return normalize_product_data(data)
