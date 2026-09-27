"""
Dashboard services layer
Reuses existing Phase 8, 9, 11, 12, 13 modules
Phase 15: Streamlit Analyst Dashboard
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

# Import existing pipeline modules
from app.semantic.semantic_search import SemanticSearch
from app.semantic.text_encoder import CLIPTextEncoder
from app.clustering.cluster_discovery import ClusterDiscovery


class SemanticSearchService:
    """Service for text-to-image semantic search (Phase 8)"""
    
    def __init__(self):
        self.search_engine = None
        self.text_encoder = None
        self._initialized = False
    
    def initialize(self):
        """Lazy initialization"""
        if not self._initialized:
            qdrant_storage_path = os.getenv('QDRANT_STORAGE', 'qdrant_storage')
            clip_collection = os.getenv('CLIP_COLLECTION', 'satellite_tiles_clip')
            
            # Initialize search engine
            self.search_engine = SemanticSearch(
                qdrant_storage_path=qdrant_storage_path,
                clip_collection_name=clip_collection
            )
            self.text_encoder = CLIPTextEncoder()
            self._initialized = True
    
    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform text-to-image search.
        
        Args:
            query: Natural language query
            top_k: Number of results to return
            
        Returns:
            List of search results with metadata
        """
        self.initialize()
        
        # Search
        results = self.search_engine.search(query, top_k=top_k)
        
        return results


