"""
Configuration for Phase 5 Geospatial Tiling
"""

from pathlib import Path
from .ingestion_config import BASE_DIR, PROCESSED_DATA_DIR

TILES_DATA_DIR = BASE_DIR / "data" / "tiles"

# Tile Settings
DEFAULT_TILE_SIZE = 256
MIN_VALID_PERCENTAGE = 60.0
SKIP_INVALID_TILES = True

# Temporal Alignment
REFERENCE_YEAR = 2022
