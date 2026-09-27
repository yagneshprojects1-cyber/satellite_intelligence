"""
System Health Check Module
Validates environment, database, Qdrant, data, models, and indexes
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result"""
    component: str
    status: str
    message: str
    details: Optional[Dict] = None


class SystemHealthChecker:
    """
    Validates system health across all components.
    
    Checks:
    - Environment configuration
    - Database connectivity
    - Qdrant connectivity
    - Data integrity
    - Model availability
    - Index presence
    """
    
    def __init__(self):
        """Initialize health checker with environment variables."""
        from dotenv import load_dotenv
        load_dotenv()
        
        self.tiles_dir = Path(os.getenv('TILES_DIR', 'data/tiles'))
        self.embeddings_dir = Path(os.getenv('EMBEDDINGS_DIR', 'embeddings'))
        self.qdrant_storage = Path(os.getenv('QDRANT_STORAGE', 'qdrant_storage'))
        self.clay_model_path = Path(os.getenv('CLAY_MODEL_PATH', 'models/clay/v1.5/clay-v1.5.ckpt'))
        self.changeformer_model_path = Path(os.getenv('CHANGEFORMER_MODEL_PATH', 'models/changeformer/Change Former checkpoints/best_ckpt.pt'))
    
    def check_all(self) -> Dict[str, any]:
        """
        Run all health checks.
        
        Returns:
            Overall health status with component details
        """
        checks = []
        
        # Environment check
        checks.append(self._check_environment())
        
        # Database check
        checks.append(self._check_database())
        
        # Qdrant check
        checks.append(self._check_qdrant())
        
        # Data check
        checks.append(self._check_data())
        
        # Model check
        checks.append(self._check_models())
        
        # Index check
        checks.append(self._check_indexes())
        
        # Determine overall status
        statuses = [check.status for check in checks]
        if all(s == HealthStatus.HEALTHY.value for s in statuses):
            overall_status = HealthStatus.HEALTHY.value
        elif any(s == HealthStatus.UNHEALTHY.value for s in statuses):
            overall_status = HealthStatus.UNHEALTHY.value
        else:
            overall_status = HealthStatus.DEGRADED.value
        
        return {
            "overall_status": overall_status,
            "checks": [asdict(check) for check in checks],
            "timestamp": self._get_timestamp()
        }
    
    def _check_environment(self) -> HealthCheck:
        """Check environment configuration."""
        required_vars = [
            'DATABASE_URL', 'TILES_DIR', 'EMBEDDINGS_DIR', 
            'QDRANT_STORAGE', 'CLAY_MODEL_PATH'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            return HealthCheck(
                component="environment",
                status=HealthStatus.UNHEALTHY.value,
                message=f"Missing environment variables: {', '.join(missing_vars)}",
                details={"missing": missing_vars}
            )
        
        return HealthCheck(
            component="environment",
            status=HealthStatus.HEALTHY.value,
            message="All required environment variables set"
        )
    
    def _check_database(self) -> HealthCheck:
        """Check PostgreSQL/PostGIS connectivity."""
        try:
            from app.database.connection import engine, init_database
            from sqlalchemy import text
            
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Check PostGIS extension
            with engine.connect() as conn:
                result = conn.execute(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='postgis')"))
                has_postgis = result.scalar()
            
            if not has_postgis:
                return HealthCheck(
                    component="database",
                    status=HealthStatus.DEGRADED.value,
                    message="PostGIS extension not enabled",
                    details={"postgis": False}
                )
            
            return HealthCheck(
                component="database",
                status=HealthStatus.HEALTHY.value,
                message="Database and PostGIS available"
            )
            
        except Exception as e:
            return HealthCheck(
                component="database",
                status=HealthStatus.UNHEALTHY.value,
                message=f"Database connection failed: {e}",
                details={"error": str(e)}
            )
    
    def _check_qdrant(self) -> HealthCheck:
        """Check Qdrant connectivity and collections."""
        try:
            from qdrant_client import QdrantClient
            
            client = QdrantClient(path=str(self.qdrant_storage))
            
            # Check Clay collection
            clay_exists = client.collection_exists("satellite_tiles")
            clay_count = 0
            if clay_exists:
                clay_info = client.get_collection("satellite_tiles")
                clay_count = clay_info.points_count
            
            # Check CLIP collection
            clip_exists = client.collection_exists("satellite_tiles_clip")
            clip_count = 0
            if clip_exists:
                clip_info = client.get_collection("satellite_tiles_clip")
                clip_count = clip_info.points_count
            
            return HealthCheck(
                component="qdrant",
                status=HealthStatus.HEALTHY.value,
                message="Qdrant available",
                details={
                    "clay_collection": clay_exists,
                    "clay_count": clay_count,
                    "clip_collection": clip_exists,
                    "clip_count": clip_count
                }
            )
            
        except Exception as e:
            # Return degraded status instead of unhealthy to allow startup
            return HealthCheck(
                component="qdrant",
                status=HealthStatus.DEGRADED.value,
                message=f"Qdrant connection issue: {str(e)[:100]}",
                details={"error": str(e)[:200]}
            )
    
    def _check_data(self) -> HealthCheck:
        """Check data directories and file counts."""
        tile_count = 0
        emb_count = 0
        
        # Count tiles
        for year in ["2022", "2023", "2024"]:
            year_dir = self.tiles_dir / year
            if year_dir.exists():
                tile_count += len([d for d in year_dir.iterdir() if d.is_dir() and (d / "metadata.json").exists()])
        
        # Count embeddings
        for year in ["2022", "2023", "2024"]:
            year_dir = self.embeddings_dir / year
            if year_dir.exists():
                emb_count += len(list(year_dir.glob("*.npy")))
        
        if tile_count == 0:
            return HealthCheck(
                component="data",
                status=HealthStatus.UNHEALTHY.value,
                message="No tiles found",
                details={"tiles": tile_count, "embeddings": emb_count}
            )
        
        return HealthCheck(
            component="data",
            status=HealthStatus.HEALTHY.value if tile_count >= 900 else HealthStatus.DEGRADED.value,
            message=f"Data available (tiles: {tile_count}, embeddings: {emb_count})",
            details={"tiles": tile_count, "embeddings": emb_count}
        )
    
    def _check_models(self) -> HealthCheck:
        """Check model availability."""
        clay_exists = self.clay_model_path.exists()
        changeformer_exists = self.changeformer_model_path.exists()
        
        if not clay_exists:
            return HealthCheck(
                component="models",
                status=HealthStatus.UNHEALTHY.value,
                message="Clay model checkpoint not found",
                details={"clay": clay_exists, "changeformer": changeformer_exists}
            )
        
        return HealthCheck(
            component="models",
            status=HealthStatus.HEALTHY.value,
            message="Models available",
            details={"clay": clay_exists, "changeformer": changeformer_exists}
        )
    
    def _check_indexes(self) -> HealthCheck:
        """Check Qdrant index status."""
        try:
            from qdrant_client import QdrantClient
            
            client = QdrantClient(path=str(self.qdrant_storage))
            
            # Check if collections have data
            clay_indexed = False
            clip_indexed = False
            
            if client.collection_exists("satellite_tiles"):
                info = client.get_collection("satellite_tiles")
                clay_indexed = info.points_count > 0
            
            if client.collection_exists("satellite_tiles_clip"):
                info = client.get_collection("satellite_tiles_clip")
                clip_indexed = info.points_count > 0
            
            return HealthCheck(
                component="indexes",
                status=HealthStatus.HEALTHY.value if (clay_indexed or clip_indexed) else HealthStatus.DEGRADED.value,
                message="Vector indexes",
                details={"clay_indexed": clay_indexed, "clip_indexed": clip_indexed}
            )
            
        except Exception as e:
            return HealthCheck(
                component="indexes",
                status=HealthStatus.DEGRADED.value,
                message=f"Index check issue: {str(e)[:100]}",
                details={"error": str(e)[:200]}
            )
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
