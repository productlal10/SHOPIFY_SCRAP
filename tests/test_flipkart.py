#!/usr/bin/env python3
"""
Unit Tests for Flipkart Extractor
"""

import pytest
from backend.platforms.flipkart import FlipkartScraper

def test_flipkart_can_handle():
    scraper = FlipkartScraper()
    assert scraper.can_handle("https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac2b8f956b4f") is True
    assert scraper.can_handle("https://amazon.in/dp/B08N5WRWNW") is False

def test_flipkart_extract_product_id():
    scraper = FlipkartScraper()
    url = "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac2b8f956b4f?pid=MOBGTAGPTRBZ2YGS"
    assert scraper.extract_product_id(url) == "MOBGTAGPTRBZ2YGS"

def test_flipkart_scrape_schema():
    scraper = FlipkartScraper()
    url = "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac2b8f956b4f"
    data = scraper.scrape_product(url)

    assert data["platform"] == "flipkart"
    assert data["currency"] == "INR"
    assert data["stock_source"] == "not_publicly_available"
    assert data["exact_stock"] is None
