"""
Phase 8 - CLIP Image Indexing CLI
Indexes Phase 5 tiles using CLIP image embeddings for text-to-image retrieval
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from app.semantic.clip_indexer import CLIPIndexer


def main():
    parser = argparse.ArgumentParser(description="Phase 8: CLIP Image Indexing for Semantic Search")
    parser.add_argument("--tiles-dir", type=str, default="data/tiles",
                       help="Directory containing Phase 5 tiles (default: data/tiles)")
    parser.add_argument("--qdrant-storage", type=str, default="qdrant_storage",
                       help="Qdrant storage path (default: qdrant_storage)")
    parser.add_argument("--clip-collection", type=str, default="satellite_tiles_clip",
                       help="CLIP Qdrant collection name (default: satellite_tiles_clip)")
    parser.add_argument("--model", type=str, default="openai/clip-vit-base-patch32",
                       help="CLIP model name (default: openai/clip-vit-base-patch32)")
    parser.add_argument("--device", type=str, default="cpu",
                       help="torch device (default: cpu)")
    parser.add_argument("--batch-size", type=int, default=16,
                       help="Batch size for processing (default: 16)")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of tiles to process for testing (default: all)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("PHASE 8: CLIP IMAGE INDEXING")
    print("=" * 60)
    print(f"Tiles directory: {args.tiles_dir}")
    print(f"Qdrant storage: {args.qdrant_storage}")
    print(f"CLIP collection: {args.clip_collection}")
    print(f"CLIP model: {args.model}")
    print(f"Device: {args.device}")
    print(f"Batch size: {args.batch_size}")
    print(f"Limit: {args.limit if args.limit else 'all'}")
    print()
    
    # Initialize CLIP indexer
    indexer = CLIPIndexer(
        tiles_dir=args.tiles_dir,
        qdrant_storage_path=args.qdrant_storage,
        clip_collection_name=args.clip_collection,
        model_name=args.model,
        device=args.device,
        batch_size=args.batch_size
    )
    
    # Run indexing
    stats = indexer.index_tiles(limit=args.limit)
    
    # Print results
    print("\n" + "=" * 60)
    print("PHASE 8 INDEXING RESULTS")
    print("=" * 60)
    print(f"Tiles discovered: {stats['discovered']}")
    print(f"Tiles processed: {stats['processed']}")
    print(f"Tiles skipped (existing): {stats['skipped_existing']}")
    print(f"Tiles failed: {stats['failed']}")
    print(f"Processing time: {stats['processing_time']:.2f}s")
    print()
    
    if stats['processed'] > 0:
        print("CLIP image indexing completed successfully!")
    else:
        print("No tiles were processed.")


if __name__ == "__main__":
    main()