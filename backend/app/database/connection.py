"""
Database connection and session management
Phase 14: PostgreSQL/PostGIS Database
"""

import os
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/satellite_intelligence')

# Create engine
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine (for future use)
async_engine = None


@contextmanager
def get_db_session() -> Session:
    """
    Get database session as context manager.
    
    Returns:
        SQLAlchemy Session
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_database():
    """
    Initialize database and create all tables.
    """
    from .models import Base
    from sqlalchemy import text
    
    # Enable PostGIS extension first
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


def drop_database():
    """
    Drop all tables (use with caution).
    """
    from .models import Base
    
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    print("Database tables dropped successfully")
