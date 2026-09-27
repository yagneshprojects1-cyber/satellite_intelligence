"""
Clay Clustering Module - Phase 13
HDBSCAN clustering using Clay embeddings for location similarity
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hdbscan


class ClusterStatus(Enum):
    """Cluster membership status"""
    CLUSTERED = "Clustered"
    NOISE = "Noise"
    OUTLIER = "Outlier"


@dataclass
class ClusterAssignment:
    """Data class for cluster assignment"""
    tile_id: str
    cluster_id: int
    cluster_probability: float
    is_noise: bool
    embedding_model: str
    cluster_method: str
    parameters: Dict[str, any]


@dataclass
class ClusterSummary:
    """Data class for cluster summary"""
    cluster_id: int
    size: int
    mean_probability: float
    representative_tile_id: str
    characteristics: Dict[str, any]


class ClayClustering:
    """
    HDBSCAN clustering using Clay embeddings.
    
    IMPORTANT: This requires complete Clay embeddings (983 total).
    Current status: 115/983 embeddings available (pending Kaggle GPU processing).
    
    Features:
    - HDBSCAN clustering (density-based, no fixed number of clusters)
    - Cluster membership with probability scores
    - Noise/outlier detection
    - Similarity ranking within clusters
    - Cross-year similar-location discovery
    """
    
    def __init__(self,
                 embeddings_dir: Path = Path("embeddings"),
                 output_dir: Path = Path("data/clusters"),
                 min_cluster_size: int = 5,
                 min_samples: int = 5,
                 metric: str = "euclidean",
                 cluster_selection_method: str = "eom"):
        """
        Initialize Clay clustering.
        
        Args:
            embeddings_dir: Directory containing Clay embeddings
            output_dir: Directory for clustering results
            min_cluster_size: Minimum cluster size for HDBSCAN
            min_samples: Minimum samples for core point
            metric: Distance metric for clustering
            cluster_selection_method: Cluster selection method
        """
        self.embeddings_dir = Path(embeddings_dir)
        self.output_dir = Path(output_dir)
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.metric = metric
        self.cluster_selection_method = cluster_selection_method
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize clusterer
        self.clusterer = None
        self.assignments = []
        self.clusters = {}
        
        # Embedding dimension
        self.embedding_dim = 1024
    
    def _load_embeddings(self) -> Tuple[np.ndarray, List[str]]:
        """
        Load all Clay embeddings.
        
        Returns:
            Tuple of (embeddings array, tile_id list)
        """
        embeddings = []
        tile_ids = []
        
        # Load embeddings from all years
        for year in ["2022", "2023", "2024"]:
            year_dir = self.embeddings_dir / year
            if not year_dir.exists():
                continue
            
            for emb_file in year_dir.glob("*.npy"):
                try:
                    # Load embedding
                    emb = np.load(emb_file)
                    
                    # Validate dimension
                    if emb.shape[0] != self.embedding_dim:
                        print(f"Warning: Embedding {emb_file} has invalid shape {emb.shape}")
                        continue
                    
                    embeddings.append(emb)
                    
                    # Extract tile_id from filename
                    tile_id = emb_file.stem
                    tile_ids.append(tile_id)
                    
                except Exception as e:
                    print(f"Error loading embedding {emb_file}: {e}")
        
        if not embeddings:
            raise ValueError("No embeddings found. Please complete Phase 6 first.")
        
        embeddings_array = np.stack(embeddings, axis=0)
        
        print(f"Loaded {len(embeddings)} embeddings")
        print(f"Embedding shape: {embeddings_array.shape}")
        
        return embeddings_array, tile_ids
    
    def _load_embedding_metadata(self, tile_id: str) -> Optional[Dict]:
        """
        Load metadata for a specific embedding.
        
        Args:
            tile_id: Tile identifier
            
        Returns:
            Metadata dictionary or None
        """
        # Determine year from tile_id
        year = tile_id.split("_")[0]
        metadata_file = self.embeddings_dir / year / f"{tile_id}.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata for {tile_id}: {e}")
            return None
    
    def cluster(self) -> Dict[str, any]:
        """
        Perform HDBSCAN clustering on Clay embeddings.
        
        Returns:
            Summary dictionary
        """
        print("=" * 60)
        print("PHASE 13: CLAY EMBEDDING CLUSTERING")
        print("=" * 60)
        print(f"Embeddings directory: {self.embeddings_dir}")
        print(f"Output directory: {self.output_dir}")
        print(f"Min cluster size: {self.min_cluster_size}")
        print(f"Min samples: {self.min_samples}")
        print(f"Metric: {self.metric}")
        print()
        
        # Load embeddings
        embeddings, tile_ids = self._load_embeddings()
        
        # Initialize HDBSCAN clusterer
        print("Initializing HDBSCAN clusterer...")
        self.clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            metric=self.metric,
            cluster_selection_method=self.cluster_selection_method,
            prediction_data=True
        )
        
        # Fit clusterer
        print("Fitting clusterer...")
        cluster_labels = self.clusterer.fit_predict(embeddings)
        
        # Get probabilities
        probabilities = self.clusterer.probabilities_
        
        print(f"Clustering complete")
        print(f"  Total points: {len(cluster_labels)}")
        print(f"  Number of clusters: {len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)}")
        print(f"  Noise points: {sum(cluster_labels == -1)}")
        
        # Create assignments
        self.assignments = []
        for i, (tile_id, label, prob) in enumerate(zip(tile_ids, cluster_labels, probabilities)):
            assignment = ClusterAssignment(
                tile_id=tile_id,
                cluster_id=int(label),
                cluster_probability=float(prob),
                is_noise=bool(label == -1),
                embedding_model="Clay v1.5",
                cluster_method="HDBSCAN",
                parameters={
                    "min_cluster_size": self.min_cluster_size,
                    "min_samples": self.min_samples,
                    "metric": self.metric,
                    "cluster_selection_method": self.cluster_selection_method
                }
            )
            self.assignments.append(assignment)
        
        # Generate cluster summaries
        self._generate_cluster_summaries()
        
        # Save results
        summary = self._save_results()
        
        print("=" * 60)
        print("CLUSTERING SUMMARY")
        print("=" * 60)
        print(f"Total tiles clustered: {len(self.assignments)}")
        print(f"Number of clusters: {len(self.clusters)}")
        print(f"Noise/outlier tiles: {sum(a.is_noise for a in self.assignments)}")
        print(f"Summary saved to: {self.output_dir / 'clustering_summary.json'}")
        print("=" * 60)
        
        return summary
    
    def _generate_cluster_summaries(self):
        """Generate summary statistics for each cluster."""
        self.clusters = {}
        
        # Group assignments by cluster
        cluster_assignments = {}
        for assignment in self.assignments:
            if not assignment.is_noise:
                cluster_id = assignment.cluster_id
                if cluster_id not in cluster_assignments:
                    cluster_assignments[cluster_id] = []
                cluster_assignments[cluster_id].append(assignment)
        
        # Generate summaries
        for cluster_id, assignments in cluster_assignments.items():
            probabilities = [a.cluster_probability for a in assignments]
            
            # Find representative tile (highest probability)
            representative = max(assignments, key=lambda a: a.cluster_probability)
            
            # Calculate cluster characteristics
            characteristics = self._calculate_cluster_characteristics(assignments)
            
            summary = ClusterSummary(
                cluster_id=cluster_id,
                size=len(assignments),
                mean_probability=np.mean(probabilities),
                representative_tile_id=representative.tile_id,
                characteristics=characteristics
            )
            
            self.clusters[cluster_id] = summary
    
    def _calculate_cluster_characteristics(self, assignments: List[ClusterAssignment]) -> Dict[str, any]:
        """
        Calculate characteristics for a cluster.
        
        Args:
            assignments: List of cluster assignments
            
        Returns:
            Dictionary of cluster characteristics
        """
        # Load metadata for tiles in cluster
        years = []
        latitudes = []
        longitudes = []
        
        for assignment in assignments:
            metadata = self._load_embedding_metadata(assignment.tile_id)
            if metadata:
                years.append(metadata.get("year", ""))
                latitudes.append(metadata.get("latitude", 0.0))
                longitudes.append(metadata.get("longitude", 0.0))
        
        characteristics = {
            "year_distribution": {},
            "latitude_range": {},
            "longitude_range": {}
        }
        
        if years:
            # Year distribution
            from collections import Counter
            year_counts = Counter(years)
            characteristics["year_distribution"] = dict(year_counts)
        
        if latitudes:
            characteristics["latitude_range"] = {
                "min": min(latitudes),
                "max": max(latitudes),
                "mean": np.mean(latitudes)
            }
        
        if longitudes:
            characteristics["longitude_range"] = {
                "min": min(longitudes),
                "max": max(longitudes),
                "mean": np.mean(longitudes)
            }
        
        return characteristics
    
    def _save_results(self) -> Dict[str, any]:
        """
        Save clustering results to files.
        
        Returns:
            Summary dictionary
        """
        # Save assignments
        assignments_data = [asdict(a) for a in self.assignments]
        assignments_file = self.output_dir / "cluster_assignments.json"
        with open(assignments_file, 'w') as f:
            json.dump(assignments_data, f, indent=2)
        
        # Save cluster summaries
        clusters_data = {str(k): asdict(v) for k, v in self.clusters.items()}
        clusters_file = self.output_dir / "cluster_summaries.json"
        with open(clusters_file, 'w') as f:
            json.dump(clusters_data, f, indent=2)
        
        # Create summary
        summary = {
            "total_tiles": len(self.assignments),
            "num_clusters": len(self.clusters),
            "num_noise": int(sum(a.is_noise for a in self.assignments)),
            "embedding_model": "Clay v1.5",
            "cluster_method": "HDBSCAN",
            "parameters": {
                "min_cluster_size": self.min_cluster_size,
                "min_samples": self.min_samples,
                "metric": self.metric,
                "cluster_selection_method": self.cluster_selection_method
            },
            "clusters": clusters_data
        }
        
        summary_file = self.output_dir / "clustering_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary
    
    def find_similar_locations(self, 
                              tile_id: str, 
                              top_k: int = 10) -> List[Dict[str, any]]:
        """
        Find similar locations within the same cluster.
        
        Args:
            tile_id: Query tile ID
            top_k: Number of similar locations to return
            
        Returns:
            List of similar locations with metadata
        """
        # Find assignment for query tile
        query_assignment = None
        for assignment in self.assignments:
            if assignment.tile_id == tile_id:
                query_assignment = assignment
                break
        
        if query_assignment is None:
            raise ValueError(f"Tile {tile_id} not found in cluster assignments")
        
        if query_assignment.is_noise:
            print(f"Tile {tile_id} is classified as noise/outlier")
            return []
        
        # Find other tiles in the same cluster
        cluster_id = query_assignment.cluster_id
        cluster_assignments = [a for a in self.assignments 
                             if a.cluster_id == cluster_id and a.tile_id != tile_id]
        
        # Sort by cluster probability
        cluster_assignments.sort(key=lambda a: a.cluster_probability, reverse=True)
        
        # Get top_k
        top_assignments = cluster_assignments[:top_k]
        
        # Enrich with metadata
        results = []
        for assignment in top_assignments:
            metadata = self._load_embedding_metadata(assignment.tile_id)
            result = {
                "tile_id": assignment.tile_id,
                "cluster_id": assignment.cluster_id,
                "cluster_probability": assignment.cluster_probability,
                "rank": len(results) + 1,
                "metadata": metadata if metadata else {}
            }
            results.append(result)
        
        return results
    
    def get_cross_year_similar_locations(self, 
                                       tile_id: str, 
                                       target_year: str) -> List[Dict[str, any]]:
        """
        Find similar locations in a different year.
        
        Args:
            tile_id: Query tile ID
            target_year: Target year (e.g., "2023")
            
        Returns:
            List of similar locations in target year
        """
        # Find assignment for query tile
        query_assignment = None
        for assignment in self.assignments:
            if assignment.tile_id == tile_id:
                query_assignment = assignment
                break
        
        if query_assignment is None:
            raise ValueError(f"Tile {tile_id} not found in cluster assignments")
        
        if query_assignment.is_noise:
            print(f"Tile {tile_id} is classified as noise/outlier")
            return []
        
        # Find tiles in the same cluster from target year
        cluster_id = query_assignment.cluster_id
        target_assignments = []
        
        for assignment in self.assignments:
            if assignment.cluster_id == cluster_id and assignment.tile_id != tile_id:
                metadata = self._load_embedding_metadata(assignment.tile_id)
                if metadata and metadata.get("year") == target_year:
                    target_assignments.append(assignment)
        
        # Sort by cluster probability
        target_assignments.sort(key=lambda a: a.cluster_probability, reverse=True)
        
        # Enrich with metadata
        results = []
        for assignment in target_assignments:
            metadata = self._load_embedding_metadata(assignment.tile_id)
            result = {
                "tile_id": assignment.tile_id,
                "cluster_id": assignment.cluster_id,
                "cluster_probability": assignment.cluster_probability,
                "rank": len(results) + 1,
                "metadata": metadata if metadata else {}
            }
            results.append(result)
        
        return results