class ImageSearchService:
    """Service for image-to-image search (Phase 9)"""
    
    def __init__(self):
        self.search_engine = None
        self._initialized = False
    
    def initialize(self):
        """Lazy initialization"""
        if not self._initialized:
            qdrant_storage_path = os.getenv('QDRANT_STORAGE', 'qdrant_storage')
            clip_collection = os.getenv('CLIP_COLLECTION', 'satellite_tiles_clip')
            
            # Initialize search engine
            self.search_engine = SemanticSearch(
                qdrant_storage_path=qdrant_storage_path,
                clip_collection_name=clip_collection
            )
            self._initialized = True
    
    def search_by_image(self, tile_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform image-to-image search.
        
        Args:
            tile_id: Reference tile ID
            top_k: Number of results to return
            
        Returns:
            List of similar tiles with metadata
        """
        self.initialize()
        
        # Search by image
        results = self.search_engine.search_by_image(tile_id, top_k=top_k)
        
        return results


class ChangeAnalysisService:
    """Service for change detection analysis (Phase 11)"""
    
    def __init__(self):
        self._initialized = False
    
    def initialize(self):
        """Lazy initialization"""
        if not self._initialized:
            self._initialized = True
    
    def get_change_result(self, pair_id: str) -> Optional[Dict[str, Any]]:
        """
        Get change detection result for a temporal pair.
        
        Args:
            pair_id: Temporal pair ID
            
        Returns:
            Change result with metadata
        """
        # Load from saved results
        change_results_dir = Path(os.getenv('CHANGE_RESULTS_DIR', 'data/change_results'))
        
        # Try to find the result file
        for year_comb in ["2022_2023", "2023_2024", "2022_2024"]:
            result_file = change_results_dir / year_comb / f"{pair_id}_result.json"
            if result_file.exists():
                with open(result_file, 'r') as f:
                    return json.load(f)
        
        return None
    
    def list_change_results(self, year_comb: str = None) -> List[Dict[str, Any]]:
        """
        List change detection results.
        
        Args:
            year_comb: Year combination (e.g., "2022_2023")
            
        Returns:
            List of change results
        """
        change_results_dir = Path(os.getenv('CHANGE_RESULTS_DIR', 'data/change_results'))
        results = []
        
        if year_comb:
            year_dirs = [change_results_dir / year_comb]
        else:
            year_dirs = [
                change_results_dir / "2022_2023",
                change_results_dir / "2023_2024",
                change_results_dir / "2022_2024"
            ]
        
        for year_dir in year_dirs:
            if year_dir.exists():
                for result_file in year_dir.glob("*_result.json"):
                    with open(result_file, 'r') as f:
                        results.append(json.load(f))
        
        return results


class EarliestChangeService:
    """Service for earliest change detection (Phase 12)"""
    
    def __init__(self):
        self._initialized = False
    
    def initialize(self):
        """Lazy initialization"""
        if not self._initialized:
            self._initialized = True
    
    def get_earliest_change_for_tile(self, tile_id: str) -> Optional[Dict[str, Any]]:
        """
        Get earliest detected change for a specific tile across all temporal pairs.
        
        Args:
            tile_id: Tile identifier
            
        Returns:
            Earliest change with evidence or None if no change detected
        """
        # Load all change results
        change_results_dir = Path(os.getenv('CHANGE_RESULTS_DIR', 'data/change_results'))
        temporal_pairs_dir = Path(os.getenv('TEMPORAL_PAIRS_DIR', 'data/temporal_pairs'))
        
        all_changes = []
        
        # Scan all year combinations
        for year_comb in ["2022_2023", "2023_2024", "2022_2024"]:
            # Load change results
            year_dir = change_results_dir / year_comb
            if year_dir.exists():
                for result_file in year_dir.glob("*_result.json"):
                    with open(result_file, 'r') as f:
                        result = json.load(f)
                    
                    # Load corresponding temporal pair
                    pair_file = temporal_pairs_dir / year_comb / f"{result['pair_id']}.json"
                    if pair_file.exists():
                        with open(pair_file, 'r') as f:
                            pair_data = json.load(f)
                        
                        # Check if this tile is involved
                        if tile_id in [pair_data.get('before_tile_id'), pair_data.get('after_tile_id')]:
                            all_changes.append({
                                'year_comb': year_comb,
                                'pair_id': result['pair_id'],
                                'before_date': result['before_date'],
                                'after_date': result['after_date'],
                                'change_percentage': result['change_percentage'],
                                'confidence': result['confidence'],
                                'method': result['model_used'],
                                'change_mask_path': result['change_mask_path'],
                                'before_path': pair_data.get('before_path'),
                                'after_path': pair_data.get('after_path')
                            })
        
        if not all_changes:
            return None
        
        # Sort by before_date to find earliest
        all_changes.sort(key=lambda x: x['before_date'])
        
        # Return earliest change
        return all_changes[0]
    
    def get_earliest_change(self, location_id: str) -> Optional[Dict[str, Any]]:
        """
        Get earliest detected change for a location.
        
        Args:
            location_id: Location identifier (tile_id or coordinate)
            
        Returns:
            Earliest change with evidence
        """
        return self.get_earliest_change_for_tile(location_id)


class SimilarLocationsService:
    """Service for similar location discovery (Phase 13)"""
    
    def __init__(self):
        self.cluster_discovery = None
        self._initialized = False
    
    def initialize(self):
        """Lazy initialization"""
        if not self._initialized:
            embeddings_dir = Path(os.getenv('EMBEDDINGS_DIR', 'embeddings'))
            clusters_dir = Path(os.getenv('CLUSTERS_DIR', 'data/clusters'))
            self.cluster_discovery = ClusterDiscovery(
                embeddings_dir=embeddings_dir,
                clusters_dir=clusters_dir
            )
            self._initialized = True
    
    def find_similar_locations(self, tile_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Find similar locations using clustering.
        
        Args:
            tile_id: Reference tile ID
            top_k: Number of results to return
            
        Returns:
            List of similar locations with metadata
        """
        self.initialize()
        
        # Find similar locations
        results = self.cluster_discovery.find_similar_locations(tile_id, top_k=top_k)
        
        return results
    
    def get_cluster_info(self, tile_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cluster information for a tile.
        
        Args:
            tile_id: Tile ID
            
        Returns:
            Cluster information
        """
        self.initialize()
        
        # Load cluster assignments
        assignments_file = Path(os.getenv('CLUSTERS_DIR', 'data/clusters')) / 'cluster_assignments.json'
        if assignments_file.exists():
            with open(assignments_file, 'r') as f:
                assignments = json.load(f)
            
            for assignment in assignments:
                if assignment['tile_id'] == tile_id:
                    return assignment
        
        return None


class AnalystReviewService:
    """Service for analyst review and decisions"""
    
    def __init__(self):
        self._initialized = False
    
    def initialize(self):
        """Lazy initialization"""
        if not self._initialized:
            self._initialized = True
    
    def save_review(self, change_result_id: str, decision: str, 
                   change_type: str, comment: str = None) -> Dict[str, Any]:
        """
        Save analyst review to database.
        
        Args:
            change_result_id: Change result ID
            decision: 'confirmed' or 'rejected'
            change_type: Change type classification
            comment: Optional analyst comment
            
        Returns:
            Saved review
        """
        from app.database.connection import get_db_session
        from app.database.models import AnalystReview
        from app.database.repository import AnalystReviewRepository
        from datetime import datetime
        
        with get_db_session() as session:
            review_repo = AnalystReviewRepository(session)
            
            review_data = {
                'change_result_id': change_result_id,
                'decision': decision,
                'change_type': change_type,
                'analyst_comment': comment,
                'analyst_id': 'system',  # Would be user ID in production
                'reviewed_at': datetime.utcnow()
            }
            
            review = review_repo.create(review_data)
            
            return {
                'id': str(review.id),
                'decision': review.decision,
                'change_type': review.change_type,
                'reviewed_at': review.reviewed_at.isoformat()
            }


class MapDataService:
    """Service for map data visualization"""
    
    def __init__(self):
        self._initialized = False
    
    def initialize(self):
        """Lazy initialization"""
        if not self._initialized:
            self._initialized = True
    
    def get_all_tiles(self) -> List[Dict[str, Any]]:
        """
        Get all tiles for map visualization.
        
        Returns:
            List of tiles with coordinates
        """
        tiles_dir = Path(os.getenv('TILES_DIR', 'data/tiles'))
        tiles = []
        
        for year_dir in tiles_dir.iterdir():
            if year_dir.is_dir() and year_dir.name in ["2022", "2023", "2024"]:
                for tile_dir in year_dir.iterdir():
                    if tile_dir.is_dir():
                        metadata_file = tile_dir / "metadata.json"
                        if metadata_file.exists():
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                            
                            # Extract year from tile_id if not in metadata
                            tile_id = metadata['tile_id']
                            year = metadata.get('year')
                            if not year:
                                year = tile_id.split('_')[0]
                            
                            tiles.append({
                                'tile_id': tile_id,
                                'year': year,
                                'latitude': metadata['latitude'],
                                'longitude': metadata['longitude'],
                                'bbox': metadata['bbox'],
                                'date': metadata['date']
                            })
        
        return tiles
    
    def get_change_locations(self) -> List[Dict[str, Any]]:
        """
        Get change locations for map visualization.
        
        Returns:
            List of change locations
        """
        change_results_dir = Path(os.getenv('CHANGE_RESULTS_DIR', 'data/change_results'))
        changes = []
        
        for year_comb in ["2022_2023", "2023_2024", "2022_2024"]:
            year_dir = change_results_dir / year_comb
            if year_dir.exists():
                for result_file in year_dir.glob("*_result.json"):
                    with open(result_file, 'r') as f:
                        result = json.load(f)
                    
                    # Extract location from pair metadata
                    changes.append({
                        'pair_id': result['pair_id'],
                        'change_percentage': result['change_percentage'],
                        'confidence': result['confidence'],
                        'before_date': result['before_date'],
                        'after_date': result['after_date'],
                        'bbox': result.get('bbox', {})
                    })
        
        return changes
