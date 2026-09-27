"""
Phase 13 - Embedding-Based Clustering CLI
Clusters satellite tiles using Clay embeddings with HDBSCAN
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from app.clustering.clustering import EmbeddingClusterer


def main():
    parser = argparse.ArgumentParser(description="Phase 13: Embedding-Based Clustering")
    parser.add_argument("--embeddings-dir", type=str, default="embeddings",
                       help="Directory containing Phase 6 embeddings (default: embeddings)")
    parser.add_argument("--output-dir", type=str, default="data/clusters",
                       help="Directory for clustering results (default: data/clusters)")
    parser.add_argument("--pca-components", type=int, default=50,
                       help="Number of PCA components (default: 50)")
    parser.add_argument("--min-cluster-size", type=int, default=3,
                       help="Minimum cluster size for HDBSCAN (default: 3)")
    parser.add_argument("--min-samples", type=int, default=3,
                       help="Minimum samples for HDBSCAN (default: 3)")
    
    args = parser.parse_args()
    
    # Initialize clusterer
    clusterer = EmbeddingClusterer(
        embeddings_dir=Path(args.embeddings_dir),
        output_dir=Path(args.output_dir),
        pca_components=args.pca_components,
        min_cluster_size=args.min_cluster_size,
        min_samples=args.min_samples
    )
    
    # Perform clustering
    summary = clusterer.cluster_all_embeddings()
    
    print("\nClustering completed successfully!")


if __name__ == "__main__":
    main()
