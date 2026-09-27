"""
Main Backend Application
Production-like automatic backend with orchestration layer
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from app.orchestration.job_system import PipelineOrchestrator, JobStatus, Phase
from app.orchestration.health_check import SystemHealthChecker
from app.database.connection import init_database
from app.semantic.semantic_search import SemanticSearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global orchestrator instance
orchestrator: Optional[PipelineOrchestrator] = None
semantic_search: Optional[SemanticSearch] = None
skip_semantic_search = False


# ============================================================
# Pydantic Models
# ============================================================

class HealthResponse(BaseModel):
    overall_status: str
    checks: List[Dict]
    timestamp: str


class PipelineStatusResponse(BaseModel):
    completeness: Dict[str, bool]
    active_jobs: List[Dict]
    timestamp: str


class JobSubmissionRequest(BaseModel):
    phase: str
    operation: str = "process"


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    filters: Optional[Dict[str, Any]] = None


class ImageSearchRequest(BaseModel):
    tile_id: str
    top_k: int = 10
    filters: Optional[Dict[str, Any]] = None


class AnalystReviewRequest(BaseModel):
    change_result_id: str
    decision: str  # confirmed, rejected
    change_type: str  # construction, clearance, water_variation, road_development, unknown
    analyst_comment: Optional[str] = None


# ============================================================
# FastAPI Application
# ============================================================

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SIH Satellite Intelligence API",
    description="Backend API for satellite imagery analysis with automatic pipeline orchestration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - startup and shutdown"""
    global orchestrator, semantic_search
    
    print("=" * 60)
    print("SIH SATELLITE INTELLIGENCE BACKEND")
    print("=" * 60)
    
    # Startup
    print("\nStarting backend...")
    
    # 1. Environment check
    print("Checking environment...")
    health_checker = SystemHealthChecker()
    health = health_checker.check_all()
    print(f"Health status: {health['overall_status']}")
    
    # Skip unhealthy components and continue
    unhealthy_components = [c for c in health['checks'] if c['status'] == 'unhealthy']
    if unhealthy_components:
        print("WARNING: Some components are unhealthy:")
        for check in unhealthy_components:
            print(f"  - {check['component']}: {check['message']}")
        print("\nContinuing with available functionality...")
    
    # 2. Database initialization
    print("Initializing database...")
    try:
        init_database()
        print("Database initialized successfully")
    except Exception as e:
        print(f"WARNING: Database initialization failed: {e}")
        print("Continuing without database...")
    
    # 3. Initialize semantic search
    print("Initializing semantic search...")
    try:
        semantic_search = SemanticSearch(
            qdrant_storage_path=os.getenv('QDRANT_STORAGE', 'qdrant_storage'),
            clip_collection_name=os.getenv('CLIP_COLLECTION', 'satellite_tiles_clip'),
            clay_collection_name=os.getenv('CLAY_COLLECTION', 'satellite_tiles'),
            tiles_dir=os.getenv('TILES_DIR', 'data/tiles'),
            device="cpu"
        )
        print("Semantic search initialized")
    except Exception as e:
        print(f"WARNING: Semantic search initialization failed: {e}")
        print("Continuing without semantic search...")
        semantic_search = None
        skip_semantic_search = True
    
    # 4. Initialize orchestrator
    print("Initializing pipeline orchestrator...")
    num_workers = int(os.getenv('WORKER_THREADS', 4))
    orchestrator = PipelineOrchestrator(num_workers=num_workers)
    orchestrator.start()
    print(f"Started {num_workers} background workers")
    
    # 5. Check data inventory
    print("Checking data inventory...")
    completeness = orchestrator.check_completeness()
    print("Phase completeness:")
    for phase, complete in completeness.items():
        status = "[OK]" if complete else "[PENDING]"
        print(f"  {status} {phase}")
    
    # 6. Auto-run missing phases (if enabled)
    auto_run = os.getenv('AUTO_RUN_PHASES', 'true').lower() == 'true'
    if auto_run:
        print("\nAuto-running missing phases...")
        skip_phases = os.getenv('SKIP_PHASES', '').split(',') if os.getenv('SKIP_PHASES') else []
        orchestrator.auto_run_missing_phases(skip_phases)
    else:
        print("\nAuto-run disabled (set AUTO_RUN_PHASES=true to enable)")
    
    print("\n" + "=" * 60)
    print("BACKEND STARTUP COMPLETE")
    print("=" * 60)
    print(f"API running on http://{os.getenv('API_HOST', '0.0.0.0')}:{os.getenv('API_PORT', 8000)}")
    print("=" * 60)
    
    yield
    
    # Shutdown
    print("\nShutting down backend...")
    if orchestrator:
        orchestrator.stop()
    print("Backend shutdown complete")


