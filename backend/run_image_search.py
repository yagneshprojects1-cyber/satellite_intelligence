"""
Phase 9 - Image-to-Image Semantic Search CLI
CLIP-based image-to-image similarity search for satellite imagery
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from app.semantic.semantic_search import SemanticSearch


def main():
    parser = argparse.ArgumentParser(description="Phase 9: CLIP-based Image-to-Image Semantic Search")
    parser.add_argument("tile_id", type=str, help="Tile ID for image-to-image search")
    parser.add_argument("--qdrant-storage", type=str, default="qdrant_storage",
                       help="Qdrant storage path (default: qdrant_storage)")
    parser.add_argument("--clip-collection", type=str, default="satellite_tiles_clip",
                       help="CLIP Qdrant collection name (default: satellite_tiles_clip)")
    parser.add_argument("--tiles-dir", type=str, default="data/tiles",
                       help="Directory containing Phase 5 tiles (default: data/tiles)")
    parser.add_argument("--model", type=str, default="openai/clip-vit-base-patch32",
                       help="CLIP model name (default: openai/clip-vit-base-patch32)")
    parser.add_argument("--device", type=str, default="cpu",
                       help="torch device (default: cpu)")
    parser.add_argument("--top-k", type=int, default=10,
                       help="Number of results to return (default: 10)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("PHASE 9: IMAGE-TO-IMAGE SEARCH")
    print("=" * 60)
    print(f"Query tile: {args.tile_id}")
    print(f"Top-K: {args.top_k}")
    print(f"CLIP collection: {args.clip_collection}")
    print(f"CLIP model: {args.model}")
    print(f"Device: {args.device}")
    print()
    
    # Initialize semantic search
    search_engine = SemanticSearch(
        qdrant_storage_path=args.qdrant_storage,
        clip_collection_name=args.clip_collection,
        tiles_dir=args.tiles_dir,
        model_name=args.model,
        device=args.device
    )
    
    # Perform image-to-image search
    results = search_engine.search_by_image(
        tile_id=args.tile_id,
        top_k=args.top_k
    )
    
    # Print results
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    if not results:
        print("No results found.")
    else:
        for result in results:
            print(f"\nRank {result['rank']}:")
            print(f"  Tile ID: {result['tile_id']}")
            print(f"  Similarity: {result['similarity']:.4f}")
            print(f"  Date: {result['date']}")
            print(f"  Location: {result['latitude']:.6f}, {result['longitude']:.6f}")
            print(f"  Sensor: {result['sensor']}")
            print(f"  Valid Percentage: {result['valid_percentage']:.2f}%")
            print(f"  Tile Path: {result['tile_path']}")
    
    print("\n" + "=" * 60)
    print(f"Total results: {len(results)}")
    print("=" * 60)


if __name__ == "__main__":
    main()