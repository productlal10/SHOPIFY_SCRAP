#!/usr/bin/env python3
"""
Unit Tests for Amazon India Extractor
"""

import pytest
from backend.platforms.amazon import AmazonScraper

def test_amazon_can_handle():
    scraper = AmazonScraper()
    assert scraper.can_handle("https://www.amazon.in/dp/B0CHX1W1XY") is True
    assert scraper.can_handle("https://www.myntra.com/tshirts/123") is False

def test_amazon_extract_asin():
    scraper = AmazonScraper()
    url = "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY"
    assert scraper.extract_asin(url) == "B0CHX1W1XY"

def test_amazon_real_product_scrape():
    scraper = AmazonScraper()
    url = "https://www.amazon.in/dp/B0CHX1W1XY"
    data = scraper.scrape_product(url)

    assert data["platform"] == "amazon"
    assert data["asin"] == "B0CHX1W1XY"
    assert data["currency"] == "INR"
    assert "stock_source" in data
