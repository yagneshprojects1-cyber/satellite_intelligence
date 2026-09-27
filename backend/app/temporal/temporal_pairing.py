"""
Temporal Tile Pairing - Phase 10
Creates temporal pairs for the same geographic locations across years
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict


@dataclass
class TemporalPair:
    """Data class for temporal tile pair"""
    pair_id: str
    before_tile_id: str
    after_tile_id: str
    before_year: str
    after_year: str
    before_date: str
    after_date: str
    bbox: Dict[str, float]
    before_path: str
    after_path: str
    sensor: str
    spatial_overlap: float
    valid_percentage_before: float
    valid_percentage_after: float
    crs: str
    resolution: float
    width: int
    height: int


class TemporalPairer:
    """
    Creates temporal pairs for the same geographic locations across years.
    Uses bbox and geographic coordinates to verify spatial correspondence.
    """
    
    def __init__(self, tiles_dir: Path = Path("data/tiles")):
        """
        Initialize temporal pairer.
        
        Args:
            tiles_dir: Directory containing Phase 5 tiles organized by year
        """
        self.tiles_dir = Path(tiles_dir)
        self.output_dir = Path("data/temporal_pairs")
        self.summary_file = self.output_dir / "temporal_pairs_summary.json"
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "2022_2023").mkdir(exist_ok=True)
        (self.output_dir / "2023_2024").mkdir(exist_ok=True)
        (self.output_dir / "2022_2024").mkdir(exist_ok=True)
    
    def _load_tile_metadata(self, tile_path: Path) -> Optional[Dict]:
        """
        Load tile metadata from metadata.json file.
        
        Args:
            tile_path: Path to tile directory
            
        Returns:
            Metadata dictionary or None if failed
        """
        metadata_file = tile_path / "metadata.json"
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata from {metadata_file}: {e}")
            return None
    
    def _calculate_bbox_overlap(self, bbox1: Dict, bbox2: Dict) -> float:
        """
        Calculate intersection-over-union (IoU) of two bounding boxes.
        
        Args:
            bbox1: First bounding box {min_lon, min_lat, max_lon, max_lat}
            bbox2: Second bounding box {min_lon, min_lat, max_lon, max_lat}
            
        Returns:
            IoU value between 0 and 1
        """
        # Calculate intersection
        inter_min_lon = max(bbox1['min_lon'], bbox2['min_lon'])
        inter_min_lat = max(bbox1['min_lat'], bbox2['min_lat'])
        inter_max_lon = min(bbox1['max_lon'], bbox2['max_lon'])
        inter_max_lat = min(bbox1['max_lat'], bbox2['max_lat'])
        
        # Check if boxes overlap
        if inter_min_lon >= inter_max_lon or inter_min_lat >= inter_max_lat:
            return 0.0
        
        # Calculate intersection area
        inter_width = inter_max_lon - inter_min_lon
        inter_height = inter_max_lat - inter_min_lat
        inter_area = inter_width * inter_height
        
        # Calculate union area
        bbox1_width = bbox1['max_lon'] - bbox1['min_lon']
        bbox1_height = bbox1['max_lat'] - bbox1['min_lat']
        bbox1_area = bbox1_width * bbox1_height
        
        bbox2_width = bbox2['max_lon'] - bbox2['min_lon']
        bbox2_height = bbox2['max_lat'] - bbox2['min_lat']
        bbox2_area = bbox2_width * bbox2_height
        
        union_area = bbox1_area + bbox2_area - inter_area
        
        # Calculate IoU
        if union_area > 0:
            return inter_area / union_area
        return 0.0
    
    def _tiles_are_compatible(self, metadata1: Dict, metadata2: Dict) -> Tuple[bool, str]:
        """
        Check if two tiles are compatible for temporal pairing.
        
        Args:
            metadata1: First tile metadata
            metadata2: Second tile metadata
            
        Returns:
            Tuple of (is_compatible, reason)
        """
        # Check CRS compatibility
        if metadata1.get('crs') != metadata2.get('crs'):
            return False, f"CRS mismatch: {metadata1.get('crs')} vs {metadata2.get('crs')}"
        
        # Check resolution compatibility
        if metadata1.get('resolution') != metadata2.get('resolution'):
            return False, f"Resolution mismatch: {metadata1.get('resolution')} vs {metadata2.get('resolution')}"
        
        # Check spatial dimensions
        if metadata1.get('width') != metadata2.get('width') or metadata1.get('height') != metadata2.get('height'):
            return False, f"Dimension mismatch: {metadata1.get('width')}x{metadata1.get('height')} vs {metadata2.get('width')}x{metadata2.get('height')}"
        
        # Check sensor compatibility
        if metadata1.get('sensor') != metadata2.get('sensor'):
            return False, f"Sensor mismatch: {metadata1.get('sensor')} vs {metadata2.get('sensor')}"
        
        # Check valid percentage
        min_valid_percentage = 50.0  # Require at least 50% valid pixels
        if metadata1.get('valid_percentage', 0) < min_valid_percentage:
            return False, f"Before tile valid percentage too low: {metadata1.get('valid_percentage')}"
        if metadata2.get('valid_percentage', 0) < min_valid_percentage:
            return False, f"After tile valid percentage too low: {metadata2.get('valid_percentage')}"
        
        return True, "Compatible"
    
    def _create_pair_id(self, before_tile_id: str, after_tile_id: str) -> str:
        """
        Create deterministic pair ID from tile IDs.
        
        Args:
            before_tile_id: Before tile ID
            after_tile_id: After tile ID
            
        Returns:
            Pair ID as string
        """
        # Use UUID5 with namespace URL for deterministic ID
        pair_string = f"{before_tile_id}_{after_tile_id}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, pair_string))
    
    def _find_pairs_for_years(self, year1: str, year2: str, min_overlap: float = 0.7) -> Tuple[List[TemporalPair], Dict[str, int]]:
        """
        Find temporal pairs between two years.
        
        Args:
            year1: First year (before)
            year2: Second year (after)
            min_overlap: Minimum bbox overlap threshold (default: 0.7)
            
        Returns:
            Tuple of (pairs list, statistics dict)
        """
        year1_dir = self.tiles_dir / year1
        year2_dir = self.tiles_dir / year2
        
        if not year1_dir.exists() or not year2_dir.exists():
            print(f"Year directories not found: {year1_dir}, {year2_dir}")
            return [], {"total": 0, "paired": 0, "skipped": 0}
        
        # Load all metadata for year1
        year1_tiles = {}
        for tile_dir in year1_dir.iterdir():
            if tile_dir.is_dir():
                metadata = self._load_tile_metadata(tile_dir)
                if metadata:
                    year1_tiles[tile_dir.name] = metadata
        
        # Load all metadata for year2
        year2_tiles = {}
        for tile_dir in year2_dir.iterdir():
            if tile_dir.is_dir():
                metadata = self._load_tile_metadata(tile_dir)
                if metadata:
                    year2_tiles[tile_dir.name] = metadata
        
        print(f"Loaded {len(year1_tiles)} tiles from {year1}")
        print(f"Loaded {len(year2_tiles)} tiles from {year2}")
        
        # Find pairs
        pairs = []
        skipped = 0
        skip_reasons = {}
        
        for tile1_id, metadata1 in year1_tiles.items():
            for tile2_id, metadata2 in year2_tiles.items():
                # Calculate bbox overlap
                overlap = self._calculate_bbox_overlap(metadata1['bbox'], metadata2['bbox'])
                
                if overlap < min_overlap:
                    skipped += 1
                    skip_reasons['low_overlap'] = skip_reasons.get('low_overlap', 0) + 1
                    continue
                
                # Check compatibility
                compatible, reason = self._tiles_are_compatible(metadata1, metadata2)
                if not compatible:
                    skipped += 1
                    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                    continue
                
                # Create pair
                pair_id = self._create_pair_id(tile1_id, tile2_id)
                
                pair = TemporalPair(
                    pair_id=pair_id,
                    before_tile_id=tile1_id,
                    after_tile_id=tile2_id,
                    before_year=year1,
                    after_year=year2,
                    before_date=metadata1['date'],
                    after_date=metadata2['date'],
                    bbox=metadata1['bbox'],
                    before_path=str(year1_dir / tile1_id),
                    after_path=str(year2_dir / tile2_id),
                    sensor=metadata1['sensor'],
                    spatial_overlap=overlap,
                    valid_percentage_before=metadata1['valid_percentage'],
                    valid_percentage_after=metadata2['valid_percentage'],
                    crs=metadata1['crs'],
                    resolution=metadata1['resolution'],
                    width=metadata1['width'],
                    height=metadata1['height']
                )
                
                pairs.append(pair)
        
        stats = {
            "total": len(year1_tiles) * len(year2_tiles),
            "paired": len(pairs),
            "skipped": skipped,
            "skip_reasons": skip_reasons
        }
        
        return pairs, stats
    
    def _save_pair(self, pair: TemporalPair, output_subdir: Path):
        """
        Save a temporal pair to JSON file.
        
        Args:
            pair: TemporalPair object
            output_subdir: Output subdirectory path
        """
        output_file = output_subdir / f"{pair.pair_id}.json"
        
        # Check if pair already exists (incremental)
        if output_file.exists():
            return
        
        with open(output_file, 'w') as f:
            json.dump(asdict(pair), f, indent=2)
    
    def create_all_pairs(self, min_overlap: float = 0.7):
        """
        Create all temporal pairs for 2022→2023, 2023→2024, and 2022→2024.
        
        Args:
            min_overlap: Minimum bbox overlap threshold (default: 0.7)
        """
        print("=" * 60)
        print("PHASE 10: TEMPORAL TILE PAIRING")
        print("=" * 60)
        print(f"Tiles directory: {self.tiles_dir}")
        print(f"Output directory: {self.output_dir}")
        print(f"Minimum overlap threshold: {min_overlap}")
        print()
        
        all_pairs = []
        all_stats = {}
        
        # 2022 to 2023
        print("Creating pairs: 2022 to 2023")
        pairs_2022_2023, stats_2022_2023 = self._find_pairs_for_years("2022", "2023", min_overlap)
        output_dir_2022_2023 = self.output_dir / "2022_2023"
        
        for pair in pairs_2022_2023:
            self._save_pair(pair, output_dir_2022_2023)
        
        all_pairs.extend(pairs_2022_2023)
        all_stats["2022_2023"] = stats_2022_2023
        print(f"  Pairs created: {len(pairs_2022_2023)}")
        print(f"  Skipped: {stats_2022_2023['skipped']}")
        print()
        
        # 2023 to 2024
        print("Creating pairs: 2023 to 2024")
        pairs_2023_2024, stats_2023_2024 = self._find_pairs_for_years("2023", "2024", min_overlap)
        output_dir_2023_2024 = self.output_dir / "2023_2024"
        
        for pair in pairs_2023_2024:
            self._save_pair(pair, output_dir_2023_2024)
        
        all_pairs.extend(pairs_2023_2024)
        all_stats["2023_2024"] = stats_2023_2024
        print(f"  Pairs created: {len(pairs_2023_2024)}")
        print(f"  Skipped: {stats_2023_2024['skipped']}")
        print()
        
        # 2022 to 2024
        print("Creating pairs: 2022 to 2024")
        pairs_2022_2024, stats_2022_2024 = self._find_pairs_for_years("2022", "2024", min_overlap)
        output_dir_2022_2024 = self.output_dir / "2022_2024"
        
        for pair in pairs_2022_2024:
            self._save_pair(pair, output_dir_2022_2024)
        
        all_pairs.extend(pairs_2022_2024)
        all_stats["2022_2024"] = stats_2022_2024
        print(f"  Pairs created: {len(pairs_2022_2024)}")
        print(f"  Skipped: {stats_2022_2024['skipped']}")
        print()
        
        # Save summary
        summary = {
            "total_pairs": len(all_pairs),
            "pairs_by_year_combination": {
                "2022_2023": len(pairs_2022_2023),
                "2023_2024": len(pairs_2023_2024),
                "2022_2024": len(pairs_2022_2024)
            },
            "statistics": all_stats,
            "min_overlap_threshold": min_overlap
        }
        
        with open(self.summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("=" * 60)
        print("TEMPORAL PAIRING SUMMARY")
        print("=" * 60)
        print(f"Total pairs created: {len(all_pairs)}")
        print(f"  2022 to 2023: {len(pairs_2022_2023)}")
        print(f"  2023 to 2024: {len(pairs_2023_2024)}")
        print(f"  2022 to 2024: {len(pairs_2022_2024)}")
        print(f"Summary saved to: {self.summary_file}")
        print("=" * 60)
        
        return summary
