"""
Phase 14 - Database Sync CLI
Synchronize existing Phase 2-13 outputs with PostgreSQL/PostGIS
"""

import sys
import argparse
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from app.database.connection import get_db_session
from app.database.models import Scene, Tile, TemporalPair, ChangeResult, ClusterAssignment, ProcessingHistory
from app.database.repository import SceneRepository, TileRepository, TemporalPairRepository, ChangeResultRepository, ClusterAssignmentRepository, ProcessingHistoryRepository


def sync_scenes(session):
    """Sync Phase 2/3 SAFE ingestion metadata"""
    print("Syncing scenes from Phase 2/3...")
    
    scene_repo = SceneRepository(session)
    history_repo = ProcessingHistoryRepository(session)
    
    # Look for SAFE metadata in data/processed/ or similar
    processed_dir = Path("data/processed")
    
    if not processed_dir.exists():
        print("No processed data directory found")
        return
    
    # Scan for scene metadata files
    scene_count = 0
    for scene_dir in processed_dir.iterdir():
        if scene_dir.is_dir():
            # Look for metadata file
            metadata_file = scene_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Create scene data
                    scene_data = {
                        'scene_id': metadata.get('scene_id', ''),
                        'sensor': metadata.get('sensor', 'Sentinel-2'),
                        'satellite': metadata.get('satellite', 'Sentinel-2'),
                        'acquisition_date': datetime.fromisoformat(metadata.get('acquisition_date', '')),
                        'source_path': str(scene_dir),
                        'crs': metadata.get('crs', ''),
                        'width': metadata.get('width', 0),
                        'height': metadata.get('height', 0),
                        'processing_status': 'completed'
                    }
                    
                    # Get or create scene
                    scene = scene_repo.get_or_create(scene_data)
                    
                    # Record processing history
                    history_data = {
                        'entity_type': 'scene',
                        'entity_id': scene.scene_id,
                        'phase': 'Phase 2/3',
                        'operation': 'ingestion',
                        'model_name': None,
                        'model_version': None,
                        'parameters': metadata,
                        'status': 'success',
                        'started_at': datetime.utcnow(),
                        'completed_at': datetime.utcnow(),
                        'error_message': None
                    }
                    history_repo.create(history_data)
                    
                    scene_count += 1
                    
                except Exception as e:
                    print(f"Error syncing scene {scene_dir}: {e}")
                    session.rollback()
    
    print(f"Synced {scene_count} scenes")


def sync_tiles(session):
    """Sync Phase 5 tiles"""
    print("Syncing tiles from Phase 5...")
    
    tile_repo = TileRepository(session)
    history_repo = ProcessingHistoryRepository(session)
    
    tiles_dir = Path("data/tiles")
    
    if not tiles_dir.exists():
        print("No tiles directory found")
        return
    
    tile_count = 0
    for year_dir in tiles_dir.iterdir():
        if year_dir.is_dir() and year_dir.name in ["2022", "2023", "2024"]:
            for tile_dir in year_dir.iterdir():
                if tile_dir.is_dir():
                    metadata_file = tile_dir / "metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                            
                            # Convert bbox to WKT for PostGIS
                            bbox = metadata.get('bbox', {})
                            min_lon = bbox['min_lon']
                            min_lat = bbox['min_lat']
                            max_lon = bbox['max_lon']
                            max_lat = bbox['max_lat']
                            # Create proper closed polygon with 5 points
                            bbox_wkt = f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
                            
                            # Extract year from tile_id if not in metadata
                            tile_id = metadata['tile_id']
                            year = metadata.get('year')
                            if not year:
                                year = tile_id.split('_')[0]  # Extract from "2024_T43QFV_000480"
                            
                            tile_data = {
                                'tile_id': tile_id,
                                'year': year,
                                'acquisition_date': datetime.fromisoformat(metadata['date']),
                                'latitude': metadata['latitude'],
                                'longitude': metadata['longitude'],
                                'bbox': bbox_wkt,
                                'crs': metadata['crs'],
                                'resolution': metadata['resolution'],
                                'width': metadata['width'],
                                'height': metadata['height'],
                                'valid_percentage': metadata['valid_percentage'],
                                'source_path': str(tile_dir)
                            }
                            
                            # Get or create tile
                            tile = tile_repo.get_or_create(tile_data)
                            
                            # Record processing history
                            history_data = {
                                'entity_type': 'tile',
                                'entity_id': tile.tile_id,
                                'phase': 'Phase 5',
                                'operation': 'tiling',
                                'model_name': None,
                                'model_version': None,
                                'parameters': metadata,
                                'status': 'success',
                                'started_at': datetime.utcnow(),
                                'completed_at': datetime.utcnow(),
                                'error_message': None
                            }
                            history_repo.create(history_data)
                            
                            tile_count += 1
                            
                        except Exception as e:
                            print(f"Error syncing tile {tile_dir}: {e}")
                            session.rollback()
    
    print(f"Synced {tile_count} tiles")


