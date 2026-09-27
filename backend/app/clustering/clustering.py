"""
Embedding-Based Clustering - Phase 13
Clusters satellite tiles using Clay embeddings with HDBSCAN
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import uuid

try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False

try:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@dataclass
class ClusterAssignment:
    """Data class for cluster assignment"""
    tile_id: str
    cluster_id: int
    year: str
    date: str
    latitude: float
    longitude: float
    bbox: Dict[str, float]
    sensor: str
    valid_percentage: float
    embedding_source: str
    embedding_dimension: int
    is_outlier: bool
    membership_score: float
    tile_path: str


class EmbeddingClusterer:
    """
    Clusters satellite tiles using Clay embeddings with HDBSCAN.
    Provides embedding-based location discovery.
    """
    
    def __init__(self, 
                 embeddings_dir: Path = Path("embeddings"),
                 output_dir: Path = Path("data/clusters"),
                 pca_components: int = 50,
                 min_cluster_size: int = 5,
                 min_samples: int = 5):
        """
        Initialize embedding clusterer.
        
        Args:
            embeddings_dir: Directory containing Phase 6 embeddings
            output_dir: Directory for clustering results
            pca_components: Number of PCA components for dimensionality reduction
            min_cluster_size: Minimum cluster size for HDBSCAN
            min_samples: Minimum samples for HDBSCAN
        """
        self.embeddings_dir = Path(embeddings_dir)
        self.output_dir = Path(output_dir)
        self.pca_components = pca_components
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "visualization").mkdir(exist_ok=True)
        
        # Initialize PCA and scaler
        self.pca = None
        self.scaler = None
        self.clusterer = None
        
        # Check dependencies
        if not HDBSCAN_AVAILABLE:
            raise ImportError("HDBSCAN is required. Install with: pip install hdbscan")
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required. Install with: pip install scikit-learn")
    
    def _load_embedding_metadata(self, embedding_file: Path) -> Optional[Dict]:
        """
        Load embedding metadata from JSON file.
        
        Args:
            embedding_file: Path to embedding JSON file
            
        Returns:
            Metadata dictionary or None if failed
        """
        try:
            with open(embedding_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata from {embedding_file}: {e}")
            return None
    
    def _load_embedding_array(self, embedding_path: Path) -> Optional[np.ndarray]:
        """
        Load embedding array from .npy file.
        
        Args:
            embedding_path: Path to embedding .npy file
            
        Returns:
            Embedding array or None if failed
        """
        try:
            return np.load(embedding_path)
        except Exception as e:
            print(f"Error loading embedding from {embedding_path}: {e}")
            return None
    
    def _load_all_embeddings(self) -> Tuple[List[Dict], np.ndarray]:
        """
        Load all embeddings from the embeddings directory.
        
        Returns:
            Tuple of (metadata list, embeddings array)
        """
        metadata_list = []
        embeddings_list = []
        
        # Search for embeddings in year directories
        for year_dir in self.embeddings_dir.iterdir():
            if year_dir.is_dir() and year_dir.name in ["2022", "2023", "2024"]:
                print(f"Loading embeddings from {year_dir.name}...")
                
                for json_file in year_dir.glob("*.json"):
                    # Skip if corresponding .npy doesn't exist
                    npy_file = json_file.with_suffix(".npy")
                    if not npy_file.exists():
                        continue
                    
                    # Load metadata
                    metadata = self._load_embedding_metadata(json_file)
                    if metadata is None:
                        continue
                    
                    # Load embedding
                    embedding = self._load_embedding_array(npy_file)
                    if embedding is None:
                        continue
                    
                    metadata_list.append(metadata)
                    embeddings_list.append(embedding)
        
        if not metadata_list:
            raise ValueError("No embeddings found")
        
        embeddings_array = np.array(embeddings_list)
        
        print(f"Loaded {len(metadata_list)} embeddings")
        print(f"Embedding shape: {embeddings_array.shape}")
        
        return metadata_list, embeddings_array
    
    def _normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Normalize embeddings using StandardScaler.
        
        Args:
            embeddings: Embeddings array
            
        Returns:
            Normalized embeddings
        """
        self.scaler = StandardScaler()
        normalized = self.scaler.fit_transform(embeddings)
        return normalized
    
    def _apply_pca(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Apply PCA dimensionality reduction.
        
        Args:
            embeddings: Normalized embeddings
            
        Returns:
            PCA-reduced embeddings
        """
        self.pca = PCA(n_components=self.pca_components)
        reduced = self.pca.fit_transform(embeddings)
        
        explained_variance = self.pca.explained_variance_ratio_.sum()
        print(f"PCA explained variance: {explained_variance:.4f}")
        
        return reduced
    
    def _cluster_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Cluster embeddings using HDBSCAN.
        
        Args:
            embeddings: PCA-reduced embeddings
            
        Returns:
            Cluster labels
        """
        self.clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            metric='euclidean',
            cluster_selection_method='eom'
        )
        
        cluster_labels = self.clusterer.fit_predict(embeddings)
        
        n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
        n_noise = list(cluster_labels).count(-1)
        
        print(f"HDBSCAN clustering completed")
        print(f"Number of clusters: {n_clusters}")
        print(f"Number of noise points: {n_noise}")
        
        return cluster_labels
    
    def _calculate_membership_scores(self, embeddings: np.ndarray, cluster_labels: np.ndarray) -> np.ndarray:
        """
        Calculate membership scores for each point.
        
        Args:
            embeddings: PCA-reduced embeddings
            cluster_labels: Cluster labels from HDBSCAN
            
        Returns:
            Membership scores
        """
        # Use HDBSCAN's membership probability if available
        if hasattr(self.clusterer, 'membership_vector_'):
            membership_scores = self.clusterer.membership_vector_
        else:
            # Fallback: use distance to cluster centroid
            membership_scores = np.ones(len(cluster_labels))
            for cluster_id in set(cluster_labels):
                if cluster_id == -1:
                    continue
                cluster_mask = cluster_labels == cluster_id
                cluster_embeddings = embeddings[cluster_mask]
                centroid = cluster_embeddings.mean(axis=0)
                distances = np.linalg.norm(embeddings[cluster_mask] - centroid, axis=1)
                # Convert distances to scores (higher = better)
                max_dist = distances.max() if distances.max() > 0 else 1
                membership_scores[cluster_mask] = 1 - (distances / max_dist)
        
        return membership_scores
    
    def cluster_all_embeddings(self) -> Dict:
        """
        Perform clustering on all embeddings.
        
        Returns:
            Clustering summary dictionary
        """
        print("=" * 60)
        print("PHASE 13: EMBEDDING-BASED CLUSTERING")
        print("=" * 60)
        print(f"Embeddings directory: {self.embeddings_dir}")
        print(f"Output directory: {self.output_dir}")
        print(f"PCA components: {self.pca_components}")
        print(f"Min cluster size: {self.min_cluster_size}")
        print(f"Min samples: {self.min_samples}")
        print()
        
        # Load all embeddings
        metadata_list, embeddings_array = self._load_all_embeddings()
        
        # Normalize embeddings
        print("Normalizing embeddings...")
        normalized_embeddings = self._normalize_embeddings(embeddings_array)
        
        # Apply PCA
        print(f"Applying PCA to {self.pca_components} components...")
        reduced_embeddings = self._apply_pca(normalized_embeddings)
        
        # Cluster
        print("Clustering with HDBSCAN...")
        cluster_labels = self._cluster_embeddings(reduced_embeddings)
        
        # Calculate membership scores
        print("Calculating membership scores...")
        membership_scores = self._calculate_membership_scores(reduced_embeddings, cluster_labels)
        
        # Create cluster assignments
        print("Creating cluster assignments...")
        cluster_assignments = []
        
        for i, (metadata, label, score) in enumerate(zip(metadata_list, cluster_labels, membership_scores)):
            assignment = ClusterAssignment(
                tile_id=metadata['tile_id'],
                cluster_id=int(label),
                year=metadata['year'],
                date=metadata['date'],
                latitude=metadata['latitude'],
                longitude=metadata['longitude'],
                bbox=metadata['bbox'],
                sensor=metadata['sensor'],
                valid_percentage=metadata['valid_percentage'],
                embedding_source=metadata['model_name'],
                embedding_dimension=metadata['embedding_dimension'],
                is_outlier=bool(label == -1),
                membership_score=float(score),
                tile_path=f"data/tiles/{metadata['year']}/{metadata['tile_id']}"
            )
            cluster_assignments.append(assignment)
        
        # Save cluster assignments
        assignments_file = self.output_dir / "cluster_assignments.json"
        with open(assignments_file, 'w') as f:
            json.dump([asdict(a) for a in cluster_assignments], f, indent=2)
        
        # Calculate cluster statistics
        cluster_sizes = {}
        for assignment in cluster_assignments:
            cluster_id = assignment.cluster_id
            cluster_sizes[cluster_id] = cluster_sizes.get(cluster_id, 0) + 1
        
        n_clusters = len(cluster_sizes) - (1 if -1 in cluster_sizes else 0)
        n_noise = cluster_sizes.get(-1, 0)
        
        # Save cluster summary
        summary = {
            "total_tiles": len(cluster_assignments),
            "number_of_clusters": n_clusters,
            "number_of_noise_tiles": n_noise,
            "cluster_sizes": cluster_sizes,
            "clustering_parameters": {
                "min_cluster_size": self.min_cluster_size,
                "min_samples": self.min_samples,
                "metric": "euclidean",
                "cluster_selection_method": "eom"
            },
            "dimensionality_reduction": {
                "pca_components": self.pca_components,
                "explained_variance": float(self.pca.explained_variance_ratio_.sum())
            },
            "embedding_model": {
                "name": "Clay Foundation Model",
                "version": "v1.5",
                "dimension": 1024
            }
        }
        
        summary_file = self.output_dir / "cluster_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("=" * 60)
        print("CLUSTERING SUMMARY")
        print("=" * 60)
        print(f"Total tiles: {len(cluster_assignments)}")
        print(f"Number of clusters: {n_clusters}")
        print(f"Number of noise tiles: {n_noise}")
        print(f"Largest cluster: {max(cluster_sizes.values())}")
        print(f"Smallest cluster: {min([s for k, s in cluster_sizes.items() if k != -1])}")
        print(f"Assignments saved to: {assignments_file}")
        print(f"Summary saved to: {summary_file}")
        print("=" * 60)
        
        return summary
    
    def get_cluster_members(self, cluster_id: int) -> List[ClusterAssignment]:
        """
        Get all members of a specific cluster.
        
        Args:
            cluster_id: Cluster ID
            
        Returns:
            List of cluster assignments
        """
        assignments_file = self.output_dir / "cluster_assignments.json"
        
        if not assignments_file.exists():
            raise FileNotFoundError("Cluster assignments not found. Run clustering first.")
        
        with open(assignments_file, 'r') as f:
            assignments_data = json.load(f)
        
        members = []
        for data in assignments_data:
            if data['cluster_id'] == cluster_id:
                members.append(ClusterAssignment(**data))
        
        return members
    
    def get_tile_cluster(self, tile_id: str) -> Optional[int]:
        """
        Get cluster ID for a specific tile.
        
        Args:
            tile_id: Tile identifier
            
        Returns:
            Cluster ID or None if not found
        """
        assignments_file = self.output_dir / "cluster_assignments.json"
        
        if not assignments_file.exists():
            raise FileNotFoundError("Cluster assignments not found. Run clustering first.")
        
        with open(assignments_file, 'r') as f:
            assignments_data = json.load(f)
        
        for data in assignments_data:
            if data['tile_id'] == tile_id:
                return data['cluster_id']
        
        return None
