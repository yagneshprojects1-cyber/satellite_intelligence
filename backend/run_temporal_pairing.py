"""
Phase 10 - Temporal Tile Pairing CLI
Creates temporal pairs for the same geographic locations across years
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from app.temporal.temporal_pairing import TemporalPairer


def main():
    parser = argparse.ArgumentParser(description="Phase 10: Temporal Tile Pairing")
    parser.add_argument("--tiles-dir", type=str, default="data/tiles",
                       help="Directory containing Phase 5 tiles (default: data/tiles)")
    parser.add_argument("--min-overlap", type=float, default=0.7,
                       help="Minimum bbox overlap threshold (default: 0.7)")
    
    args = parser.parse_args()
    
    # Initialize temporal pairer
    pairer = TemporalPairer(tiles_dir=Path(args.tiles_dir))
    
    # Create all temporal pairs
    summary = pairer.create_all_pairs(min_overlap=args.min_overlap)
    
    print("\nTemporal pairing completed successfully!")


if __name__ == "__main__":
    main()
