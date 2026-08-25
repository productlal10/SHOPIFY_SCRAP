#!/usr/bin/env python3
"""
Myntra Modular Extractor
========================
Extracts product attributes, pricing, color/size variants, seller info, style codes,
and EXACT numeric inventory counts from Myntra's public hydration JSON state (`window.__myx`).
"""

import re
import json
import urllib.parse
from typing import Dict, Any, List

from backend.core.scraper_base import BaseScraper
from backend.core.http_client import fetch_url
from backend.core.normalizer import normalize_product_data

class MyntraScraper(BaseScraper):
    """Production Myntra product & inventory extractor."""

    @property
    def platform_name(self) -> str:
        return "myntra"

    def can_handle(self, url: str) -> bool:
        """Determines if URL belongs to Myntra."""
        parsed = urllib.parse.urlparse(url.lower())
        return "myntra.com" in parsed.netloc

    def extract_style_code(self, url: str) -> str:
        """Extract style code / product ID from Myntra URL."""
        parsed = urllib.parse.urlparse(url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        
        for part in reversed(path_parts):
            if part.isdigit():
                return part
            m = re.search(r'(\d{5,10})', part)
            if m:
                return m.group(1)
        return ""

    def scrape_product(self, url: str) -> Dict[str, Any]:
        """Scrape Myntra product URL and return normalized JSON data."""
        data = self.create_empty_normalized_schema(url)
        style_code = self.extract_style_code(url)
        data["style_code"] = style_code
        data["product_id"] = style_code

        r = fetch_url(url, timeout=15)
        if r.status_code != 200:
            return normalize_product_data(data)

        html = r.text
        m = re.search(r'window\.__myx\s*=\s*(\{.*?\});?</script>', html, re.DOTALL)
        if not m:
            m = re.search(r'window\.__myx\s*=\s*(\{.*?\});', html, re.DOTALL)

        if not m:
            return normalize_product_data(data)

        try:
            myx_data = json.loads(m.group(1))
            pdp = myx_data.get("pdpData", {})
        except Exception:
            return normalize_product_data(data)

        if not pdp:
            return normalize_product_data(data)

        # Core Metadata
        data["product_id"] = str(pdp.get("id", style_code))
        data["style_code"] = str(pdp.get("id", style_code))
        data["product_name"] = pdp.get("name", "")
        
        brand_info = pdp.get("brand", {})
        data["brand"] = brand_info.get("name", "") if isinstance(brand_info, dict) else str(brand_info)
        
        analytics = pdp.get("analytics", {})
        data["category"] = analytics.get("articleType", pdp.get("landingPageUrl", ""))

        # Description
        desc_list = pdp.get("productDetails", [])
        desc_lines = []
        for item in desc_list:
            if isinstance(item, dict):
                title = item.get("title", "")
                val = item.get("description", "")
                if title or val:
                    desc_lines.append(f"{title}: {val}".strip(": "))
        data["description"] = "\n".join(desc_lines)

        # Images
        media = pdp.get("media", {})
        albums = media.get("albums", [])
        imgs = []
        for album in albums:
            for img_obj in album.get("images", []):
                src = img_obj.get("src") or img_obj.get("imageURL")
                if src:
                    imgs.append(src)
        data["images"] = imgs

        # Base Pricing
        price_info = pdp.get("price", {})
        if isinstance(price_info, dict):
            data["mrp"] = price_info.get("mrp")
            data["selling_price"] = price_info.get("discounted") or price_info.get("mrp")
        else:
            data["mrp"] = pdp.get("mrp")
            data["selling_price"] = pdp.get("mrp")

        # Color
        base_color = pdp.get("baseColour", "")

        # Sizes & Exact Inventory Breakdown
        raw_sizes = pdp.get("sizes", [])
        variants_list = []
        total_product_stock = 0
        has_exact_stock = False

        sellers_set = set()

        for s in raw_sizes:
            size_label = s.get("label") or s.get("name", "")
            sku_id = str(s.get("skuId", ""))
            avail = bool(s.get("available", False))

            seller_data = s.get("sizeSellerData", [])
            var_stock = 0
            var_mrp = None
            var_selling = None

            if seller_data:
                for sel in seller_data:
                    if isinstance(sel, dict):
                        # Accumulate inventory across all sellers for this size
                        sel_count = sel.get("sellableInventoryCount") or sel.get("availableCount")
                        if sel_count is not None:
                            var_stock += int(sel_count)
                            has_exact_stock = True
                        
                        if sel.get("mrp"):
                            var_mrp = sel.get("mrp")
                        if sel.get("discountedPrice"):
                            var_selling = sel.get("discountedPrice")
                        
                        sel_id = sel.get("sellerPartnerId")
                        if sel_id:
                            sellers_set.add(str(sel_id))

            if not has_exact_stock:
                var_exact = None
                var_src = "not_publicly_available"
            else:
                var_exact = var_stock
                var_src = "window.__myx.pdpData.sizes.sizeSellerData"
                total_product_stock += var_stock

            v_dict = {
                "variant_id": sku_id if sku_id else f"{style_code}_{size_label}",
                "sku": sku_id,
                "color": base_color,
                "size": size_label,
                "attributes": {"color": base_color, "size": size_label},
                "mrp": var_mrp or data["mrp"],
                "selling_price": var_selling or data["selling_price"],
                "available": avail and (var_exact is None or var_exact > 0),
                "stock_status": "IN_STOCK" if avail and (var_exact is None or var_exact > 0) else "OUT_OF_STOCK",
                "exact_stock": var_exact,
                "stock_source": var_src
            }
            variants_list.append(v_dict)

        data["variants"] = variants_list
        data["available"] = any(v["available"] for v in variants_list) if variants_list else bool(pdp.get("flags", {}).get("buyButtonEnabled", True))
        
        if sellers_set:
            data["seller"] = f"Myntra Seller Partners: {', '.join(sorted(sellers_set))}"
        else:
            data["seller"] = "Myntra Authorized Seller"

        if has_exact_stock:
            data["exact_stock"] = total_product_stock
            data["stock_source"] = "window.__myx.pdpData.sizes.sizeSellerData"
        else:
            data["exact_stock"] = None
            data["stock_source"] = "not_publicly_available"

        return normalize_product_data(data)
