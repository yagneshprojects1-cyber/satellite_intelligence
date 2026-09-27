"""
Phase 14 - Database Setup CLI
Initialize PostgreSQL/PostGIS database and create tables
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from app.database.connection import init_database, drop_database


def main():
    parser = argparse.ArgumentParser(description="Phase 14: Database Setup")
    parser.add_argument("--drop", action="store_true",
                       help="Drop existing tables before recreation")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("PHASE 14: DATABASE SETUP")
    print("=" * 60)
    
    if args.drop:
        print("Dropping existing tables...")
        drop_database()
    
    print("Initializing database...")
    init_database()
    
    print("\nDatabase setup completed successfully!")


if __name__ == "__main__":
    main()
