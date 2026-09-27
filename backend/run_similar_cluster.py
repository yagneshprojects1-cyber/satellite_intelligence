"""
Phase 13 - Cluster Discovery CLI
Find similar locations within the same cluster using Clay embeddings
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from app.clustering.cluster_discovery import ClusterDiscovery


def main():
    parser = argparse.ArgumentParser(description="Phase 13: Cluster Discovery - Find Similar Locations")
    parser.add_argument("--tile-id", type=str, required=True,
                       help="Query tile identifier")
    parser.add_argument("--embeddings-dir", type=str, default="embeddings",
                       help="Directory containing Phase 6 embeddings (default: embeddings)")
    parser.add_argument("--clusters-dir", type=str, default="data/clusters",
                       help="Directory containing clustering results (default: data/clusters)")
    parser.add_argument("--top-k", type=int, default=10,
                       help="Number of similar locations to return (default: 10)")
    parser.add_argument("--include-query", action="store_true",
                       help="Include query tile in results")
    parser.add_argument("--target-year", type=str, default=None,
                       help="Target year for cross-year discovery (e.g., 2023)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("PHASE 13: CLUSTER DISCOVERY")
    print("=" * 60)
    print(f"Query tile: {args.tile_id}")
    print(f"Top-K: {args.top_k}")
    print(f"Target year: {args.target_year if args.target_year else 'All years'}")
    print()
    
    # Initialize cluster discovery
    discovery = ClusterDiscovery(
        embeddings_dir=Path(args.embeddings_dir),
        clusters_dir=Path(args.clusters_dir)
    )
    
    # Find similar locations
    if args.target_year:
        results = discovery.find_similar_locations_cross_year(
            tile_id=args.tile_id,
            target_year=args.target_year,
            top_k=args.top_k
        )
    else:
        results = discovery.find_similar_locations(
            tile_id=args.tile_id,
            top_k=args.top_k,
            include_query_tile=args.include_query
        )
    
    # Print results
    print("=" * 60)
    print("SIMILAR LOCATIONS")
    print("=" * 60)
    
    if not results:
        print("No similar locations found.")
    else:
        for result in results:
            print(f"\nRank {result.rank}:")
            print(f"  Tile ID: {result.tile_id}")
            print(f"  Similarity: {result.similarity:.4f}")
            print(f"  Cluster ID: {result.cluster_id}")
            print(f"  Date: {result.date}")
            print(f"  Location: {result.latitude:.6f}, {result.longitude:.6f}")
            print(f"  Sensor: {result.sensor}")
            print(f"  Source Scene: {result.source_scene}")
            print(f"  Tile Path: {result.tile_path}")
    
    print("\n" + "=" * 60)
    print(f"Total results: {len(results)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
