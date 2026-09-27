"""
Configuration for Sentinel-2 Ingestion Pipeline
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

# Sentinel-2 band specifications (mapping resolution to bands)
BAND_RESOLUTIONS = {
    "R10m": ["B02", "B03", "B04", "B08"],
    "R20m": ["B05", "B06", "B07", "B8A", "B11", "B12"],
    "R60m": ["B01", "B09"]
}

# RGB band mapping (using R10m bands)
RGB_BANDS = {
    "red": "B04",
    "green": "B03",
    "blue": "B02"
}

# Quality bands
QUALITY_BANDS = ["SCL"]

# SCL (Scene Classification Layer) class values — Sentinel-2 L2A specification
# Reference: https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-2-msi/level-2a/algorithm
SCL_CLASSES = {
    0: "NO_DATA",
    1: "SATURATED_DEFECTIVE",
    2: "DARK_AREA_PIXELS",
    3: "CLOUD_SHADOW",
    4: "VEGETATION",
    5: "NOT_VEGETATED",
    6: "WATER",
    7: "UNCLASSIFIED",
    8: "CLOUD_MEDIUM_PROBABILITY",
    9: "CLOUD_HIGH_PROBABILITY",
    10: "THIN_CIRRUS",
    11: "SNOW_ICE"
}

# Valid SCL classes for analysis (exclude problematic classes)
# Configurable for Phase 4 quality processing
# Keep: dark area pixels (2), vegetation (4), bare soil (5), water (6)
VALID_SCL_CLASSES = [2, 4, 5, 6]

# Invalid SCL classes (excluded from analysis)
# Exclude: no data (0), saturated/defective (1), cloud shadow (3),
#          unclassified (7), cloud med (8), cloud high (9), cirrus (10), snow (11)
INVALID_SCL_CLASSES = [0, 1, 3, 7, 8, 9, 10, 11]

# Classes to apply morphological buffer around (cloud edges & shadow)
CLOUD_SHADOW_BUFFER_CLASSES = [3, 8, 9, 10]  # shadow, cloud med, cloud high, cirrus

# SCL class groupings for quality statistics reporting
SCL_CLASS_GROUPS = {
    "cloud_medium":    [8],       # Cloud medium probability
    "cloud_high":      [9],       # Cloud high probability
    "cloud_cirrus":    [10],      # Thin cirrus
    "cloud_all":       [8, 9, 10],# All cloud types
    "cloud_shadow":    [3],       # Cloud shadow
    "snow_ice":        [11],      # Snow/ice
    "vegetation":      [4],       # Vegetation
    "water":           [6],       # Water
    "bare_soil":       [5],       # Not vegetated / bare soil
    "dark_area":       [2],       # Dark area pixels
    "no_data":         [0, 1],    # No data + saturated/defective
    "unclassified":    [7]        # Unclassified
}

# ---------------------------------------------------------------------------
# Sentinel-2 L2A Reflectance Scaling
# ---------------------------------------------------------------------------
# Processing baselines < N04.00 : reflectance = DN * 0.0001  (offset = 0)
# Processing baselines >= N04.00: reflectance = DN * 0.0001 - 0.1  (offset = -1000 DN)
# Our data uses N05.10 → baseline >= N04.00 → offset applies.
# Reference: ESA Technical Note OMPC.CS-TN-0005 "Sentinel-2 MSI Level-2A Products"
# ---------------------------------------------------------------------------
L2A_SCALE_FACTOR = 0.0001            # DN → reflectance scale (all baselines)
L2A_REFLECTANCE_OFFSET = -0.1        # Additive offset AFTER scaling (baseline >= N04.00)

# Quality processing settings
APPLY_QUALITY_MASK_TO_BANDS = False  # Apply valid mask to band files (creates cleaned versions)
CLOUD_SHADOW_BUFFER_SIZE = 0  # Pixels to buffer around cloud/shadow (0 = disabled)
REFLECTANCE_NORMALIZATION = True  # Apply reflectance normalization to processed bands
SPATIAL_ALIGNMENT_CHECK = True  # Verify spatial alignment across temporal scenes

# Directory structure for processed data
PROCESSED_STRUCTURE = {
    "bands": "bands",
    "quality": "quality", 
    "previews": "previews"
}

# File extensions
SAFE_EXTENSION = ".SAFE"
JP2_EXTENSION = ".jp2"
GEOTIFF_EXTENSION = ".tif"

# Processing settings
OVERWRITE_EXISTING = False  # Set to True to reprocess existing data
CREATE_VALID_MASK = True  # Create combined valid/invalid mask
CREATE_RGB_PREVIEW = True  # Create RGB preview image