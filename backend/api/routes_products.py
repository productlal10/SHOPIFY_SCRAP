#!/usr/bin/env python3
"""
FastAPI Products & Scraping Endpoints
======================================
Provides REST API endpoints for scraping single/bulk product URLs, querying product catalogs,
inspecting price/stock history, and downloading CSV/Excel exports.
"""

import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from backend.database.connection import get_db, init_db
from backend.database.models import Product, Variant, PriceHistory, AvailabilityHistory, ScrapeRun
from backend.platforms.shopify import ShopifyScraper
from backend.platforms.myntra import MyntraScraper
from backend.platforms.flipkart import FlipkartScraper
from backend.platforms.amazon import AmazonScraper
from backend.services.product_service import save_scraped_product, record_scrape_run
from backend.export.excel_exporter import generate_excel_export
from backend.export.csv_exporter import generate_csv_export

router = APIRouter(prefix="/api/v1", tags=["Products & Scraping"])

# Register Available Extractors
EXTRACTORS = [
    ShopifyScraper(),
    MyntraScraper(),
    FlipkartScraper(),
    AmazonScraper()
]

def get_extractor_for_url(url: str):
    """Find matching platform extractor for URL."""
    for extractor in EXTRACTORS:
        if extractor.can_handle(url):
            return extractor
    return None

# Pydantic Request Models
class ScrapeRequest(BaseModel):
    url: str

class BulkScrapeRequest(BaseModel):
    urls: List[str]

@router.post("/products/scrape")
def scrape_single_product(payload: ScrapeRequest, db: Session = Depends(get_db)):
    """Scrape a single product URL and save to database."""
    url = payload.url.strip()
    extractor = get_extractor_for_url(url)
    
    if not extractor:
        raise HTTPException(status_code=400, detail=f"No extractor registered for URL domain: {url}")

    start_time = time.time()
    try:
        data = extractor.scrape_product(url)
        product = save_scraped_product(db, data)
        duration_ms = int((time.time() - start_time) * 1000)
        record_scrape_run(db, url, extractor.platform_name, "SUCCESS", duration_ms)
        return {"status": "success", "platform": extractor.platform_name, "data": data}
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        record_scrape_run(db, url, extractor.platform_name if extractor else "unknown", "FAILED", duration_ms, str(e))
        raise HTTPException(status_code=500, detail=f"Scrape failed: {str(e)}")

@router.post("/products/bulk-scrape")
def bulk_scrape_products(payload: BulkScrapeRequest, db: Session = Depends(get_db)):
    """Bulk scrape multiple product URLs."""
    results = []
    for url in payload.urls:
        url_clean = url.strip()
        extractor = get_extractor_for_url(url_clean)
        if not extractor:
            results.append({"url": url_clean, "status": "failed", "error": "Unsupported platform"})
            continue

        start_time = time.time()
        try:
            data = extractor.scrape_product(url_clean)
            product = save_scraped_product(db, data)
            duration_ms = int((time.time() - start_time) * 1000)
            record_scrape_run(db, url_clean, extractor.platform_name, "SUCCESS", duration_ms)
            results.append({"url": url_clean, "status": "success", "data": data})
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            record_scrape_run(db, url_clean, extractor.platform_name, "FAILED", duration_ms, str(e))
            results.append({"url": url_clean, "status": "failed", "error": str(e)})

    return {"status": "completed", "total": len(payload.urls), "results": results}

