#!/usr/bin/env python3
"""
CSV Exporter Service
====================
Generates standard CSV output for single or bulk scraped datasets.
"""

import io
import csv
import pandas as pd
from typing import List, Dict, Any
from backend.export.excel_exporter import REQUIRED_EXCEL_COLUMNS, generate_excel_export

def generate_csv_export(products_data: List[Dict[str, Any]]) -> str:
    """Transforms normalized products list into CSV string content."""
    excel_bytes = generate_excel_export(products_data)
    df = pd.read_excel(io.BytesIO(excel_bytes))
    return df.to_csv(index=False)
