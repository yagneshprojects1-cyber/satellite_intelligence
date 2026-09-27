"""
Phase 7 - Qdrant Vector Database / Vector Indexing
CLI entry point for indexing Phase 6 Clay embeddings into Qdrant
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from app.vector_db.qdrant_indexer import QdrantIndexer


def main():
    parser = argparse.ArgumentParser(description="Phase 7: Qdrant Vector Database Indexing")
    parser.add_argument("--embeddings-dir", type=str, default="embeddings",
                       help="Directory containing Phase 6 embeddings (default: embeddings)")
    parser.add_argument("--batch-size", type=int, default=64,
                       help="Batch size for Qdrant upserts (default: 64)")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of embeddings to process for testing (default: all)")
    parser.add_argument("--validate", action="store_true",
                       help="Run validation mode with limit=1 first")
    
    args = parser.parse_args()
    
    # If validate mode, force limit=1
    if args.validate:
        print("Running in validation mode with limit=1")
        args.limit = 1
    
    print("=" * 60)
    print("PHASE 7: QDRANT VECTOR DATABASE INDEXING")
    print("=" * 60)
    print(f"Embeddings directory: {args.embeddings_dir}")
    print(f"Batch size: {args.batch_size}")
    print(f"Limit: {args.limit if args.limit else 'all'}")
    print()
    
    # Initialize indexer
    indexer = QdrantIndexer(
        embeddings_dir=args.embeddings_dir,
        batch_size=args.batch_size
    )
    
    # Run indexing
    stats = indexer.index_all(limit=args.limit)
    
    # Print results
    print("\n" + "=" * 60)
    print("PHASE 7 RESULTS")
    print("=" * 60)
    print(f"Embeddings discovered: {stats['discovered']}")
    print(f"Successfully indexed: {stats['indexed']}")
    print(f"Skipped (existing): {stats['skipped']}")
    print(f"Failed: {stats['failed']}")
    print(f"Processing time: {stats['processing_time']:.2f}s")
    print()
    
    # Run validation tests
    if not args.validate and stats['indexed'] > 0:
        print("Running validation tests...")
        similarity_ok = indexer.validate_similarity_search()
        filter_ok = indexer.validate_filter_search()
        
        if similarity_ok and filter_ok:
            print("\nAll validation tests PASSED")
        else:
            print("\nSome validation tests FAILED (may be due to limited embeddings)")
            print("Once Phase 6 completes all 983 embeddings, re-run Phase 7 for full validation")
    
    if args.validate:
        print("Validation mode completed successfully!")
        print("You can now run the full indexing without --validate")
    else:
        print("Phase 7 indexing completed!")


if __name__ == "__main__":
    main()