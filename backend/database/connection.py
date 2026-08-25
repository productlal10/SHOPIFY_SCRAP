#!/usr/bin/env python3
"""
Database Connection & Session Management
=========================================
Configures SQLite/PostgreSQL database engine and provides session context managers.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.models import Base

# Default to local SQLite for lightweight standalone dev, or PostgreSQL when DATABASE_URL env is set
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:////Users/turbom/Desktop/Alan/SHOPIFY_SCRAP/ecommerce_monitoring.db"
)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency injector for FastAPI database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
