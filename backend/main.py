#!/usr/bin/env python3
"""
FastAPI Master Application Entrypoint
=====================================
Initializes database, CORS middleware, API routers, and healthcheck endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database.connection import init_db
from backend.api.routes_products import router as products_router

app = FastAPI(
    title="Universal E-Commerce Product Data & Inventory Monitoring API",
    description="Production API for tracking real-time pricing, size variants, stock status, and price/stock history across Shopify, Myntra, Flipkart, and Amazon India.",
    version="1.0.0"
)

# Enable CORS for React frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Initialize database tables on application start."""
    init_db()

@app.get("/")
def root_endpoint():
    return {
        "system": "Universal E-Commerce Product Data & Inventory Monitoring API",
        "status": "online",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

# Include API Router
app.include_router(products_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