@router.get("/products")
def list_products(
    platform: Optional[str] = None,
    brand: Optional[str] = None,
    available: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Retrieve catalog products with filtering, search, and pagination."""
    query = db.query(Product)
    if platform:
        query = query.filter(Product.platform == platform.lower())
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))
    if available is not None:
        query = query.filter(Product.available == available)
    if search:
        query = query.filter(Product.product_name.ilike(f"%{search}%"))

    total = query.count()
    products = query.offset(offset).limit(limit).all()

    return {"total": total, "limit": limit, "offset": offset, "products": products}

@router.get("/products/{product_id}")
def get_product_details(product_id: str, db: Session = Depends(get_db)):
    """Get single product details with variants."""
    product = db.query(Product).filter((Product.id == product_id) | (Product.product_id == product_id)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/products/{product_id}/history")
def get_product_history(product_id: str, db: Session = Depends(get_db)):
    """Get price and availability change history for a product."""
    product = db.query(Product).filter((Product.id == product_id) | (Product.product_id == product_id)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    prices = db.query(PriceHistory).filter(PriceHistory.product_id == product.id).order_by(PriceHistory.recorded_at.desc()).all()
    availability = db.query(AvailabilityHistory).filter(AvailabilityHistory.product_id == product.id).order_by(AvailabilityHistory.recorded_at.desc()).all()

    return {
        "product_id": product.id,
        "product_name": product.product_name,
        "price_history": prices,
        "availability_history": availability
    }

@router.get("/export/excel")
def export_excel_file(db: Session = Depends(get_db)):
    """Download entire monitored catalog as an Excel (.xlsx) file."""
    products = db.query(Product).all()
    
    # Format list of dicts for exporter
    data_list = []
    for p in products:
        p_dict = {
            "platform": p.platform,
            "product_id": p.product_id,
            "asin": p.asin,
            "sku": p.sku,
            "style_code": p.style_code,
            "product_name": p.product_name,
            "brand": p.brand,
            "category": p.category,
            "description": p.description,
            "product_url": p.product_url,
            "images": p.images,
            "seller": p.seller,
            "vendor": p.vendor,
            "mrp": float(p.mrp) if p.mrp else None,
            "selling_price": float(p.selling_price) if p.selling_price else None,
            "discount_percent": float(p.discount_percent) if p.discount_percent else 0.0,
            "currency": p.currency,
            "available": p.available,
            "stock_status": p.stock_status,
            "exact_stock": p.exact_stock,
            "stock_source": p.stock_source,
            "last_checked_at": p.last_checked_at.isoformat() if p.last_checked_at else "",
            "variants": [
                {
                    "variant_id": v.variant_id,
                    "sku": v.sku,
                    "color": v.color,
                    "size": v.size,
                    "mrp": float(v.mrp) if v.mrp else None,
                    "selling_price": float(v.selling_price) if v.selling_price else None,
                    "available": v.available,
                    "stock_status": v.stock_status,
                    "exact_stock": v.exact_stock,
                    "stock_source": v.stock_source
                } for v in p.variants
            ]
        }
        data_list.append(p_dict)

    excel_bytes = generate_excel_export(data_list)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ecommerce_catalog_export.xlsx"}
    )

@router.get("/export/csv")
def export_csv_file(db: Session = Depends(get_db)):
    """Download entire monitored catalog as a CSV file."""
    products = db.query(Product).all()
    data_list = []
    for p in products:
        p_dict = {
            "platform": p.platform,
            "product_id": p.product_id,
            "asin": p.asin,
            "sku": p.sku,
            "style_code": p.style_code,
            "product_name": p.product_name,
            "brand": p.brand,
            "category": p.category,
            "description": p.description,
            "product_url": p.product_url,
            "images": p.images,
            "seller": p.seller,
            "vendor": p.vendor,
            "mrp": float(p.mrp) if p.mrp else None,
            "selling_price": float(p.selling_price) if p.selling_price else None,
            "discount_percent": float(p.discount_percent) if p.discount_percent else 0.0,
            "currency": p.currency,
            "available": p.available,
            "stock_status": p.stock_status,
            "exact_stock": p.exact_stock,
            "stock_source": p.stock_source,
            "last_checked_at": p.last_checked_at.isoformat() if p.last_checked_at else "",
            "variants": [
                {
                    "variant_id": v.variant_id,
                    "sku": v.sku,
                    "color": v.color,
                    "size": v.size,
                    "mrp": float(v.mrp) if v.mrp else None,
                    "selling_price": float(v.selling_price) if v.selling_price else None,
                    "available": v.available,
                    "stock_status": v.stock_status,
                    "exact_stock": v.exact_stock,
                    "stock_source": v.stock_source
                } for v in p.variants
            ]
        }
        data_list.append(p_dict)

    csv_text = generate_csv_export(data_list)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ecommerce_catalog_export.csv"}
    )
