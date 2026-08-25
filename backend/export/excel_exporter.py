#!/usr/bin/env python3
"""
Excel (.xlsx) Exporter Service
==============================
Generates production Excel spreadsheets adhering strictly to the required column specification.
"""

import os
import io
import pandas as pd
from typing import List, Dict, Any

REQUIRED_EXCEL_COLUMNS = [
    "Platform",
    "Product ID",
    "ASIN",
    "SKU",
    "Style Code",
    "Brand",
    "Product",
    "Color",
    "Size",
    "MRP",
    "Selling Price",
    "Discount %",
    "Available",
    "Stock Status",
    "Exact Stock",
    "Stock Source",
    "Seller",
    "Product URL",
    "Last Checked"
]

def generate_excel_export(products_data: List[Dict[str, Any]]) -> bytes:
    """Transforms normalized products list into Excel workbook bytes adhering to specification."""
    rows = []
    
    for p in products_data:
        platform = p.get("platform", "").upper()
        p_id = p.get("product_id", "")
        asin = p.get("asin")
        p_sku = p.get("sku")
        style_code = p.get("style_code")
        brand = p.get("brand", "")
        p_name = p.get("product_name", "")
        p_mrp = p.get("mrp")
        p_price = p.get("selling_price")
        p_disc = p.get("discount_percent")
        p_avail = "True" if p.get("available") else "False"
        p_status = p.get("stock_status", "UNKNOWN")
        p_exact = p.get("exact_stock") if p.get("exact_stock") is not None else "NULL"
        p_source = p.get("stock_source", "not_publicly_available")
        seller = p.get("seller") or p.get("vendor") or ""
        p_url = p.get("product_url", "")
        last_checked = p.get("last_checked_at", "")

        variants = p.get("variants", [])
        if variants:
            for v in variants:
                row = {
                    "Platform": platform,
                    "Product ID": p_id,
                    "ASIN": asin or "",
                    "SKU": v.get("sku") or p_sku or "",
                    "Style Code": style_code or "",
                    "Brand": brand,
                    "Product": p_name,
                    "Color": v.get("color") or "",
                    "Size": v.get("size") or "",
                    "MRP": v.get("mrp") if v.get("mrp") is not None else (p_mrp or ""),
                    "Selling Price": v.get("selling_price") if v.get("selling_price") is not None else (p_price or ""),
                    "Discount %": p_disc or 0.0,
                    "Available": "True" if v.get("available") else "False",
                    "Stock Status": v.get("stock_status", p_status),
                    "Exact Stock": v.get("exact_stock") if v.get("exact_stock") is not None else p_exact,
                    "Stock Source": v.get("stock_source") or p_source,
                    "Seller": seller,
                    "Product URL": p_url,
                    "Last Checked": last_checked
                }
                rows.append(row)
        else:
            row = {
                "Platform": platform,
                "Product ID": p_id,
                "ASIN": asin or "",
                "SKU": p_sku or "",
                "Style Code": style_code or "",
                "Brand": brand,
                "Product": p_name,
                "Color": "",
                "Size": "",
                "MRP": p_mrp or "",
                "Selling Price": p_price or "",
                "Discount %": p_disc or 0.0,
                "Available": p_avail,
                "Stock Status": p_status,
                "Exact Stock": p_exact,
                "Stock Source": p_source,
                "Seller": seller,
                "Product URL": p_url,
                "Last Checked": last_checked
            }
            rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=REQUIRED_EXCEL_COLUMNS)
    else:
        df = df[REQUIRED_EXCEL_COLUMNS]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="E-Commerce Monitoring")
    return output.getvalue()
