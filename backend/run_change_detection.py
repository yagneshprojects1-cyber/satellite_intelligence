"""
Phase 11 - Multi-Temporal Change Detection CLI
Detects meaningful changes between before and after satellite images
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from app.temporal.change_detection import ChangeDetector


def main():
    parser = argparse.ArgumentParser(description="Phase 11: Multi-Temporal Change Detection")
    parser.add_argument("--pairs-dir", type=str, default="data/temporal_pairs",
                       help="Directory containing temporal pairs (default: data/temporal_pairs)")
    parser.add_argument("--output-dir", type=str, default="data/change_results",
                       help="Directory for change detection results (default: data/change_results)")
    parser.add_argument("--changeformer-path", type=str, default=None,
                       help="Path to ChangeFormer model checkpoint (optional)")
    parser.add_argument("--changeformer-repo", type=str, default=None,
                       help="Path to ChangeFormer repository (optional)")
    parser.add_argument("--method", type=str, default="baseline",
                       choices=["baseline", "changeformer"],
                       help="Detection method (default: baseline)")
    parser.add_argument("--pair", type=str, default=None,
                       help="Specific year combination to process (e.g., 2022_2023)")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of pairs to process per year combination")
    parser.add_argument("--all", action="store_true",
                       help="Process all year combinations")
    
    args = parser.parse_args()
    
    # Initialize change detector
    detector = ChangeDetector(
        pairs_dir=Path(args.pairs_dir),
        output_dir=Path(args.output_dir),
        changeformer_path=Path(args.changeformer_path) if args.changeformer_path else None,
        changeformer_repo=Path(args.changeformer_repo) if args.changeformer_repo else None
    )
    
    # Process pairs
    if args.all:
        summary = detector.process_all_pairs(method=args.method, limit=args.limit)
    elif args.pair:
        results, stats = detector.process_pair_directory(
            args.pair, limit=args.limit, method=args.method
        )
        print(f"\nProcessed {stats['processed']} pairs from {args.pair}")
        print(f"Failed: {stats['failed']}")
    else:
        print("Please specify either --all or --pair <year_combination>")
        return
    
    print("\nChange detection completed successfully!")


if __name__ == "__main__":
    main()
