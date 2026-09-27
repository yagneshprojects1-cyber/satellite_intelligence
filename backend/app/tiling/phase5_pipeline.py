"""
Phase 5 — Geospatial Tiling Pipeline
====================================
Converts Phase 4 outputs into 256x256 tiles suitable for AI processing.
Memory efficient: uses rasterio windowed reading based on a master grid.
"""

import sys
import json
import math
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import numpy as np
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.warp import transform as transform_coords

# Path bootstrap
sys.path.append(str(Path(__file__).parent.parent))

from config.tiling_config import (
    TILES_DATA_DIR,
    DEFAULT_TILE_SIZE,
    MIN_VALID_PERCENTAGE,
    SKIP_INVALID_TILES,
    REFERENCE_YEAR
)
from config.ingestion_config import PROCESSED_DATA_DIR
from utils.metadata_extractor import load_metadata
from tiling.tile_grid import TileGrid


class Phase5TilingPipeline:
    def __init__(
        self,
        processed_dir: Path = PROCESSED_DATA_DIR,
        output_dir: Path = TILES_DATA_DIR,
        tile_size: int = DEFAULT_TILE_SIZE,
        min_valid_pct: float = MIN_VALID_PERCENTAGE,
        skip_invalid: bool = SKIP_INVALID_TILES,
        ref_year: int = REFERENCE_YEAR
    ):
        self.processed_dir = Path(processed_dir)
        self.output_dir = Path(output_dir)
        self.tile_size = tile_size
        self.min_valid_pct = min_valid_pct
        self.skip_invalid = skip_invalid
        self.ref_year = ref_year

        self.master_grid: Optional[TileGrid] = None
        self.stats = {
            "years_processed": 0,
            "total_tiles_generated": 0,
            "total_tiles_skipped": 0,
            "by_year": {}
        }

    def _get_year_directories(self) -> List[Tuple[int, Path]]:
        dirs = []
        if not self.processed_dir.exists():
            return dirs
            
        for d in sorted(self.processed_dir.iterdir()):
            if d.is_dir():
                try:
                    year = int(d.name)
                    dirs.append((year, d))
                except ValueError:
                    pass
        return dirs

    def _build_master_grid(self) -> bool:
        """
        Builds the master geospatial grid from the reference year's valid_mask.
        """
        ref_dir = self.processed_dir / str(self.ref_year)
        if not ref_dir.exists():
            print(f"[ERROR] Reference year directory {self.ref_year} not found.")
            return False

        mask_path = ref_dir / "quality" / "valid_mask.tif"
        if not mask_path.exists():
            print(f"[ERROR] Reference valid_mask.tif not found: {mask_path}")
            return False

        print(f"Building master grid from reference scene {self.ref_year}...")
        with rasterio.open(mask_path) as src:
            self.master_grid = TileGrid(
                crs=src.crs.to_string(),
                transform=src.transform,
                width=src.width,
                height=src.height,
                tile_size=self.tile_size
            )
        
        print(f"  Master grid created: {len(self.master_grid.tiles)} potential tiles.")
        return True

    def _pad_array(self, arr: np.ndarray, nodata: int = 0) -> np.ndarray:
        """
        Pad a 2D array to the expected tile size if it is smaller.
        """
        h, w = arr.shape
        if h == self.tile_size and w == self.tile_size:
            return arr
            
        padded = np.full((self.tile_size, self.tile_size), nodata, dtype=arr.dtype)
        padded[:h, :w] = arr
        return padded

    def _get_lat_lon(self, crs: str, x: float, y: float) -> Tuple[float, float]:
        """Convert a point from the source CRS to WGS84 (EPSG:4326)."""
        xs, ys = transform_coords(crs, 'EPSG:4326', [x], [y])
        return ys[0], xs[0]  # lat, lon

    def _process_year(self, year: int, year_dir: Path) -> None:
        print(f"\n{'-'*60}")
        print(f"Processing year: {year}")
        print(f"{'-'*60}")

        self.stats["by_year"][year] = {"generated": 0, "skipped": 0}

        # 1. Discover inputs
        mask_path = year_dir / "quality" / "valid_mask.tif"
        if not mask_path.exists():
            print(f"  [WARN] No valid_mask.tif found. Skipping {year}.")
            return

        # Load bands
        normalized_dir = year_dir / "normalized"
        if not normalized_dir.exists():
            print(f"  [WARN] No normalized bands found. Skipping {year}.")
            return
            
        bands = {p.stem.replace('_normalized', ''): p for p in normalized_dir.glob("*_normalized.tif")}
        if not bands:
            print(f"  [WARN] No band files found. Skipping {year}.")
            return

        print(f"  Found {len(bands)} bands to tile.")

        # Try load phase 4 metadata for date/scene info
        meta_path = year_dir / "metadata.json"
        base_meta = {}
        if meta_path.exists():
            base_meta = load_metadata(meta_path)
            
        acq_date = base_meta.get("acquisition_date", f"{year}-01-01")
        tile_suffix = base_meta.get("tile_id", "UNKNOWN")

        year_out_dir = self.output_dir / str(year)
        
        # 2. Iterate through master grid
        with rasterio.open(mask_path) as mask_src:
            mask_crs = mask_src.crs.to_string()
            
            # Open all bands once to avoid open/close overhead in loop
            band_srcs = {name: rasterio.open(path) for name, path in bands.items()}
            
            total_grid_tiles = len(self.master_grid.tiles)
            
            try:
                for i, grid_tile in enumerate(self.master_grid.tiles, 1):
                    bounds = grid_tile["bounds"]
                    
                    # Calculate read window based on bounding box
                    # This gracefully handles minor spatial misalignments
                    window = from_bounds(
                        bounds["left"], bounds["bottom"], 
                        bounds["right"], bounds["top"], 
                        mask_src.transform
                    )
                    
                    # Round window to avoid sub-pixel shifts
                    window = window.round_lengths().round_offsets()
                    
                    # Read valid mask
                    try:
                        mask_data = mask_src.read(1, window=window)
                    except ValueError:
                        # Window might be completely outside the raster
                        self.stats["by_year"][year]["skipped"] += 1
                        continue

                    # If empty
                    if mask_data.size == 0:
                        self.stats["by_year"][year]["skipped"] += 1
                        continue

                    # Calculate valid percentage
                    total_px = mask_data.size
                    valid_px = np.count_nonzero(mask_data == 1)
                    valid_pct = (valid_px / total_px) * 100.0

                    if valid_pct < self.min_valid_pct and self.skip_invalid:
                        self.stats["by_year"][year]["skipped"] += 1
                        continue

                    # At this point, we will generate the tile
                    tile_id = f"{year}_{tile_suffix}_{grid_tile['grid_id']}"
                    tile_dir = year_out_dir / tile_id
                    tile_dir.mkdir(parents=True, exist_ok=True)

                    # Calculate lat/lon of tile center
                    center_x = (bounds["left"] + bounds["right"]) / 2.0
                    center_y = (bounds["bottom"] + bounds["top"]) / 2.0
                    lat, lon = self._get_lat_lon(mask_crs, center_x, center_y)

                    # Prepare transform for the new padded 256x256 tile
                    tile_transform = rasterio.transform.from_bounds(
                        bounds["left"], bounds["bottom"],
                        bounds["right"], bounds["top"],
                        self.tile_size, self.tile_size
                    )

                    # 3. Read, pad and save bands
                    for band_name, src in band_srcs.items():
                        band_data = src.read(1, window=window)
                        # Pad with NoData (0 or whatever the source nodata is)
                        nodata_val = src.nodata if src.nodata is not None else 0
                        padded_data = self._pad_array(band_data, nodata_val)
                        
                        out_path = tile_dir / f"{band_name}.tif"
                        profile = src.profile.copy()
                        profile.update({
                            "height": self.tile_size,
                            "width": self.tile_size,
                            "transform": tile_transform,
                            "blockxsize": self.tile_size,
                            "blockysize": self.tile_size,
                            "tiled": False
                        })
                        
                        with rasterio.open(out_path, 'w', **profile) as dst:
                            dst.write(padded_data, 1)

                    # Save valid mask too
                    padded_mask = self._pad_array(mask_data, 0)
                    mask_out = tile_dir / "valid_mask.tif"
                    mask_profile = mask_src.profile.copy()
                    mask_profile.update({
                        "height": self.tile_size,
                        "width": self.tile_size,
                        "transform": tile_transform,
                        "tiled": False
                    })
                    with rasterio.open(mask_out, 'w', **mask_profile) as dst:
                        dst.write(padded_mask, 1)

                    # 4. Save Tile Metadata
                    tile_meta = {
                        "tile_id": tile_id,
                        "date": acq_date,
                        "latitude": round(lat, 6),
                        "longitude": round(lon, 6),
                        "bbox": {
                            "min_lon": round(self._get_lat_lon(mask_crs, bounds["left"], bounds["bottom"])[1], 6),
                            "min_lat": round(self._get_lat_lon(mask_crs, bounds["left"], bounds["bottom"])[0], 6),
                            "max_lon": round(self._get_lat_lon(mask_crs, bounds["right"], bounds["top"])[1], 6),
                            "max_lat": round(self._get_lat_lon(mask_crs, bounds["right"], bounds["top"])[0], 6)
                        },
                        "sensor": "Sentinel-2",
                        "source_scene": base_meta.get("scene_id", "UNKNOWN"),
                        "crs": mask_crs,
                        "resolution": mask_src.res[0],
                        "width": self.tile_size,
                        "height": self.tile_size,
                        "valid_percentage": round(valid_pct, 2)
                    }

                    with open(tile_dir / "metadata.json", "w") as f:
                        json.dump(tile_meta, f, indent=2)

                    self.stats["by_year"][year]["generated"] += 1
                    
                    if i % 1000 == 0:
                        print(f"    Progress: {i}/{total_grid_tiles} tiles checked...")
                        
            finally:
                # Ensure all band readers are closed
                for src in band_srcs.values():
                    src.close()
                    
            print(f"  Generated: {self.stats['by_year'][year]['generated']}")
            print(f"  Skipped:   {self.stats['by_year'][year]['skipped']}")
            
            self.stats["years_processed"] += 1
            self.stats["total_tiles_generated"] += self.stats["by_year"][year]["generated"]
            self.stats["total_tiles_skipped"] += self.stats["by_year"][year]["skipped"]

    def run(self) -> Dict:
        print("\n" + "="*60)
        print("PHASE 5 - GEOSPATIAL TILING")
        print("="*60)
        
        years = self._get_year_directories()
        if not years:
            print("[ERROR] No processed data found.")
            return {}

        if not self._build_master_grid():
            return {}

        for year, year_dir in years:
            self._process_year(year, year_dir)

        # Save run summary
        summary = {
            "phase": "Phase 5 - Tiling",
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "tile_size": self.tile_size,
                "min_valid_pct": self.min_valid_pct,
                "skip_invalid": self.skip_invalid,
                "reference_year": self.ref_year
            },
            "statistics": self.stats
        }
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(self.output_dir / "tiling_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        print("\n" + "="*60)
        print("PHASE 5 SUMMARY")
        print("="*60)
        print(f"  Total generated: {self.stats['total_tiles_generated']}")
        print(f"  Total skipped:   {self.stats['total_tiles_skipped']}")
        print(f"  Summary saved:   {self.output_dir / 'tiling_summary.json'}")
        
        return summary


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase 5 - Geospatial Tiling Pipeline")
    p.add_argument("--processed-dir", type=str, default=str(PROCESSED_DATA_DIR))
    p.add_argument("--output-dir", type=str, default=str(TILES_DATA_DIR))
    p.add_argument("--tile-size", type=int, default=DEFAULT_TILE_SIZE)
    p.add_argument("--min-valid", type=float, default=MIN_VALID_PERCENTAGE)
    p.add_argument("--keep-invalid", action="store_true")
    p.add_argument("--ref-year", type=int, default=REFERENCE_YEAR)
    return p


def main():
    args = _build_arg_parser().parse_args()
    pipeline = Phase5TilingPipeline(
        processed_dir=Path(args.processed_dir),
        output_dir=Path(args.output_dir),
        tile_size=args.tile_size,
        min_valid_pct=args.min_valid,
        skip_invalid=not args.keep_invalid,
        ref_year=args.ref_year
    )
    pipeline.run()


if __name__ == "__main__":
    main()