app.router.lifespan_context = lifespan


# ============================================================
# API Endpoints
# ============================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check endpoint"""
    health_checker = SystemHealthChecker()
    health = health_checker.check_all()
    return health


@app.get("/pipeline/status", response_model=PipelineStatusResponse)
async def pipeline_status():
    """Get pipeline status and active jobs"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    completeness = orchestrator.check_completeness()
    jobs = orchestrator.get_all_jobs()
    
    from datetime import datetime
    return PipelineStatusResponse(
        completeness=completeness,
        active_jobs=jobs,
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/pipeline/jobs")
async def get_jobs():
    """Get all background jobs"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    jobs = orchestrator.get_all_jobs()
    return {"jobs": jobs}


@app.post("/pipeline/run")
async def run_pipeline_job(request: JobSubmissionRequest, background_tasks: BackgroundTasks):
    """Submit a pipeline job for background processing"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    job_id = orchestrator.submit_job(request.phase, request.operation)
    
    return {
        "job_id": job_id,
        "phase": request.phase,
        "operation": request.operation,
        "status": "submitted"
    }


@app.get("/tiles/{tile_id}")
async def get_tile(tile_id: str):
    """Get tile metadata by ID"""
    from pathlib import Path
    import json
    
    tiles_dir = Path(os.getenv('TILES_DIR', 'data/tiles'))
    
    # Search for tile in year directories
    for year in ["2022", "2023", "2024"]:
        tile_path = tiles_dir / year / tile_id
        if tile_path.exists() and (tile_path / "metadata.json").exists():
            with open(tile_path / "metadata.json", 'r') as f:
                return json.load(f)
    
    raise HTTPException(status_code=404, detail=f"Tile {tile_id} not found")

@app.get("/image/{tile_id}")
async def get_tile_image(tile_id: str):
    """Serve RGB preview image for a tile"""
    from pathlib import Path
    from fastapi.responses import StreamingResponse
    import io
    
    # Extract year from tile_id (e.g., '2022_T43QFV_000459')
    parts = tile_id.split('_')
    year = parts[0] if len(parts) >= 1 and parts[0] in ["2022", "2023", "2024"] else None
    
    tiles_dir = Path(os.getenv('TILES_DIR', 'data/tiles'))
    
    tile_path = None
    if year and (tiles_dir / year / tile_id).exists():
        tile_path = tiles_dir / year / tile_id
    else:
        for y in ["2022", "2023", "2024"]:
            if (tiles_dir / y / tile_id).exists():
                tile_path = tiles_dir / y / tile_id
                break
                
    if not tile_path:
        raise HTTPException(status_code=404, detail=f"Tile {tile_id} not found")
        
    if semantic_search:
        pil_image = semantic_search._create_rgb_from_tile(tile_path)
        if pil_image:
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='JPEG', quality=85)
            img_byte_arr.seek(0)
            return StreamingResponse(img_byte_arr, media_type="image/jpeg")
            
    raise HTTPException(status_code=500, detail="Failed to generate image")


@app.post("/search")
async def search(request: SearchRequest):
    """Text-to-image semantic search using CLIP"""
    if not semantic_search:
        raise HTTPException(status_code=503, detail="Semantic search not initialized - Qdrant may have compatibility issues")
    
    try:
        results = semantic_search.search(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@app.post("/image-search")
async def image_search(request: ImageSearchRequest):
    """Image-to-image similarity search using CLIP"""
    if not semantic_search:
        raise HTTPException(status_code=503, detail="Semantic search not initialized")
    
    try:
        results = semantic_search.search_by_image(
            tile_id=request.tile_id,
            top_k=request.top_k,
            filters=request.filters
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image search failed: {e}")


@app.get("/change-analysis")
async def get_change_analysis():
    """Get change detection results"""
    from pathlib import Path
    import json
    
    change_dir = Path(os.getenv('CHANGE_RESULTS_DIR', 'data/change_results'))
    
    results = []
    for year_comb in ["2022_2023", "2023_2024", "2022_2024"]:
        comb_dir = change_dir / year_comb
        if comb_dir.exists():
            for result_file in comb_dir.glob("*_result.json"):
                with open(result_file, 'r') as f:
                    results.append(json.load(f))
    
    return {"results": results}


@app.get("/similar-locations")
async def get_similar_locations(tile_id: str, top_k: int = 10):
    """Get similar locations using Clay clustering"""
    from app.clustering.clay_clustering import ClayClustering
    from pathlib import Path
    from dotenv import load_dotenv
    import os
    load_dotenv()
    
    try:
        clusterer = ClayClustering(
            embeddings_dir=Path(os.getenv('EMBEDDINGS_DIR', 'embeddings')),
            output_dir=Path(os.getenv('CLUSTERS_DIR', 'data/clusters'))
        )
        
        # This would require the clustering to be run first
        # For now, return a placeholder
        return {
            "tile_id": tile_id,
            "similar_locations": [],
            "message": "Clustering not yet run. Submit clustering job first."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similar locations failed: {e}")


@app.get("/earliest-change")
async def get_earliest_changes():
    """Get earliest change analysis results"""
    from pathlib import Path
    import json
    
    earliest_dir = Path(os.getenv('EARLIEST_CHANGES_DIR', 'data/earliest_changes'))
    summary_file = earliest_dir / "earliest_changes_summary.json"
    
    if not summary_file.exists():
        return {
            "results": [],
            "message": "Earliest change analysis not yet run. Submit earliest change job first."
        }
    
    with open(summary_file, 'r') as f:
        summary = json.load(f)
    
    return summary


@app.post("/analyst-review")
async def submit_analyst_review(request: AnalystReviewRequest):
    """Submit analyst review for a change result"""
    from app.database.connection import get_db_session
    from app.database.models import AnalystReview
    from sqlalchemy import select
    from datetime import datetime
    
    with get_db_session() as session:
        # Find change result
        from app.database.models import ChangeResult
        change_result = session.query(ChangeResult).filter(
            ChangeResult.id == request.change_result_id
        ).first()
        
        if not change_result:
            raise HTTPException(status_code=404, detail="Change result not found")
        
        # Create analyst review
        review = AnalystReview(
            change_result_id=request.change_result_id,
            decision=request.decision,
            change_type=request.change_type,
            analyst_comment=request.analyst_comment,
            analyst_id="system",  # Would be actual user in production
            reviewed_at=datetime.utcnow()
        )
        
        session.add(review)
        session.commit()
    
    return {"status": "submitted", "review_id": str(review.id)}


# ============================================================
# Main Entry Point
# ============================================================

def main():
    """Main entry point for running the backend"""
    import os
    
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 8000))
    workers = int(os.getenv('API_WORKERS', 1))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    uvicorn.run(
        "run_backend:app",
        host=host,
        port=port,
        workers=workers,
        reload=debug
    )


if __name__ == "__main__":
    main()
