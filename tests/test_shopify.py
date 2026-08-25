#!/usr/bin/env python3
"""
Unit Tests for Shopify Extractor & Core Normalizer
"""

import pytest
from backend.platforms.shopify import ShopifyScraper
from backend.core.normalizer import normalize_product_data, calculate_discount

def test_can_handle_shopify_urls():
    scraper = ShopifyScraper()
    assert scraper.can_handle("https://cavaathleisure.com/products/brown-hourglass-booty-shorts") is True
    assert scraper.can_handle("https://musclemind.com/products/oversized-tee") is True
    assert scraper.can_handle("https://myntra.com/tshirts/brand/12345") is False

def test_calculate_discount():
    assert calculate_discount(1000, 750) == 25.0
    assert calculate_discount(2000, 1000) == 50.0
    assert calculate_discount(100, 100) == 0.0

def test_shopify_real_product_scrape():
    scraper = ShopifyScraper()
    url = "https://cavaathleisure.com/products/brown-hourglass-booty-shorts"
    data = scraper.scrape_product(url)

    assert data["platform"] == "shopify"
    assert "Brown Hourglass Booty Shorts" in data["product_name"]
    assert data["product_url"] == url
    assert data["selling_price"] > 0
    assert len(data["variants"]) > 0
    assert data["variants"][0]["size"] is not None
