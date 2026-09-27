# Backend Startup Guide

## Quick Start

### Prerequisites

1. **Python Virtual Environment**
   The backend requires a Python 3.12 virtual environment with all dependencies installed.

2. **PostgreSQL/PostGIS**
   - Install PostgreSQL with PostGIS extension
   - Create database: `satellite_intelligence`
   - Configure connection in `.env`

3. **Environment Configuration**
   - Copy `.env.example` to `.env`
   - Fill in your actual values (database credentials, paths, etc.)

### Starting the Backend

```bash
cd backend

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Activate virtual environment (Linux/Mac)
source .venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Start the backend
python run_backend.py
```

The backend will automatically:
1. Check system health (environment, database, Qdrant, data, models, indexes)
2. Initialize database tables if needed
3. Initialize semantic search
4. Start background workers (default: 4)
5. Check data inventory and phase completeness
6. Auto-run missing phases (if `AUTO_RUN_PHASES=true`)
7. Start API server

### API Endpoints

Once started, the API is available at `http://localhost:8000`

**Health & Status:**
- `GET /health` - System health check
- `GET /pipeline/status` - Pipeline status and active jobs
- `GET /pipeline/jobs` - All background jobs
- `POST /pipeline/run` - Submit a pipeline job

**Search & Analysis:**
- `POST /search` - Text-to-image semantic search
- `POST /image-search` - Image-to-image similarity search
- `GET /change-analysis` - Change detection results
- `GET /similar-locations` - Similar locations (Clay clustering)
- `GET /earliest-change` - Earliest change analysis

**Data Access:**
- `GET /tiles/{tile_id}` - Get tile metadata

**Analyst Review:**
- `POST /analyst-review` - Submit analyst review

### Background Processing

The backend runs heavy AI processing in background workers to keep the API responsive:

- **Phase 6:** Clay embedding generation (GPU recommended)
- **Phase 7:** Qdrant indexing
- **Phase 10:** Temporal pairing
- **Phase 11:** Change detection
- **Phase 12:** Earliest change analysis
- **Phase 13:** Clay clustering
- **Database Sync:** PostgreSQL/PostGIS synchronization

Jobs are:
- **Resumable:** Skip already-completed work
- **Idempotent:** Safe to re-run
- **Retry-safe:** Failed jobs can be retried

### Configuration

All configuration is done through `.env`:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/satellite_intelligence

# Data paths
TILES_DIR=data/tiles
EMBEDDINGS_DIR=embeddings

# Model paths
CLAY_MODEL_PATH=models/clay/v1.5/clay-v1.5.ckpt

# Processing
AUTO_RUN_PHASES=true
SKIP_PHASES=6,7  # Skip specific phases
CLAY_DEVICE=cuda  # or cpu
WORKER_THREADS=4
```

### Testing

Run the startup test:

```bash
cd backend
.venv\Scripts\activate
python test_backend_startup.py
```

This verifies:
- Orchestration module imports
- System health check
- Orchestrator initialization
- Pipeline completeness check
- Job submission
- Job status tracking
- Worker lifecycle

### Architecture

**Request Flow:**
```
API Request → FastAPI Handler → Lightweight Operation → Response
                    ↓
              Background Job Queue → Worker Thread → Heavy Processing → Database/Qdrant Update
```

**Data Flow:**
```
Phase 2-5: Tiles → Phase 6: Clay Embeddings → Phase 7: Qdrant Clay
                          ↓
Phase 8-9: CLIP Embeddings → Qdrant CLIP
                          ↓
Phase 10: Temporal Pairs → Phase 11: Change Detection → Phase 12: Earliest Change
                          ↓
Phase 13: Clay Clustering
                          ↓
Database Sync → PostgreSQL/PostGIS
```

### Troubleshooting

**Database Connection Failed:**
- Ensure PostgreSQL is running
- Check DATABASE_URL in `.env`
- Verify PostGIS extension is enabled

**Qdrant Connection Failed:**
- Check QDRANT_STORAGE path in `.env`
- Ensure directory exists and is writable

**Phase 6 Fails (CPU):**
- Clay model requires GPU for reasonable performance
- Set `CLAY_DEVICE=cpu` in `.env` for CPU (slow)
- Use Kaggle GPU for Phase 6 (see clay_kaggle package)

**Jobs Not Running:**
- Check `AUTO_RUN_PHASES=true` in `.env`
- Check `SKIP_PHASES` doesn't include the phase you need
- Review job status at `GET /pipeline/jobs`

### Production Deployment

For production deployment:

1. **Environment Variables:** Use environment variables, not `.env`
2. **Database:** Use managed PostgreSQL/PostGIS service
3. **Workers:** Increase `WORKER_THREADS` based on CPU cores
4. **API Workers:** Set `API_WORKERS` > 1 for production
5. **Logging:** Add proper logging configuration
6. **Monitoring:** Add metrics and monitoring
7. **Authentication:** Add API authentication/authorization

### Developer Experience

The intended developer experience is:

```bash
cd backend
.venv\Scripts\activate
python run_backend.py
```

That's it. The backend automatically:
- Validates environment
- Connects to services
- Checks data/models/indexes
- Resumes incomplete processing
- Starts background workers
- Exposes API

No manual phase-by-phase commands required.
