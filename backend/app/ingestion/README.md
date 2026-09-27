# Sentinel-2 Ingestion Pipeline

## Overview
This module handles the ingestion of Sentinel-2 SAFE files into a standardized, processed format suitable for AI/ML analysis.

## Technology Used
- **Python 3.x**
- **Rasterio/GDAL**: For geospatial image processing and JP2 to GeoTIFF conversion
- **NumPy**: For array operations and image manipulation
- **SciPy**: For image resampling
- **XML Parsing**: For extracting Sentinel-2 metadata

## Module Structure

### Core Files

#### `ingest.py`
**Main orchestration pipeline** that coordinates the entire ingestion process.

**Key Classes:**
- `Sentinel2IngestionPipeline`: Main pipeline class that orchestrates SAFE file discovery, processing, and metadata extraction

**Key Functions:**
- `discover_and_group()`: Automatically discovers SAFE files and groups them by year
- `process_single_safe()`: Processes a single SAFE file through the complete pipeline
- `run_pipeline()`: Executes the complete ingestion pipeline

**Technologies:** Python, pathlib, json, datetime

#### `utils/safe_parser.py`
**SAFE file structure parser** that handles Sentinel-2 directory structure and metadata extraction.

**Key Classes:**
- `SAFEParser`: Parses Sentinel-2 SAFE files and extracts metadata
- `SAFEParseError`: Custom exception for SAFE parsing errors

**Key Functions:**
- `parse_filename()`: Extracts satellite, date, tile ID from SAFE filename
- `find_granule_dir()`: Automatically finds GRANULE directory
- `find_img_data_dirs()`: Finds IMG_DATA directories for different resolutions
- `find_band_files()`: Locates specific band files
- `get_quality_masks()`: Extracts quality mask information
- `discover_safe_files()`: Discovers all SAFE files in a directory
- `group_safe_by_year()`: Groups SAFE files by acquisition year

**Technologies:** Python, re (regex), xml.etree.ElementTree, pathlib

#### `utils/image_processor.py`
**Image processing utilities** for converting JP2 to GeoTIFF and creating quality masks.

**Key Classes:**
- `ImageProcessor`: Handles image conversion and processing operations

**Key Functions:**
- `jp2_to_geotiff()`: Converts JP2 files to GeoTIFF while preserving geospatial information
- `create_rgb_composite()`: Creates RGB preview from individual bands
- `create_valid_mask()`: Creates valid/invalid mask from SCL quality data
- `process_band_collection()`: Processes multiple bands in batch
- `match_resolution()`: Gets bands for specific resolution
- `get_rgb_bands()`: Extracts RGB bands from available bands

**Technologies:** Rasterio, NumPy, SciPy (for resampling)

#### `utils/metadata_extractor.py`
**Metadata extraction and management** for scene documentation.

**Key Classes:**
- `MetadataExtractor`: Extracts and formats metadata from processed scenes

**Key Functions:**
- `extract_metadata()`: Creates complete metadata dictionary
- `save_metadata()`: Saves metadata to JSON file
- `load_metadata()`: Loads metadata from JSON file

**Technologies:** Python, json, datetime

#### `config/ingestion_config.py`
**Configuration settings** for the ingestion pipeline.

**Key Configuration:**
- `BAND_RESOLUTIONS`: Maps band names to their resolutions
- `RGB_BANDS`: RGB channel to band name mapping
- `SCL_CLASSES`: Scene Classification class definitions
- `VALID_SCL_CLASSES`: Classes considered valid for analysis
- Directory structure and processing settings

**Technologies:** Python, pathlib

## Processing Pipeline

### Step 1: SAFE Discovery
- Scans `data/raw/` for `*.SAFE` directories
- Parses filenames to extract satellite, date, tile ID
- Groups files by acquisition year

### Step 2: Structure Analysis
- Automatically finds GRANULE directory
- Locates IMG_DATA directories (R10m, R20m, R60m)
- Identifies available bands and quality masks

### Step 3: Band Extraction
- Extracts bands at native resolutions:
  - 10m: B02, B03, B04, B08
  - 20m: B05, B06, B07, B8A, B11, B12
  - 60m: B01, B09

### Step 4: Format Conversion
- Converts JP2 files to GeoTIFF format
- Preserves all geospatial information (CRS, transform, resolution, bounds)
- Maintains original resolution (no resampling)

### Step 5: Quality Processing
- Extracts SCL (Scene Classification Layer)
- Creates valid/invalid masks based on quality rules
- Filters out clouds, shadows, snow, etc.

### Step 6: RGB Preview Generation
- Creates RGB composite from B04 (red), B03 (green), B02 (blue)
- Used for visualization and analyst interface

### Step 7: Metadata Extraction
- Extracts complete scene metadata
- Saves to JSON for provenance and analysis

## Output Structure

```
data/processed/
├── 2022/
│   ├── bands/
│   │   ├── B01.tif, B02.tif, ..., B12.tif
│   ├── quality/
│   │   ├── SCL.tif
│   │   └── valid_mask.tif
│   ├── previews/
│   │   └── rgb.tif
│   └── metadata.json
├── 2023/
│   └── ...
└── 2024/
    └── ...
```

## Usage

### Command Line
```bash
cd backend
python -m app.ingestion.ingest --raw-dir data/raw --processed-dir data/processed
```

### With Options
```bash
# Process specific years only
python -m app.ingestion.ingest --years 2022 2023

# Overwrite existing files
python -m app.ingestion.ingest --overwrite
```

### Python API
```python
from app.ingestion import Sentinel2IngestionPipeline
from pathlib import Path

pipeline = Sentinel2IngestionPipeline(
    raw_dir=Path("data/raw"),
    processed_dir=Path("data/processed"),
    overwrite=False
)

pipeline.run_pipeline()
```

## Key Features

1. **Automatic Discovery**: No hardcoding of SAFE structure
2. **Resolution Preservation**: Maintains original band resolutions
3. **Geospatial Integrity**: Preserves all coordinate reference information
4. **Quality Handling**: Integrates Sentinel-2 quality masks
5. **Incremental Processing**: Can skip already processed files
6. **Comprehensive Metadata**: Full provenance tracking
7. **Modular Design**: Easy to extend and maintain

## Dependencies
- rasterio (geospatial image processing)
- GDAL (geospatial data abstraction)
- numpy (numerical operations)
- scipy (image resampling)
- lxml (XML parsing)

## Notes
- Original SAFE files are never modified
- All processing maintains geospatial provenance
- Quality masks help suppress false changes in later analysis
- RGB previews facilitate visual inspection and UI development