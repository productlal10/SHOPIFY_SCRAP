#!/usr/bin/env python3
"""
PostgreSQL SQLAlchemy Database Models
======================================
Database schema definition for products, variants, price history, availability history,
and scrape run metrics.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer, DateTime, ForeignKey, Index, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    platform = Column(String(50), nullable=False, index=True)
    product_id = Column(String(100), nullable=False, index=True)
    asin = Column(String(20), nullable=True, index=True)
    sku = Column(String(100), nullable=True)
    style_code = Column(String(100), nullable=True)

    product_name = Column(String(500), nullable=False)
    brand = Column(String(200), nullable=False, index=True)
    category = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)

    product_url = Column(String(1000), nullable=False, unique=True, index=True)
    images = Column(JSON, nullable=True)

    seller = Column(String(200), nullable=True)
    vendor = Column(String(200), nullable=True)

    mrp = Column(Numeric(10, 2), nullable=True)
    selling_price = Column(Numeric(10, 2), nullable=True)
    discount_percent = Column(Numeric(5, 2), nullable=True)
    currency = Column(String(10), default="INR")

    available = Column(Boolean, default=True)
    stock_status = Column(String(50), default="UNKNOWN")
    exact_stock = Column(Integer, nullable=True)
    stock_source = Column(String(100), default="not_publicly_available")

    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_checked_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    variants = relationship("Variant", back_populates="product", cascade="all, delete-orphan")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")
    availability_history = relationship("AvailabilityHistory", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_platform_product_id", "platform", "product_id"),
    )

class Variant(Base):
    __tablename__ = "variants"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(String(100), nullable=False, index=True)
    sku = Column(String(100), nullable=True)
    color = Column(String(100), nullable=True)
    size = Column(String(100), nullable=True)
    attributes = Column(JSON, nullable=True)

    mrp = Column(Numeric(10, 2), nullable=True)
    selling_price = Column(Numeric(10, 2), nullable=True)
    available = Column(Boolean, default=False)
    stock_status = Column(String(50), default="UNKNOWN")
    exact_stock = Column(Integer, nullable=True)
    stock_source = Column(String(100), default="")

    product = relationship("Product", back_populates="variants")
    price_history = relationship("PriceHistory", back_populates="variant", cascade="all, delete-orphan")
    availability_history = relationship("AvailabilityHistory", back_populates="variant", cascade="all, delete-orphan")

class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(String(36), ForeignKey("variants.id", ondelete="CASCADE"), nullable=True)

    old_price = Column(Numeric(10, 2), nullable=False)
    new_price = Column(Numeric(10, 2), nullable=False)
    old_mrp = Column(Numeric(10, 2), nullable=True)
    new_mrp = Column(Numeric(10, 2), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    product = relationship("Product", back_populates="price_history")
    variant = relationship("Variant", back_populates="price_history")

class AvailabilityHistory(Base):
    __tablename__ = "availability_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(String(36), ForeignKey("variants.id", ondelete="CASCADE"), nullable=True)

    old_available = Column(Boolean, nullable=False)
    new_available = Column(Boolean, nullable=False)
    old_exact_stock = Column(Integer, nullable=True)
    new_exact_stock = Column(Integer, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    product = relationship("Product", back_populates="availability_history")
    variant = relationship("Variant", back_populates="availability_history")

class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    url = Column(String(1000), nullable=False)
    platform = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False) # SUCCESS, PARTIAL_SUCCESS, FAILED
    duration_ms = Column(Integer, nullable=False)
    error_message = Column(Text, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)
