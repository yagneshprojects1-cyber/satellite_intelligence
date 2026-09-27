"""
Database Synchronization Module
Populates PostgreSQL/PostGIS from existing data with idempotent upsert logic
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text, func, select, update, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .models import (
    Scene, Tile, TemporalPair, ChangeResult, 
    EarliestChange, ClusterAssignment, ProcessingHistory
)
from .connection import get_db_session


class DatabaseSynchronizer:
    """
    Synchronizes existing data to PostgreSQL/PostGIS.
    
    Implements idempotent upsert logic with foreign keys, indexes,
    spatial indexes, timestamps, and processing status tracking.
    """
    
    def __init__(self, tiles_dir: Path = None, embeddings_dir: Path = None):
        """Initialize synchronizer with data directories."""
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        self.tiles_dir = Path(os.getenv('TILES_DIR', 'data/tiles'))
        self.embeddings_dir = Path(os.getenv('EMBEDDINGS_DIR', 'embeddings'))
        self.temporal_pairs_dir = Path(os.getenv('TEMPORAL_PAIRS_DIR', 'data/temporal_pairs'))
        self.change_results_dir = Path(os.getenv('CHANGE_RESULTS_DIR', 'data/change_results'))
        self.clusters_dir = Path(os.getenv('CLUSTERS_DIR', 'data/clusters'))
        self.earliest_changes_dir = Path(os.getenv('EARLIEST_CHANGES_DIR', 'data/earliest_changes'))
        
        self.stats = {
            "scenes": {"synced": 0, "skipped": 0, "failed": 0},
            "tiles": {"synced": 0, "skipped": 0, "failed": 0},
            "temporal_pairs": {"synced": 0, "skipped": 0, "failed": 0},
            "change_results": {"synced": 0, "skipped": 0, "failed": 0},
            "earliest_changes": {"synced": 0, "skipped": 0, "failed": 0},
            "cluster_assignments": {"synced": 0, "skipped": 0, "failed": 0}
        }
    
    def synchronize_all(self) -> Dict[str, any]:
        """
        Synchronize all data to PostgreSQL.
        
        Returns:
            Synchronization statistics
        """
        print("=" * 60)
        print("DATABASE SYNCHRONIZATION")
        print("=" * 60)
        
        with get_db_session() as session:
            # Synchronize in dependency order
            self._synchronize_scenes(session)
            self._synchronize_tiles(session)
            self._synchronize_temporal_pairs(session)
            self._synchronize_change_results(session)
            self._synchronize_earliest_changes(session)
            self._synchronize_cluster_assignments(session)
            
            session.commit()
        
        summary = {
            "total_synced": sum(s["synced"] for s in self.stats.values()),
            "total_skipped": sum(s["skipped"] for s in self.stats.values()),
            "total_failed": sum(s["failed"] for s in self.stats.values()),
            "details": self.stats
        }
        
        print("=" * 60)
        print("SYNCHRONIZATION SUMMARY")
        print("=" * 60)
        print(f"Total synced: {summary['total_synced']}")
        print(f"Total skipped: {summary['total_skipped']}")
        print(f"Total failed: {summary['total_failed']}")
        print("=" * 60)
        
        return summary
    
    def _synchronize_scenes(self, session: Session):
        """Synchronize Sentinel-2 source scenes."""
        print("Synchronizing scenes...")
        
        # Extract unique source scenes from tile metadata
        scenes_seen = set()
        for year in ["2022", "2023", "2024"]:
            year_dir = self.tiles_dir / year
            if not year_dir.exists():
                continue
            
            for tile_dir in year_dir.iterdir():
                if not tile_dir.is_dir():
                    continue
                
                metadata_file = tile_dir / "metadata.json"
                if not metadata_file.exists():
                    continue
                
                try:
                    with open(metadata_file, 'r') as f:
                        meta = json.load(f)
                    
                    source_scene = meta.get("source_scene", "")
                    if source_scene and source_scene not in scenes_seen:
                        scenes_seen.add(source_scene)
                        
                        # Parse scene ID from source_scene
                        scene_id = source_scene.split("_")[0] if "_" in source_scene else source_scene
                        
                        # Parse acquisition date
                        scene_date_str = source_scene.split("_")[2] if "_" in source_scene else ""
                        acquisition_date = None
                        if scene_date_str and "T" in scene_date_str:
                            try:
                                date_part = scene_date_str.split("T")[0]
                                acquisition_date = datetime.strptime(date_part, "%Y%m%d")
                            except:
                                pass
                        
                        # Upsert scene
                        existing = session.query(Scene).filter(Scene.scene_id == scene_id).first()
                        if existing:
                            self.stats["scenes"]["skipped"] += 1
                        else:
                            scene = Scene(
                                scene_id=scene_id,
                                sensor="Sentinel-2",
                                satellite="Sentinel-2A",
                                acquisition_date=acquisition_date or datetime.utcnow(),
                                source_path=f"data/raw/{source_scene}.SAFE",
                                crs="EPSG:4326",
                                width=0,  # Will be updated from tiles
                                height=0,
                                processing_status="completed"
                            )
                            session.add(scene)
                            self.stats["scenes"]["synced"] += 1
                
                except Exception as e:
                    print(f"  Error processing {tile_dir}: {e}")
                    self.stats["scenes"]["failed"] += 1
        
        print(f"  Scenes: {self.stats['scenes']['synced']} synced, {self.stats['scenes']['skipped']} skipped")
    
    def _synchronize_tiles(self, session: Session):
        """Synchronize tiles with idempotent upsert."""
        print("Synchronizing tiles...")
        
        for year in ["2022", "2023", "2024"]:
            year_dir = self.tiles_dir / year
            if not year_dir.exists():
                continue
            
            for tile_dir in year_dir.iterdir():
                if not tile_dir.is_dir():
                    continue
                
                metadata_file = tile_dir / "metadata.json"
                if not metadata_file.exists():
                    continue
                
                try:
                    with open(metadata_file, 'r') as f:
                        meta = json.load(f)
                    
                    tile_id = meta.get("tile_id", tile_dir.name)
                    
                    # Check if tile already exists
                    existing = session.query(Tile).filter(Tile.tile_id == tile_id).first()
                    
                    if existing:
                        self.stats["tiles"]["skipped"] += 1
                        continue
                    
                    # Get scene reference
                    source_scene = meta.get("source_scene", "")
                    scene_id = source_scene.split("_")[0] if "_" in source_scene else source_scene
                    scene = session.query(Scene).filter(Scene.scene_id == scene_id).first()
                    
                    # Parse date
                    date_str = meta.get("date", "")
                    acquisition_date = None
                    if date_str:
                        try:
                            acquisition_date = datetime.strptime(date_str, "%Y-%m-%d")
                        except:
                            pass
                    
                    # Create bbox geometry (PostGIS)
                    bbox = meta.get("bbox", {})
                    bbox_geom = f"POLYGON(({bbox.get('min_lon', 0)} {bbox.get('min_lat', 0)}, {bbox.get('max_lon', 0)} {bbox.get('min_lat', 0)}, {bbox.get('max_lon', 0)} {bbox.get('max_lat', 0)}, {bbox.get('min_lon', 0)} {bbox.get('max_lat', 0)}))"
                    
                    tile = Tile(
                        tile_id=tile_id,
                        scene_id=scene.id if scene else None,
                        year=year,
                        acquisition_date=acquisition_date or datetime.utcnow(),
                        latitude=meta.get("latitude", 0.0),
                        longitude=meta.get("longitude", 0.0),
                        bbox=text(f"ST_GeomFromText('{bbox_geom}', 4326)"),
                        crs=meta.get("crs", "EPSG:4326"),
                        resolution=meta.get("resolution", 10.0),
                        width=meta.get("width", 256),
                        height=meta.get("height", 256),
                        valid_percentage=meta.get("valid_percentage", 100.0),
                        source_path=str(tile_dir)
                    )
                    
                    session.add(tile)
                    self.stats["tiles"]["synced"] += 1
                
                except Exception as e:
                    print(f"  Error processing {tile_dir}: {e}")
                    self.stats["tiles"]["failed"] += 1
        
        print(f"  Tiles: {self.stats['tiles']['synced']} synced, {self.stats['tiles']['skipped']} skipped")
    
    def _synchronize_temporal_pairs(self, session: Session):
        """Synchronize temporal pairs."""
        print("Synchronizing temporal pairs...")
        
        for year_comb in ["2022_2023", "2023_2024", "2022_2024"]:
            comb_dir = self.temporal_pairs_dir / year_comb
            if not comb_dir.exists():
                continue
            
            for pair_file in comb_dir.glob("*.json"):
                try:
                    with open(pair_file, 'r') as f:
                        pair_data = json.load(f)
                    
                    pair_id = pair_data.get("pair_id", "")
                    
                    # Check if pair already exists
                    existing = session.query(TemporalPair).filter(TemporalPair.pair_id == pair_id).first()
                    if existing:
                        self.stats["temporal_pairs"]["skipped"] += 1
                        continue
                    
                    # Get tile references
                    before_tile = session.query(Tile).filter(Tile.tile_id == pair_data.get("before_tile_id")).first()
                    after_tile = session.query(Tile).filter(Tile.tile_id == pair_data.get("after_tile_id")).first()
                    
                    if not before_tile or not after_tile:
                        self.stats["temporal_pairs"]["failed"] += 1
                        continue
                    
                    # Parse dates
                    before_date = None
                    after_date = None
                    try:
                        before_date = datetime.strptime(pair_data.get("before_date", ""), "%Y-%m-%d")
                        after_date = datetime.strptime(pair_data.get("after_date", ""), "%Y-%m-%d")
                    except:
                        pass
                    
                    # Create bbox geometry
                    bbox = pair_data.get("bbox", {})
                    bbox_geom = f"POLYGON(({bbox.get('min_lon', 0)} {bbox.get('min_lat', 0)}, {bbox.get('max_lon', 0)} {bbox.get('min_lat', 0)}, {bbox.get('max_lon', 0)} {bbox.get('max_lat', 0)}, {bbox.get('min_lon', 0)} {bbox.get('max_lat', 0)}))"
                    
                    temporal_pair = TemporalPair(
                        pair_id=pair_id,
                        before_tile_id=before_tile.id,
                        after_tile_id=after_tile.id,
                        before_date=before_date or datetime.utcnow(),
                        after_date=after_date or datetime.utcnow(),
                        bbox=text(f"ST_GeomFromText('{bbox_geom}', 4326)"),
                        spatial_overlap=pair_data.get("spatial_overlap", 0.0)
                    )
                    
                    session.add(temporal_pair)
                    self.stats["temporal_pairs"]["synced"] += 1
                
                except Exception as e:
                    print(f"  Error processing {pair_file}: {e}")
                    self.stats["temporal_pairs"]["failed"] += 1
        
        print(f"  Temporal pairs: {self.stats['temporal_pairs']['synced']} synced, {self.stats['temporal_pairs']['skipped']} skipped")
    
    def _synchronize_change_results(self, session: Session):
        """Synchronize change detection results."""
        print("Synchronizing change results...")
        
        for year_comb in ["2022_2023", "2023_2024", "2022_2024"]:
            comb_dir = self.change_results_dir / year_comb
            if not comb_dir.exists():
                continue
            
            for result_file in comb_dir.glob("*_result.json"):
                try:
                    with open(result_file, 'r') as f:
                        result_data = json.load(f)
                    
                    pair_id = result_data.get("pair_id", "")
                    
                    # Get temporal pair reference
                    temporal_pair = session.query(TemporalPair).filter(TemporalPair.pair_id == pair_id).first()
                    if not temporal_pair:
                        self.stats["change_results"]["failed"] += 1
                        continue
                    
                    # Check if result already exists
                    existing = session.query(ChangeResult).filter(
                        ChangeResult.pair_id == temporal_pair.id,
                        ChangeResult.method == result_data.get("model_used", "baseline")
                    ).first()
                    
                    if existing:
                        self.stats["change_results"]["skipped"] += 1
                        continue
                    
                    change_result = ChangeResult(
                        pair_id=temporal_pair.id,
                        method=result_data.get("model_used", "baseline"),
                        change_percentage=result_data.get("change_percentage", 0.0),
                        confidence=result_data.get("confidence", 0.0),
                        change_mask_path=result_data.get("change_mask_path", ""),
                        result_path=str(result_file),
                        model_name="ChangeFormer" if "changeformer" in result_data.get("model_used", "").lower() else "Baseline",
                        model_version="1.0",
                        processing_time=result_data.get("processing_time", 0.0)
                    )
                    
                    session.add(change_result)
                    self.stats["change_results"]["synced"] += 1
                
                except Exception as e:
                    print(f"  Error processing {result_file}: {e}")
                    self.stats["change_results"]["failed"] += 1
        
        print(f"  Change results: {self.stats['change_results']['synced']} synced, {self.stats['change_results']['skipped']} skipped")
    
    def _synchronize_earliest_changes(self, session: Session):
        """Synchronize earliest change results."""
        print("Synchronizing earliest changes...")
        
        summary_file = self.earliest_changes_dir / "earliest_changes_summary.json"
        if not summary_file.exists():
            print("  No earliest changes summary found")
            return
        
        try:
            with open(summary_file, 'r') as f:
                summary = json.load(f)
            
            for result in summary.get("results", []):
                try:
                    location_ref = result.get("location_reference", "")
                    
                    # Check if already exists
                    existing = session.query(EarliestChange).filter(
                        EarliestChange.location_reference == location_ref
                    ).first()
                    
                    if existing:
                        self.stats["earliest_changes"]["skipped"] += 1
                        continue
                    
                    # Parse dates
                    earliest_date = None
                    before_date = None
                    after_date = None
                    try:
                        if result.get("earliest_change_date") and result["earliest_change_date"] != "N/A":
                            earliest_date = datetime.strptime(result["earliest_change_date"], "%Y-%m-%d")
                        if result.get("before_date") and result["before_date"] != "N/A":
                            before_date = datetime.strptime(result["before_date"], "%Y-%m-%d")
                        if result.get("after_date") and result["after_date"] != "N/A":
                            after_date = datetime.strptime(result["after_date"], "%Y-%m-%d")
                    except:
                        pass
                    
                    earliest_change = EarliestChange(
                        location_reference=location_ref,
                        earliest_change_date=earliest_date or datetime.utcnow(),
                        before_date=before_date or datetime.utcnow(),
                        after_date=after_date or datetime.utcnow(),
                        confidence=result.get("confidence", 0.0),
                        evidence=result.get("evidence_pairs", [])
                    )
                    
                    session.add(earliest_change)
                    self.stats["earliest_changes"]["synced"] += 1
                
                except Exception as e:
                    print(f"  Error processing earliest change: {e}")
                    self.stats["earliest_changes"]["failed"] += 1
        
        print(f"  Earliest changes: {self.stats['earliest_changes']['synced']} synced, {self.stats['earliest_changes']['skipped']} skipped")
    
    def _synchronize_cluster_assignments(self, session: Session):
        """Synchronize cluster assignments."""
        print("Synchronizing cluster assignments...")
        
        assignments_file = self.clusters_dir / "cluster_assignments.json"
        if not assignments_file.exists():
            print("  No cluster assignments found")
            return
        
        try:
            with open(assignments_file, 'r') as f:
                assignments = json.load(f)
            
            for assignment in assignments:
                try:
                    tile_id = assignment.get("tile_id", "")
                    
                    # Get tile reference
                    tile = session.query(Tile).filter(Tile.tile_id == tile_id).first()
                    if not tile:
                        self.stats["cluster_assignments"]["failed"] += 1
                        continue
                    
                    # Check if already exists
                    existing = session.query(ClusterAssignment).filter(
                        ClusterAssignment.tile_id == tile.id
                    ).first()
                    
                    if existing:
                        self.stats["cluster_assignments"]["skipped"] += 1
                        continue
                    
                    cluster_assignment = ClusterAssignment(
                        tile_id=tile.id,
                        cluster_id=assignment.get("cluster_id", -1),
                        cluster_probability=assignment.get("cluster_probability", 0.0),
                        is_noise=assignment.get("is_noise", False),
                        embedding_model=assignment.get("embedding_model", "Clay v1.5")
                    )
                    
                    session.add(cluster_assignment)
                    self.stats["cluster_assignments"]["synced"] += 1
                
                except Exception as e:
                    print(f"  Error processing cluster assignment: {e}")
                    self.stats["cluster_assignments"]["failed"] += 1
        
        print(f"  Cluster assignments: {self.stats['cluster_assignments']['synced']} synced, {self.stats['cluster_assignments']['skipped']} skipped")
    
    def record_processing_history(self, session: Session, phase: str, operation: str, 
                                 entity_type: str, entity_id: str, status: str,
                                 model_name: str = None, model_version: str = None,
                                 parameters: dict = None, error_message: str = None):
        """Record processing history for provenance."""
        history = ProcessingHistory(
            entity_type=entity_type,
            entity_id=entity_id,
            phase=phase,
            operation=operation,
            model_name=model_name,
            model_version=model_version,
            parameters=parameters,
            status=status,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow() if status == "success" else None,
            error_message=error_message
        )
        
        session.add(history)