def sync_temporal_pairs(session):
    """Sync Phase 10 temporal pairs"""
    print("Syncing temporal pairs from Phase 10...")
    
    pair_repo = TemporalPairRepository(session)
    history_repo = ProcessingHistoryRepository(session)
    
    pairs_dir = Path("data/temporal_pairs")
    
    if not pairs_dir.exists():
        print("No temporal pairs directory found")
        return
    
    pair_count = 0
    for year_comb in ["2022_2023", "2023_2024", "2022_2024"]:
        year_dir = pairs_dir / year_comb
        if not year_dir.exists():
            continue
        
        for pair_file in year_dir.glob("*.json"):
            try:
                with open(pair_file, 'r') as f:
                    pair_data = json.load(f)
                
                # Get before and after tiles
                before_tile = session.query(Tile).filter(Tile.tile_id == pair_data['before_tile_id']).first()
                after_tile = session.query(Tile).filter(Tile.tile_id == pair_data['after_tile_id']).first()
                
                if not before_tile or not after_tile:
                    print(f"Skipping pair {pair_data['pair_id']}: tiles not found in database")
                    continue
                
                # Convert bbox to WKT
                bbox = pair_data.get('bbox', {})
                min_lon = bbox['min_lon']
                min_lat = bbox['min_lat']
                max_lon = bbox['max_lon']
                max_lat = bbox['max_lat']
                # Create proper closed polygon with 5 points
                bbox_wkt = f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
                
                temporal_pair_data = {
                    'pair_id': pair_data['pair_id'],
                    'before_tile_id': before_tile.id,
                    'after_tile_id': after_tile.id,
                    'before_date': datetime.fromisoformat(pair_data['before_date']),
                    'after_date': datetime.fromisoformat(pair_data['after_date']),
                    'bbox': bbox_wkt,
                    'spatial_overlap': pair_data['spatial_overlap']
                }
                
                # Get or create temporal pair
                pair = pair_repo.get_or_create(temporal_pair_data)
                
                # Record processing history
                history_data = {
                    'entity_type': 'temporal_pair',
                    'entity_id': pair.pair_id,
                    'phase': 'Phase 10',
                    'operation': 'temporal_pairing',
                    'model_name': None,
                    'model_version': None,
                    'parameters': pair_data,
                    'status': 'success',
                    'started_at': datetime.utcnow(),
                    'completed_at': datetime.utcnow(),
                    'error_message': None
                }
                history_repo.create(history_data)
                
                pair_count += 1
                
            except Exception as e:
                print(f"Error syncing pair {pair_file}: {e}")
                session.rollback()
    
    print(f"Synced {pair_count} temporal pairs")


