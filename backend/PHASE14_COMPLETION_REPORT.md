# Phase 14 - PostgreSQL/PostGIS Database and Provenance

## Implementation Status: COMPLETED ✅

## Summary

Phase 14 implements a PostgreSQL/PostGIS database for structured metadata, geospatial information, provenance tracking, and analyst decisions. The database layer is designed to complement the existing Qdrant vector database without modifying any existing pipeline phases.

## Technology Used

- **PostgreSQL** - Relational database
- **PostGIS** - Geospatial extension for PostgreSQL
- **SQLAlchemy** - ORM for database operations
- **GeoAlchemy2** - PostGIS integration with SQLAlchemy
- **python-dotenv** - Environment variable management
- **psycopg2-binary** - PostgreSQL adapter

## Files Created

### Database Module
1. `backend/app/database/__init__.py` - Module initialization
2. `backend/app/database/connection.py` - Database connection and session management
3. `backend/app/database/models.py` - SQLAlchemy ORM models
4. `backend/app/database/repository.py` - Repository classes for data access

### Configuration
5. `backend/.env.example` - Environment variable template
6. `.gitignore` - Updated to exclude .env and sensitive files

### CLI Commands
7. `backend/run_database_setup.py` - Database initialization command
8. `backend/run_database_sync.py` - Database synchronization command

## Database Schema

### Tables Created

1. **scenes** - Sentinel-2 source scenes
   - scene_id, sensor, satellite, acquisition_date, source_path, crs, width, height, processing_status

2. **tiles** - 256x256 satellite tiles
   - tile_id, scene_id, year, acquisition_date, latitude, longitude, bbox (PostGIS geometry), crs, resolution, width, height, valid_percentage, source_path
   - Spatial index on bbox

3. **temporal_pairs** - Temporal tile pairs for change detection
   - pair_id, before_tile_id, after_tile_id, before_date, after_date, bbox, spatial_overlap
   - Foreign keys to tiles

4. **change_results** - Change detection results
   - pair_id, method, change_percentage, confidence, change_mask_path, result_path, model_name, model_version, processing_time
   - Foreign key to temporal_pairs

5. **earliest_changes** - Earliest detected changes
   - location_reference, earliest_change_date, before_date, after_date, confidence, evidence

6. **cluster_assignments** - HDBSCAN cluster assignments
   - tile_id, cluster_id, cluster_probability, is_noise, embedding_model
   - Foreign key to tiles

7. **analyst_reviews** - Analyst reviews and decisions
   - change_result_id, decision (confirmed/rejected), change_type (construction/clearance/water_variation/road_development/unknown), analyst_comment, analyst_id, reviewed_at
   - Foreign key to change_results

8. **processing_history** - Processing provenance and history
   - entity_type, entity_id, phase, operation, model_name, model_version, parameters (JSONB), status, started_at, completed_at, error_message

## Configuration

### Environment Variables

All configuration is read from environment variables via `.env` file:

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/satellite_intelligence
DB_HOST=localhost
DB_PORT=5432
DB_NAME=satellite_intelligence
DB_USER=postgres
DB_PASSWORD=YOUR_PASSWORD

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333

# CLIP Configuration
CLIP_COLLECTION=satellite_tiles_clip
CLAY_COLLECTION=satellite_tiles

# Model Paths
CLAY_MODEL_PATH=models/clay/v1.5/clay-v1.5.ckpt
CHANGEFORMER_MODEL_PATH=models/changeformer/Change Former checkpoints/best_ckpt.pt
CHANGEFORMER_REPO=changeformer-repo

# Data Paths
RAW_DATA_DIR=data/raw
PROCESSED_DATA_DIR=data/processed
TILES_DIR=data/tiles
EMBEDDINGS_DIR=embeddings
CHANGE_RESULTS_DIR=data/change_results
TEMPORAL_PAIRS_DIR=data/temporal_pairs
CLUSTERS_DIR=data/clusters
QDRANT_STORAGE=qdrant_storage
```

## Commands

### Database Setup

```bash
cd backend
python run_database_setup.py
```

This creates:
- Database `satellite_intelligence`
- PostGIS extension
- All tables
- Spatial indexes

### Database Synchronization

```bash
# Sync all Phase 2-13 data
python run_database_sync.py --all

# Sync specific phases
python run_database_sync.py --scenes
python run_database_sync.py --tiles
python run_database_sync.py --pairs
python run_database_sync.py --changes
python run_database_sync.py --clusters
```

The sync command:
- Reads existing Phase 2-13 outputs
- Populates PostgreSQL with metadata
- Records processing provenance
- Supports incremental execution (no duplicates)

## Key Features

### 1. Provenance Tracking

Every imported object retains:
- Source scene
- Source path
- Acquisition date
- Sensor
- Processing phase
- Model name/version
- Processing parameters
- Confidence where applicable

Analysts can trace:
```
Dashboard result → change result → temporal pair → before/after tiles → source scene → original SAFE data
```

### 2. Spatial Indexing

- PostGIS geometry column for bbox
- Spatial index on tiles.bbox
- Enables efficient geospatial queries

### 3. Incremental Synchronization

- Uses `get_or_create` pattern
- Unique constraints prevent duplicates
- Running sync multiple times is safe

### 4. Processing History

- Complete audit trail of all operations
- Per-entity phase tracking
- Success/failure status
- Error messages for debugging

## Architecture

```
Phase 2-13 Outputs
        ↓
    JSON Metadata
        ↓
  Database Sync
        ↓
  PostgreSQL/PostGIS
        ↓
  Repository Layer
        ↓
  Dashboard Services
```

## Files Modified

1. `backend/requirements.txt` - Added database dependencies:
   - sqlalchemy
   - geoalchemy2
   - psycopg2-binary
   - python-dotenv

## Existing Phases Preserved

- ✅ Phase 2-5: Ingestion, quality, tiling - Unchanged
- ✅ Phase 6: Clay embeddings - Unchanged
- ✅ Phase 7: Clay Qdrant collection - Unchanged
- ✅ Phase 8: CLIP text-to-image search - Unchanged
- ✅ Phase 9: CLIP image-to-image search - Unchanged
- ✅ Phase 10: Temporal pairing - Unchanged
- ✅ Phase 11: Change detection - Unchanged
- ✅ Phase 13: Clustering - Unchanged

Phase 14 only reads existing outputs and does not modify any source data, embeddings, or vector collections.

## Next Steps

Before using the database:
1. Install PostgreSQL and PostGIS
2. Create database `satellite_intelligence`
3. Configure `.env` with database credentials
4. Run `python run_database_setup.py`
5. Run `python run_database_sync.py --all`

## Validation Notes

The database sync implementation is ready but requires:
- PostgreSQL installation
- PostGIS extension
- Database creation
- `.env` configuration

Testing should be performed after database setup is complete.

## Phase 14 Status: COMPLETED ✅
