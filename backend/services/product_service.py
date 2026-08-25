#!/usr/bin/env python3
"""
Product Service
===============
Handles upserting normalized product payloads into the database, managing variant updates,
and triggering price and availability history delta recordings.
"""

from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from backend.database.models import Product, Variant, PriceHistory, AvailabilityHistory, ScrapeRun

def save_scraped_product(db: Session, data: Dict[str, Any]) -> Product:
    """Upserts normalized product dictionary into database and records price/stock history deltas."""
    url = data.get("product_url")
    platform = data.get("platform")
    product_id_val = data.get("product_id")

    # Search existing product by URL or (platform + product_id)
    product = db.query(Product).filter(
        (Product.product_url == url) | 
        ((Product.platform == platform) & (Product.product_id == product_id_val))
    ).first()

    now = datetime.utcnow()

    if not product:
        product = Product(
            platform=platform,
            product_id=product_id_val,
            asin=data.get("asin"),
            sku=data.get("sku"),
            style_code=data.get("style_code"),
            product_name=data.get("product_name"),
            brand=data.get("brand"),
            category=data.get("category"),
            description=data.get("description"),
            product_url=url,
            images=data.get("images", []),
            seller=data.get("seller"),
            vendor=data.get("vendor"),
            mrp=data.get("mrp"),
            selling_price=data.get("selling_price"),
            discount_percent=data.get("discount_percent"),
            currency=data.get("currency", "INR"),
            available=data.get("available", False),
            stock_status=data.get("stock_status", "UNKNOWN"),
            exact_stock=data.get("exact_stock"),
            stock_source=data.get("stock_source", "not_publicly_available"),
            first_seen_at=now,
            last_checked_at=now
        )
        db.add(product)
        db.flush()
    else:
        # Check product level price delta
        if product.selling_price != data.get("selling_price") or product.mrp != data.get("mrp"):
            price_delta = PriceHistory(
                product_id=product.id,
                variant_id=None,
                old_price=product.selling_price or 0,
                new_price=data.get("selling_price") or 0,
                old_mrp=product.mrp,
                new_mrp=data.get("mrp"),
                recorded_at=now
            )
            db.add(price_delta)

        # Check product level availability delta
        if product.available != data.get("available") or product.exact_stock != data.get("exact_stock"):
            avail_delta = AvailabilityHistory(
                product_id=product.id,
                variant_id=None,
                old_available=product.available,
                new_available=data.get("available", False),
                old_exact_stock=product.exact_stock,
                new_exact_stock=data.get("exact_stock"),
                recorded_at=now
            )
            db.add(avail_delta)

        # Update product fields
        product.product_name = data.get("product_name", product.product_name)
        product.brand = data.get("brand", product.brand)
        product.category = data.get("category", product.category)
        product.description = data.get("description", product.description)
        product.images = data.get("images", product.images)
        product.seller = data.get("seller", product.seller)
        product.vendor = data.get("vendor", product.vendor)
        product.mrp = data.get("mrp", product.mrp)
        product.selling_price = data.get("selling_price", product.selling_price)
        product.discount_percent = data.get("discount_percent", product.discount_percent)
        product.available = data.get("available", product.available)
        product.stock_status = data.get("stock_status", product.stock_status)
        product.exact_stock = data.get("exact_stock", product.exact_stock)
        product.stock_source = data.get("stock_source", product.stock_source)
        product.last_checked_at = now

    # Process Variants
    for v_data in data.get("variants", []):
        v_id_val = str(v_data.get("variant_id"))
        variant = db.query(Variant).filter(
            Variant.product_id == product.id,
            Variant.variant_id == v_id_val
        ).first()

        if not variant:
            variant = Variant(
                product_id=product.id,
                variant_id=v_id_val,
                sku=v_data.get("sku"),
                color=v_data.get("color"),
                size=v_data.get("size"),
                attributes=v_data.get("attributes", {}),
                mrp=v_data.get("mrp"),
                selling_price=v_data.get("selling_price"),
                available=v_data.get("available", False),
                stock_status=v_data.get("stock_status", "UNKNOWN"),
                exact_stock=v_data.get("exact_stock"),
                stock_source=v_data.get("stock_source", "")
            )
            db.add(variant)
            db.flush()
        else:
            # Check variant price delta
            if variant.selling_price != v_data.get("selling_price") or variant.mrp != v_data.get("mrp"):
                v_price_delta = PriceHistory(
                    product_id=product.id,
                    variant_id=variant.id,
                    old_price=variant.selling_price or 0,
                    new_price=v_data.get("selling_price") or 0,
                    old_mrp=variant.mrp,
                    new_mrp=v_data.get("mrp"),
                    recorded_at=now
                )
                db.add(v_price_delta)

            # Check variant availability delta
            if variant.available != v_data.get("available") or variant.exact_stock != v_data.get("exact_stock"):
                v_avail_delta = AvailabilityHistory(
                    product_id=product.id,
                    variant_id=variant.id,
                    old_available=variant.available,
                    new_available=v_data.get("available", False),
                    old_exact_stock=variant.exact_stock,
                    new_exact_stock=v_data.get("exact_stock"),
                    recorded_at=now
                )
                db.add(v_avail_delta)

            # Update variant fields
            variant.sku = v_data.get("sku", variant.sku)
            variant.color = v_data.get("color", variant.color)
            variant.size = v_data.get("size", variant.size)
            variant.attributes = v_data.get("attributes", variant.attributes)
            variant.mrp = v_data.get("mrp", variant.mrp)
            variant.selling_price = v_data.get("selling_price", variant.selling_price)
            variant.available = v_data.get("available", variant.available)
            variant.stock_status = v_data.get("stock_status", variant.stock_status)
            variant.exact_stock = v_data.get("exact_stock", variant.exact_stock)
            variant.stock_source = v_data.get("stock_source", variant.stock_source)

    db.commit()
    db.refresh(product)
    return product

def record_scrape_run(db: Session, url: str, platform: str, status: str, duration_ms: int, error_msg: str = None):
    run = ScrapeRun(
        url=url,
        platform=platform,
        status=status,
        duration_ms=duration_ms,
        error_message=error_msg,
        scraped_at=datetime.utcnow()
    )
    db.add(run)
    db.commit()
    return run
