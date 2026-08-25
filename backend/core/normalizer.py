#!/usr/bin/env python3
"""
Unified Data Schema Normalizer
==============================
Validates, calculates discounts, formats currency, and enforces strict schema compliance
across all extracted product datasets.
"""

from typing import Dict, Any, List

def calculate_discount(mrp: float, selling_price: float) -> float:
    """Calculate discount percentage from MRP and selling price."""
    if mrp and selling_price and mrp > selling_price > 0:
        return round(((mrp - selling_price) / mrp) * 100, 2)
    return 0.0

def normalize_product_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures all product fields strictly adhere to the unified format."""
    data["platform"] = str(data.get("platform", "")).lower()
    data["product_id"] = str(data.get("product_id", ""))
    data["asin"] = str(data["asin"]) if data.get("asin") else None
    data["sku"] = str(data["sku"]) if data.get("sku") else None
    data["style_code"] = str(data["style_code"]) if data.get("style_code") else None

    data["product_name"] = str(data.get("product_name", "")).strip()
    data["brand"] = str(data.get("brand", "")).strip()
    data["category"] = str(data.get("category", "")).strip() if data.get("category") else None
    data["description"] = str(data.get("description", "")).strip() if data.get("description") else None

    data["product_url"] = str(data.get("product_url", "")).strip()
    data["images"] = list(data.get("images", []))

    data["seller"] = str(data["seller"]).strip() if data.get("seller") else None
    data["vendor"] = str(data["vendor"]).strip() if data.get("vendor") else None

    # Pricing calculations
    mrp = float(data["mrp"]) if data.get("mrp") is not None else None
    selling = float(data["selling_price"]) if data.get("selling_price") is not None else None
    
    if mrp and not selling:
        selling = mrp
    if selling and not mrp:
        mrp = selling

    data["mrp"] = mrp
    data["selling_price"] = selling
    data["discount_percent"] = calculate_discount(mrp, selling) if (mrp and selling) else 0.0
    data["currency"] = str(data.get("currency", "INR"))

    # Stock & Availability
    data["available"] = bool(data.get("available", False))
    if data["exact_stock"] is not None:
        try:
            data["exact_stock"] = int(data["exact_stock"])
        except (ValueError, TypeError):
            data["exact_stock"] = None

    if data.get("exact_stock") is not None and data["exact_stock"] > 0:
        data["available"] = True
        data["stock_status"] = "IN_STOCK"
    elif data["available"]:
        data["stock_status"] = "IN_STOCK"
    else:
        data["stock_status"] = "OUT_OF_STOCK"

    # Normalize Variants
    normalized_variants = []
    for v in data.get("variants", []):
        v_mrp = float(v["mrp"]) if v.get("mrp") is not None else mrp
        v_selling = float(v["selling_price"]) if v.get("selling_price") is not None else selling
        v_exact = int(v["exact_stock"]) if v.get("exact_stock") is not None else None
        v_avail = bool(v.get("available", False))

        if v_exact is not None and v_exact > 0:
            v_avail = True
            v_status = "IN_STOCK"
        elif v_avail:
            v_status = "IN_STOCK"
        else:
            v_status = "OUT_OF_STOCK"

        norm_v = {
            "variant_id": str(v.get("variant_id", "")),
            "sku": str(v["sku"]) if v.get("sku") else None,
            "color": str(v["color"]) if v.get("color") else None,
            "size": str(v["size"]) if v.get("size") else None,
            "attributes": dict(v.get("attributes", {})),
            "mrp": v_mrp,
            "selling_price": v_selling,
            "available": v_avail,
            "stock_status": v_status,
            "exact_stock": v_exact,
            "stock_source": str(v.get("stock_source", data.get("stock_source", "")))
        }
        normalized_variants.append(norm_v)

    data["variants"] = normalized_variants
    return data
