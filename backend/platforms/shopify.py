#!/usr/bin/env python3
"""
Shopify Modular Extractor
=========================
Extracts product attributes, pricing, variants, and EXACT inventory quantities
for ANY Shopify storefront using multi-tier hybrid detection logic.
"""

import re
import json
import urllib.parse
from typing import Dict, Any, List

from backend.core.scraper_base import BaseScraper
from backend.core.http_client import get_http_session
from backend.core.normalizer import normalize_product_data

class ShopifyScraper(BaseScraper):
    """Production Shopify product & inventory extractor."""

    @property
    def platform_name(self) -> str:
        return "shopify"

    def can_handle(self, url: str) -> bool:
        """Determines if URL belongs to a Shopify store or product page."""
        parsed = urllib.parse.urlparse(url.lower())
        return "/products/" in parsed.path or "myshopify.com" in parsed.netloc

    def clean_base_url(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def extract_product_handle(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        if "products" in path_parts:
            idx = path_parts.index("products")
            if idx + 1 < len(path_parts):
                return path_parts[idx + 1]
        return path_parts[-1] if path_parts else ""

    def probe_cart_add_exact_stock(self, base_url: str, v_id: int) -> int:
        """Probe /cart/add.js endpoint to extract exact available stock count."""
        session = get_http_session()
        url = f"{base_url}/cart/add.js"
        payload = {"items": [{"id": int(v_id), "quantity": 999}]}

        try:
            r = session.post(url, json=payload, timeout=8)
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

    def parse_hybrid_stock_from_html(self, html: str) -> tuple[dict, str]:
        """Extract variant stock map and source tier from page HTML."""
        stock_dict = {}

        # Tier 1: Cava pattern (window.inventories)
        if "window.inventories" in html:
            matches = re.findall(r"window\.inventories\['\d+'\]\[(\d+)\]\s*=\s*\{\s*'quantity':\s*(-?\d+)", html)
            if matches:
                return {int(v_id): int(qty) for v_id, qty in matches}, "window.inventories"

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
                return stock_dict, "GloboPreorderParams"

        # Tier 3: GrowWave gwProductInventoryQuantity pattern (Kosher Casual)
        if "gwProductInventoryQuantity" in html:
            gw_matches = re.findall(r'window\.gwProductInventoryQuantity\[(\d+)\]\s*=\s*\"?(-?\d+)\"?;', html)
            if gw_matches:
                return {int(v_id): int(qty) for v_id, qty in gw_matches}, "gwProductInventoryQuantity"

        # Tier 4: Multiline Script Block JSON Engine
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
                return stock_dict, "script_json_hydration"

        return {}, "not_publicly_available"

    def scrape_product(self, url: str) -> Dict[str, Any]:
        """Scrape Shopify product URL and return normalized data schema."""
        base_url = self.clean_base_url(url)
        handle = self.extract_product_handle(url)
        session = get_http_session()

        data = self.create_empty_normalized_schema(url)

        # 1. Fetch Shopify Product JSON API
        json_url = f"{base_url}/products/{handle}.js"
        r_json = session.get(json_url, timeout=12)

        prod_json = {}
        if r_json.status_code == 200:
            try:
                prod_json = r_json.json()
            except Exception:
                pass

        # 2. Fetch HTML for exact stock extraction
        html_url = f"{base_url}/products/{handle}"
        r_html = session.get(html_url, timeout=12)
        html_text = r_html.text if r_html.status_code == 200 else ""

        stock_map, stock_src = self.parse_hybrid_stock_from_html(html_text)

        # Populate basic details
        if prod_json:
            data["product_id"] = str(prod_json.get("id", ""))
            data["product_name"] = prod_json.get("title", "")
            data["brand"] = prod_json.get("vendor", "")
            data["vendor"] = prod_json.get("vendor", "")
            data["seller"] = prod_json.get("vendor", "")
            data["category"] = prod_json.get("type", "")
            data["description"] = prod_json.get("description", "")
            
            images = prod_json.get("images", [])
            if images:
                data["images"] = ["https:" + img if img.startswith("//") else img for img in images]

            price_cents = prod_json.get("price", 0)
            data["selling_price"] = round(price_cents / 100.0, 2) if price_cents else 0.0
            
            cmp_price = prod_json.get("compare_at_price")
            data["mrp"] = round(cmp_price / 100.0, 2) if cmp_price else data["selling_price"]

            # Variants
            variants_list = []
            options = prod_json.get("options", [])
            
            for v in prod_json.get("variants", []):
                v_id = v.get("id")
                v_title = v.get("title", "")
                v_price = round(v.get("price", 0) / 100.0, 2)
                v_cmp = v.get("compare_at_price")
                v_mrp = round(v_cmp / 100.0, 2) if v_cmp else v_price
                v_avail = v.get("available", False)
                v_sku = v.get("sku", "")

                # Size / Color option parsing
                color = None
                size = None
                attrs = {}
                for idx, opt in enumerate(options):
                    opt_name = opt.get("name", "").lower()
                    opt_val = v.get(f"option{idx+1}")
                    if opt_val:
                        attrs[opt_name] = opt_val
                        if "size" in opt_name:
                            size = opt_val
                        elif "color" in opt_name or "colour" in opt_name:
                            color = opt_val

                if not size and v_title != "Default Title":
                    size = v_title

                # Stock extraction calculation
                if v_id in stock_map:
                    v_qty = stock_map[v_id]
                    v_src = stock_src
                elif v_avail:
                    cart_qty = self.probe_cart_add_exact_stock(base_url, v_id)
                    if cart_qty is not None:
                        v_qty = cart_qty
                        v_src = "cart_probe"
                    else:
                        v_qty = None
                        v_src = "not_publicly_available"
                else:
                    v_qty = 0
                    v_src = stock_src if stock_src != "not_publicly_available" else "product_state"

                variant_dict = {
                    "variant_id": str(v_id),
                    "sku": v_sku,
                    "color": color,
                    "size": size,
                    "attributes": attrs,
                    "mrp": v_mrp,
                    "selling_price": v_price,
                    "available": v_avail and (v_qty is None or v_qty > 0),
                    "stock_status": "IN_STOCK" if v_avail and (v_qty is None or v_qty > 0) else "OUT_OF_STOCK",
                    "exact_stock": v_qty,
                    "stock_source": v_src
                }
                variants_list.append(variant_dict)

            data["variants"] = variants_list
            data["stock_source"] = stock_src if stock_map else ("cart_probe" if any(v["stock_source"] == "cart_probe" for v in variants_list) else "not_publicly_available")
            
            # Aggregate product level exact stock
            exact_quantities = [v["exact_stock"] for v in variants_list if v["exact_stock"] is not None]
            if exact_quantities:
                data["exact_stock"] = sum(exact_quantities)

        return normalize_product_data(data)