def sync_change_results(session):
    """Sync Phase 11 change detection results"""
    print("Syncing change results from Phase 11...")
    
    result_repo = ChangeResultRepository(session)
    history_repo = ProcessingHistoryRepository(session)
    
    results_dir = Path("data/change_results")
    
    if not results_dir.exists():
        print("No change results directory found")
        return
    
    result_count = 0
    for year_comb in ["2022_2023", "2023_2024", "2022_2024"]:
        year_dir = results_dir / year_comb
        if not year_dir.exists():
            continue
        
        for result_file in year_dir.glob("*_result.json"):
            try:
                with open(result_file, 'r') as f:
                    result_data = json.load(f)
                
                # Get temporal pair
                pair = session.query(TemporalPair).filter(TemporalPair.pair_id == result_data['pair_id']).first()
                
                if not pair:
                    print(f"Skipping result {result_data['pair_id']}: pair not found in database")
                    continue
                
                change_result_data = {
                    'pair_id': pair.id,
                    'method': result_data['model_used'],
                    'change_percentage': result_data['change_percentage'],
                    'confidence': result_data['confidence'],
                    'change_mask_path': result_data['change_mask_path'],
                    'result_path': str(result_file),
                    'model_name': result_data.get('model_name', ''),
                    'model_version': result_data.get('model_version', ''),
                    'processing_time': result_data['processing_time']
                }
                
                # Create change result
                result = result_repo.create(change_result_data)
                
                # Record processing history
                history_data = {
                    'entity_type': 'change_result',
                    'entity_id': result_data['pair_id'],
                    'phase': 'Phase 11',
                    'operation': 'change_detection',
                    'model_name': result_data.get('model_name', ''),
                    'model_version': result_data.get('model_version', ''),
                    'parameters': result_data,
                    'status': 'success',
                    'started_at': datetime.utcnow(),
                    'completed_at': datetime.utcnow(),
                    'error_message': None
                }
                history_repo.create(history_data)
                
                result_count += 1
                
            except Exception as e:
                print(f"Error syncing result {result_file}: {e}")
                session.rollback()
    
    print(f"Synced {result_count} change results")


def sync_cluster_assignments(session):
    """Sync Phase 13 cluster assignments"""
    print("Syncing cluster assignments from Phase 13...")
    
    cluster_repo = ClusterAssignmentRepository(session)
    history_repo = ProcessingHistoryRepository(session)
    
    assignments_file = Path("data/clusters/cluster_assignments.json")
    
    if not assignments_file.exists():
        print("No cluster assignments file found")
        return
    
    try:
        with open(assignments_file, 'r') as f:
            assignments_data = json.load(f)
        
        assignment_count = 0
        for assignment_data in assignments_data:
            # Get tile
            tile = session.query(Tile).filter(Tile.tile_id == assignment_data['tile_id']).first()
            
            if not tile:
                print(f"Skipping assignment for {assignment_data['tile_id']}: tile not found in database")
                continue
            
            cluster_assignment_data = {
                'tile_id': tile.id,
                'cluster_id': assignment_data['cluster_id'],
                'cluster_probability': assignment_data['membership_score'],
                'is_noise': assignment_data['is_outlier'],
                'embedding_model': assignment_data['embedding_source']
            }
            
            # Get or create cluster assignment
            assignment = cluster_repo.get_or_create(cluster_assignment_data)
            
            # Record processing history
            history_data = {
                'entity_type': 'cluster_assignment',
                'entity_id': assignment_data['tile_id'],
                'phase': 'Phase 13',
                'operation': 'clustering',
                'model_name': None,
                'model_version': None,
                'parameters': assignment_data,
                'status': 'success',
                'started_at': datetime.utcnow(),
                'completed_at': datetime.utcnow(),
                'error_message': None
            }
            history_repo.create(history_data)
            
            assignment_count += 1
        
        print(f"Synced {assignment_count} cluster assignments")
        
    except Exception as e:
        print(f"Error syncing cluster assignments: {e}")
        session.rollback()


def main():
    parser = argparse.ArgumentParser(description="Phase 14: Database Sync")
    parser.add_argument("--scenes", action="store_true",
                       help="Sync scenes from Phase 2/3")
    parser.add_argument("--tiles", action="store_true",
                       help="Sync tiles from Phase 5")
    parser.add_argument("--pairs", action="store_true",
                       help="Sync temporal pairs from Phase 10")
    parser.add_argument("--changes", action="store_true",
                       help="Sync change results from Phase 11")
    parser.add_argument("--clusters", action="store_true",
                       help="Sync cluster assignments from Phase 13")
    parser.add_argument("--all", action="store_true",
                       help="Sync all Phase 2-13 data")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("PHASE 14: DATABASE SYNC")
    print("=" * 60)
    
    with get_db_session() as session:
        if args.scenes or args.all:
            sync_scenes(session)
        
        if args.tiles or args.all:
            sync_tiles(session)
        
        if args.pairs or args.all:
            sync_temporal_pairs(session)
        
        if args.changes or args.all:
            sync_change_results(session)
        
        if args.clusters or args.all:
            sync_cluster_assignments(session)
    
    print("\nDatabase sync completed successfully!")


if __name__ == "__main__":
    main()
