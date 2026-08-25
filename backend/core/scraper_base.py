#!/usr/bin/env python3
"""
Abstract Base Scraper Interface
================================
Defines the required contract and standard output structure for all platform extractors
(Shopify, Myntra, Flipkart, Amazon).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

class BaseScraper(ABC):
    """Abstract Base Class for platform specific product data & inventory extractors."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Returns the identifier name of the platform (e.g. 'shopify', 'myntra', 'flipkart', 'amazon')."""
        pass

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Determines if this extractor can handle the given URL."""
        pass

    @abstractmethod
    def scrape_product(self, url: str) -> Dict[str, Any]:
        """
        Scrapes a single product URL and returns the unified normalized JSON dictionary.
        Must return structure matching the Unified Data Format.
        """
        pass

    def create_empty_normalized_schema(self, url: str) -> Dict[str, Any]:
        """Returns a baseline normalized dictionary schema initialized with null defaults."""
        now_iso = datetime.utcnow().isoformat() + "Z"
        return {
            "platform": self.platform_name,
            "product_id": "",
            "asin": None,
            "sku": None,
            "style_code": None,

            "product_name": "",
            "brand": "",
            "category": "",
            "description": "",

            "product_url": url,
            "images": [],

            "seller": None,
            "vendor": None,

            "mrp": None,
            "selling_price": None,
            "discount_percent": None,
            "currency": "INR",

            "available": False,
            "stock_status": "UNKNOWN",
            "exact_stock": None,
            "stock_source": "not_publicly_available",

            "variants": [],

            "first_seen_at": now_iso,
            "last_checked_at": now_iso
        }
