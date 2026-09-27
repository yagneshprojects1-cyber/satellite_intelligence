"""
Cluster Discovery - Phase 13
Find similar locations within the same cluster using Clay embeddings
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from .clustering import EmbeddingClusterer


def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


@dataclass
class SimilarLocation:
    """Data class for similar location result"""
    rank: int
    tile_id: str
    similarity: float
    cluster_id: int
    date: str
    latitude: float
    longitude: float
    bbox: Dict[str, float]
    sensor: str
    source_scene: str
    tile_path: str


class ClusterDiscovery:
    """
    Discovers similar locations within the same cluster using Clay embeddings.
    """
    
    def __init__(self, 
                 embeddings_dir: Path = Path("embeddings"),
                 clusters_dir: Path = Path("data/clusters")):
        """
        Initialize cluster discovery.
        
        Args:
            embeddings_dir: Directory containing Phase 6 embeddings
            clusters_dir: Directory containing clustering results
        """
        self.embeddings_dir = Path(embeddings_dir)
        self.clusters_dir = Path(clusters_dir)
        
        # Initialize clusterer for access to cluster assignments
        self.clusterer = EmbeddingClusterer(
            embeddings_dir=embeddings_dir,
            output_dir=clusters_dir
        )
    
    def _load_tile_embedding(self, tile_id: str, year: str) -> Optional[np.ndarray]:
        """
        Load Clay embedding for a specific tile.
        
        Args:
            tile_id: Tile identifier
            year: Year directory
            
        Returns:
            Embedding array or None if failed
        """
        embedding_path = self.embeddings_dir / year / f"{tile_id}.npy"
        
        if not embedding_path.exists():
            return None
        
        try:
            return np.load(embedding_path)
        except Exception as e:
            print(f"Error loading embedding for {tile_id}: {e}")
            return None
    
    def _find_tile_year(self, tile_id: str) -> Optional[str]:
        """
        Find the year directory for a specific tile.
        
        Args:
            tile_id: Tile identifier
            
        Returns:
            Year string or None if not found
        """
        for year_dir in self.embeddings_dir.iterdir():
            if year_dir.is_dir() and year_dir.name in ["2022", "2023", "2024"]:
                embedding_file = year_dir / f"{tile_id}.npy"
                if embedding_file.exists():
                    return year_dir.name
        return None
    
    def _load_tile_metadata(self, tile_id: str, year: str) -> Optional[Dict]:
        """
        Load tile metadata from embedding JSON.
        
        Args:
            tile_id: Tile identifier
            year: Year directory
            
        Returns:
            Metadata dictionary or None if failed
        """
        metadata_file = self.embeddings_dir / year / f"{tile_id}.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata for {tile_id}: {e}")
            return None
    
    def find_similar_locations(self, 
                               tile_id: str, 
                               top_k: int = 10,
                               include_query_tile: bool = False) -> List[SimilarLocation]:
        """
        Find similar locations within the same cluster.
        
        Args:
            tile_id: Query tile identifier
            top_k: Number of similar locations to return
            include_query_tile: Whether to include the query tile in results
            
        Returns:
            List of similar locations ranked by similarity
        """
        print(f"Finding similar locations for tile: {tile_id}")
        
        # Find year for query tile
        query_year = self._find_tile_year(tile_id)
        if query_year is None:
            raise ValueError(f"Tile {tile_id} not found in embeddings")
        
        # Get cluster for query tile
        query_cluster = self.clusterer.get_tile_cluster(tile_id)
        if query_cluster is None:
            raise ValueError(f"Tile {tile_id} not found in cluster assignments")
        
        if query_cluster == -1:
            print(f"Warning: Tile {tile_id} is marked as noise/outlier")
        
        print(f"Query tile cluster: {query_cluster}")
        
        # Load query embedding
        query_embedding = self._load_tile_embedding(tile_id, query_year)
        if query_embedding is None:
            raise ValueError(f"Failed to load embedding for {tile_id}")
        
        # Get cluster members
        cluster_members = self.clusterer.get_cluster_members(query_cluster)
        print(f"Cluster {query_cluster} has {len(cluster_members)} members")
        
        # Calculate similarities
        similarities = []
        
        for member in cluster_members:
            # Skip query tile if not requested
            if not include_query_tile and member.tile_id == tile_id:
                continue
            
            # Load member embedding
            member_embedding = self._load_tile_embedding(member.tile_id, member.year)
            if member_embedding is None:
                continue
            
            # Calculate cosine similarity
            similarity = cosine_similarity(query_embedding, member_embedding)
            
            # Load member metadata
            metadata = self._load_tile_metadata(member.tile_id, member.year)
            if metadata is None:
                continue
            
            similar_location = SimilarLocation(
                rank=0,  # Will be assigned after sorting
                tile_id=member.tile_id,
                similarity=float(similarity),
                cluster_id=member.cluster_id,
                date=member.date,
                latitude=member.latitude,
                longitude=member.longitude,
                bbox=member.bbox,
                sensor=member.sensor,
                source_scene=metadata.get('source_scene', ''),
                tile_path=member.tile_path
            )
            
            similarities.append(similar_location)
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x.similarity, reverse=True)
        
        # Assign ranks
        for i, loc in enumerate(similarities[:top_k]):
            loc.rank = i + 1
        
        return similarities[:top_k]
    
    def find_similar_locations_cross_year(self,
                                         tile_id: str,
                                         target_year: str,
                                         top_k: int = 10,
                                         include_query_tile: bool = False) -> List[SimilarLocation]:
        """
        Find similar locations in a specific year within the same cluster.
        
        Args:
            tile_id: Query tile identifier
            target_year: Target year for results (e.g., "2023")
            top_k: Number of similar locations to return
            
        Returns:
            List of similar locations ranked by similarity
        """
        print(f"Finding similar locations for tile: {tile_id} in year: {target_year}")
        
        # Get cluster for query tile
        query_cluster = self.clusterer.get_tile_cluster(tile_id)
        if query_cluster is None:
            raise ValueError(f"Tile {tile_id} not found in cluster assignments")
        
        # Get cluster members
        cluster_members = self.clusterer.get_cluster_members(query_cluster)
        
        # Filter by target year
        target_members = [m for m in cluster_members if m.year == target_year]
        print(f"Found {len(target_members)} members in year {target_year}")
        
        if not target_members:
            return []
        
        # Find query year
        query_year = self._find_tile_year(tile_id)
        
        # Load query embedding
        query_embedding = self._load_tile_embedding(tile_id, query_year)
        if query_embedding is None:
            raise ValueError(f"Failed to load embedding for {tile_id}")
        
        # Calculate similarities
        similarities = []
        
        for member in target_members:
            # Skip query tile if not requested
            if not include_query_tile and member.tile_id == tile_id:
                continue
            member_embedding = self._load_tile_embedding(member.tile_id, member.year)
            if member_embedding is None:
                continue
            
            # Calculate cosine similarity
            similarity = cosine_similarity(query_embedding, member_embedding)
            
            # Load member metadata
            metadata = self._load_tile_metadata(member.tile_id, member.year)
            if metadata is None:
                continue
            
            similar_location = SimilarLocation(
                rank=0,
                tile_id=member.tile_id,
                similarity=float(similarity),
                cluster_id=member.cluster_id,
                date=member.date,
                latitude=member.latitude,
                longitude=member.longitude,
                bbox=member.bbox,
                sensor=member.sensor,
                source_scene=metadata.get('source_scene', ''),
                tile_path=member.tile_path
            )
            
            similarities.append(similar_location)
        
        # Sort by similarity
        similarities.sort(key=lambda x: x.similarity, reverse=True)
        
        # Assign ranks
        for i, loc in enumerate(similarities[:top_k]):
            loc.rank = i + 1
        
        return similarities[:top_k]
