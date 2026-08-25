#!/usr/bin/env python3
"""
Unit Tests for Myntra Extractor
"""

import pytest
from backend.platforms.myntra import MyntraScraper

def test_myntra_can_handle():
    scraper = MyntraScraper()
    assert scraper.can_handle("https://www.myntra.com/tshirts/hrx-by-hrithik-roshan/hrx/1700944/buy") is True
    assert scraper.can_handle("https://amazon.in/dp/B08N5WRWNW") is False

def test_myntra_extract_style_code():
    scraper = MyntraScraper()
    url = "https://www.myntra.com/tshirts/hrx-by-hrithik-roshan/hrx-by-hrithik-roshan-men-yellow-printed-pure-cotton-t-shirt/1700944/buy"
    assert scraper.extract_style_code(url) == "1700944"

def test_myntra_real_product_scrape():
    scraper = MyntraScraper()
    url = "https://www.myntra.com/tshirts/hrx-by-hrithik-roshan/hrx-by-hrithik-roshan-men-yellow-printed-pure-cotton-t-shirt/1700944/buy"
    data = scraper.scrape_product(url)

    assert data["platform"] == "myntra"
    assert data["product_id"] == "1700944"
    assert data["style_code"] == "1700944"
    assert "HRX" in data["brand"]
    assert data["mrp"] == 699.0
    assert data["selling_price"] == 299.0
    assert data["discount_percent"] > 0
    assert len(data["variants"]) > 0
    assert data["exact_stock"] is not None and data["exact_stock"] > 0
    assert "window.__myx" in data["stock_source"]
