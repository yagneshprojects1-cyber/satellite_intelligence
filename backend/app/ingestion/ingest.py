"""
Main Sentinel-2 Ingestion Pipeline
Orchestrates the conversion of SAFE files to processed GeoTIFF format
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.safe_parser import SAFEParser, discover_safe_files, group_safe_by_year, SAFEParseError
from utils import get_image_processor, get_metadata_extractor, get_quality_processor
from config.ingestion_config import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, BAND_RESOLUTIONS,
    RGB_BANDS, QUALITY_BANDS, SCL_CLASSES, VALID_SCL_CLASSES,
    INVALID_SCL_CLASSES, SCL_CLASS_GROUPS,
    PROCESSED_STRUCTURE, OVERWRITE_EXISTING, CREATE_VALID_MASK, CREATE_RGB_PREVIEW,
    APPLY_QUALITY_MASK_TO_BANDS, CLOUD_SHADOW_BUFFER_SIZE,
    REFLECTANCE_NORMALIZATION, SPATIAL_ALIGNMENT_CHECK
)

# Import heavy dependencies
ImageProcessor, match_resolution, get_rgb_bands = get_image_processor()
MetadataExtractor, _ = get_metadata_extractor()
QualityProcessor = get_quality_processor()


class Sentinel2IngestionPipeline:
    """Main pipeline for Sentinel-2 data ingestion"""
    
    def __init__(self, 
                 raw_dir: Path = RAW_DATA_DIR,
                 processed_dir: Path = PROCESSED_DATA_DIR,
                 overwrite: bool = OVERWRITE_EXISTING):
        """
        Initialize ingestion pipeline
        
        Args:
            raw_dir: Directory containing raw SAFE files
            processed_dir: Directory for processed output
            overwrite: Whether to overwrite existing processed files
        """
        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)
        self.overwrite = overwrite
        
        self.image_processor = ImageProcessor(quality_check=True)
        self.quality_processor = QualityProcessor(self.image_processor)
        
        # Statistics
        self.stats = {
            "total_safe_files": 0,
            "successfully_processed": 0,
            "failed_processing": 0,
            "total_bands_processed": 0,
            "total_quality_masks": 0,
            "total_rgb_previews": 0,
            "quality_stats_calculated": 0,
            "bands_normalized": 0,
            "bands_masked": 0
        }
    
    def discover_and_group(self) -> Dict[int, List[Path]]:
        """
        Step 1: Discover SAFE files and group by year
        
        Returns:
            Dictionary mapping year to list of SAFE file paths
        """
        print("=" * 60)
        print("STEP 1: Discovering SAFE files")
        print("=" * 60)
        
        try:
            safe_files = discover_safe_files(self.raw_dir)
            self.stats["total_safe_files"] = len(safe_files)
            
            print(f"Found {len(safe_files)} SAFE files in {self.raw_dir}")
            
            grouped = group_safe_by_year(safe_files)
            
            for year, files in sorted(grouped.items()):
                print(f"  Year {year}: {len(files)} files")
            
            return grouped
            
        except SAFEParseError as e:
            print(f"Error discovering SAFE files: {e}")
            return {}
    
    def verify_spatial_alignment_across_scenes(self, metadata_list: List[Dict]) -> Dict:
        """
        Verify spatial alignment across multiple temporal scenes
        
        Args:
            metadata_list: List of metadata dictionaries from processed scenes
            
        Returns:
            Dictionary with alignment verification results
        """
        if not SPATIAL_ALIGNMENT_CHECK:
            print("Spatial alignment check disabled")
            return {"status": "disabled"}
        
        print("\n" + "=" * 60)
        print("SPATIAL ALIGNMENT VERIFICATION")
        print("=" * 60)
        
        # Get reference bands for alignment check (use B02 10m as reference)
        reference_bands = []
        for metadata in metadata_list:
            if "B02" in metadata["bands"] and metadata["bands"]["B02"]["status"] == "success":
                reference_bands.append(Path(metadata["bands"]["B02"]["processed_file"]))
        
        if len(reference_bands) < 2:
            print("Need at least 2 scenes for alignment verification")
            return {"status": "insufficient_data"}
        
        try:
            alignment_results = self.quality_processor.verify_spatial_alignment(reference_bands)
            
            print(f"Overall alignment: {alignment_results['overall_alignment']}")
            for scene_name, comparison in alignment_results["comparisons"].items():
                print(f"  {scene_name}: {comparison['status']}")
                if comparison["status"] == "misaligned":
                    print(f"    CRS match: {comparison['crs_match']}")
                    print(f"    Resolution match: {comparison['resolution_match']}")
                    print(f"    Dimensions match: {comparison['dimensions_match']}")
                    print(f"    Bounds match: {comparison['bounds_match']}")
            
            return alignment_results
            
        except Exception as e:
            print(f"Error during spatial alignment verification: {e}")
            return {"status": "error", "message": str(e)}
    
    def process_single_safe(self, safe_path: Path) -> Optional[Dict]:
        """
        Process a single SAFE file through the complete pipeline
        
        Args:
            safe_path: Path to SAFE directory
            
        Returns:
            Metadata dictionary if successful, None otherwise
        """
        print(f"\nProcessing: {safe_path.name}")
        print("-" * 50)
        
        try:
            # Initialize parser
            parser = SAFEParser(safe_path)
            filename_info = parser.parse_filename()
            year = filename_info["year"]
            
            print(f"Satellite: {filename_info['satellite']}")
            print(f"Date: {filename_info['acquisition_date']}")
            print(f"Tile: {filename_info['tile_id']}")
            
            # Setup output directories
            year_dir = self.processed_dir / str(year)
            bands_dir = year_dir / PROCESSED_STRUCTURE["bands"]
            quality_dir = year_dir / PROCESSED_STRUCTURE["quality"]
            previews_dir = year_dir / PROCESSED_STRUCTURE["previews"]
            
            # Get SAFE structure information
            safe_info = parser.get_safe_info()
            
            # Process bands by resolution
            print("\nStep 2-5: Processing bands...")
            band_info = {}
            geo_info = {}

            for resolution, band_names in BAND_RESOLUTIONS.items():
                # resolution is already in format "10m", "20m", "60m"
                if resolution in safe_info["bands"]:
                    available_bands = safe_info["bands"][resolution]

                    # Filter to requested bands for this resolution
                    resolution_bands = {
                        band: path for band, path in available_bands.items()
                        if band in band_names
                    }

                    if resolution_bands:
                        print(f"  Processing {resolution} bands: {list(resolution_bands.keys())}")

                        # Process bands
                        results = self.image_processor.process_band_collection(
                            resolution_bands, bands_dir, self.overwrite
                        )

                        # Store results and geo info
                        for band_name, geo_data in results.items():
                            if geo_data:
                                band_info.setdefault(resolution, {})[band_name] = {
                                    "source": resolution_bands[band_name],
                                    "output": str(bands_dir / f"{band_name}.tif"),
                                    "status": "success"
                                }
                                geo_info[f"{band_name}_{resolution}"] = geo_data
                                self.stats["total_bands_processed"] += 1
                            else:
                                band_info.setdefault(resolution, {})[band_name] = {
                                    "source": resolution_bands[band_name],
                                    "output": None,
                                    "status": "failed"
                                }
            
            # Process quality masks
            print("\nStep 8: Processing quality masks...")
            quality_info = {}
            quality_stats = None

            # Process SCL (Scene Classification Layer) - prefer 20m version
            scl_key = None
            for key in safe_info["quality_masks"]:
                if key.startswith("SCL_"):
                    scl_key = key
                    # Prefer R20m over R60m
                    if "R20m" in key:
                        break

            if scl_key:
                scl_path = Path(safe_info["quality_masks"][scl_key])
                scl_output = quality_dir / "SCL.tif"

                try:
                    geo_data = self.image_processor.jp2_to_geotiff(scl_path, scl_output, self.overwrite)
                    quality_info["SCL"] = {
                        "source": str(scl_path),
                        "output": str(scl_output),
                        "status": "success"
                    }
                    geo_info["SCL_quality"] = geo_data
                    self.stats["total_quality_masks"] += 1

                    # Create valid mask if requested
                    if CREATE_VALID_MASK:
                        valid_mask_output = quality_dir / "valid_mask.tif"
                        valid_geo = self.image_processor.create_valid_mask(
                            scl_output, valid_mask_output, VALID_SCL_CLASSES, self.overwrite
                        )
                        quality_info["valid_mask"] = {
                            "source": str(scl_output),
                            "output": str(valid_mask_output),
                            "status": "success"
                        }
                        geo_info["valid_mask_quality"] = valid_geo
                        self.stats["total_quality_masks"] += 1

                    print(f"  Processed SCL quality mask ({scl_key})")

                    # Calculate quality statistics (Phase 4)
                    try:
                        quality_stats = self.quality_processor.calculate_quality_statistics(
                            scl_output, SCL_CLASSES, SCL_CLASS_GROUPS
                        )
                        print(f"  Quality statistics: {quality_stats['valid_percentage']:.1f}% valid pixels")
                        self.stats["quality_stats_calculated"] += 1
                    except Exception as e:
                        print(f"  Warning: Could not calculate quality statistics: {e}")

                    # Apply cloud shadow buffer if configured (Phase 4)
                    if CLOUD_SHADOW_BUFFER_SIZE > 0:
                        try:
                            buffered_scl_output = quality_dir / "SCL_buffered.tif"
                            buffer_geo = self.quality_processor.apply_cloud_shadow_buffer(
                                scl_output, buffered_scl_output, CLOUD_SHADOW_BUFFER_SIZE, self.overwrite
                            )
                            quality_info["SCL_buffered"] = {
                                "source": str(scl_output),
                                "output": str(buffered_scl_output),
                                "status": "success"
                            }
                            # Recreate valid mask with buffered SCL
                            if CREATE_VALID_MASK:
                                buffered_valid_output = quality_dir / "valid_mask_buffered.tif"
                                buffered_valid_geo = self.image_processor.create_valid_mask(
                                    buffered_scl_output, buffered_valid_output, VALID_SCL_CLASSES, self.overwrite
                                )
                                quality_info["valid_mask_buffered"] = {
                                    "source": str(buffered_scl_output),
                                    "output": str(buffered_valid_output),
                                    "status": "success"
                                }
                        except Exception as e:
                            print(f"  Warning: Could not apply cloud shadow buffer: {e}")

                except Exception as e:
                    print(f"  Error processing SCL: {e}")
                    quality_info["SCL"] = {
                        "source": str(scl_path),
                        "output": None,
                        "status": f"failed: {e}"
                    }
            else:
                print(f"  No SCL mask found in quality data")
            
            # Create RGB preview
            print("\nStep 9: Creating RGB preview...")
            if CREATE_RGB_PREVIEW:
                # Get R10m bands for RGB
                rgb_bands = {}
                if "R10m" in band_info:
                    for channel, band_name in RGB_BANDS.items():
                        if band_name in band_info["R10m"] and band_info["R10m"][band_name]["status"] == "success":
                            rgb_bands[channel] = Path(band_info["R10m"][band_name]["output"])

                if len(rgb_bands) == 3:
                    rgb_output = previews_dir / "rgb.tif"
                    try:
                        rgb_geo = self.image_processor.create_rgb_composite(
                            rgb_bands["red"], rgb_bands["green"], rgb_bands["blue"],
                            rgb_output, self.overwrite
                        )
                        geo_info["rgb_preview"] = rgb_geo
                        self.stats["total_rgb_previews"] += 1
                        print(f"  Created RGB preview")
                    except Exception as e:
                        print(f"  Error creating RGB preview: {e}")
                else:
                    print(f"  Could not create RGB preview - missing bands (found: {list(rgb_bands.keys())})")

            # Phase 4: Advanced quality processing
            print("\nPhase 4: Advanced quality processing...")

            # Apply reflectance normalization if configured
            if REFLECTANCE_NORMALIZATION:
                print("  Applying reflectance normalization...")
                normalized_dir = year_dir / "normalized"
                normalized_info = {}

                for resolution, bands in band_info.items():
                    for band_name, band_data in bands.items():
                        if band_data["status"] == "success":
                            input_path = Path(band_data["output"])
                            output_path = normalized_dir / f"{band_name}_normalized.tif"

                            try:
                                norm_geo = self.quality_processor.normalize_reflectance(
                                    input_path, output_path, overwrite=self.overwrite
                                )
                                normalized_info[band_name] = {
                                    "source": str(input_path),
                                    "output": str(output_path),
                                    "status": "success"
                                }
                                self.stats["bands_normalized"] += 1
                            except Exception as e:
                                print(f"    Error normalizing {band_name}: {e}")
                                normalized_info[band_name] = {
                                    "source": str(input_path),
                                    "output": None,
                                    "status": f"failed: {e}"
                                }

                if normalized_info:
                    band_info["normalized"] = normalized_info

            # Apply quality mask to bands if configured
            if APPLY_QUALITY_MASK_TO_BANDS and "valid_mask" in quality_info:
                print("  Applying quality mask to bands...")
                masked_dir = year_dir / "masked"
                masked_info = {}

                valid_mask_path = Path(quality_info["valid_mask"]["output"])

                for resolution, bands in band_info.items():
                    if resolution == "normalized":  # Skip normalized bands if separate
                        continue

                    for band_name, band_data in bands.items():
                        if band_data["status"] == "success":
                            input_path = Path(band_data["output"])
                            output_path = masked_dir / f"{band_name}_masked.tif"

                            try:
                                mask_geo = self.quality_processor.apply_quality_mask_to_band(
                                    input_path, valid_mask_path, output_path, overwrite=self.overwrite
                                )
                                masked_info[band_name] = {
                                    "source": str(input_path),
                                    "output": str(output_path),
                                    "status": "success"
                                }
                                self.stats["bands_masked"] += 1
                            except Exception as e:
                                print(f"    Error masking {band_name}: {e}")
                                masked_info[band_name] = {
                                    "source": str(input_path),
                                    "output": None,
                                    "status": f"failed: {e}"
                                }

                if masked_info:
                    band_info["masked"] = masked_info

            # Extract and save metadata
            print("\nStep 7: Extracting and saving metadata...")
            metadata_extractor = MetadataExtractor(parser)
            metadata = metadata_extractor.extract_metadata(band_info, quality_info, geo_info, quality_stats)
            
            metadata_path = year_dir / "metadata.json"
            metadata_extractor.save_metadata(metadata, metadata_path)
            
            self.stats["successfully_processed"] += 1
            print(f"\n[OK] Successfully processed {safe_path.name}")
            
            return metadata
            
        except Exception as e:
            print(f"\n[FAIL] Failed to process {safe_path.name}: {e}")
            self.stats["failed_processing"] += 1
            return None
    
    def run_pipeline(self, specific_years: Optional[List[int]] = None):
        """
        Run the complete ingestion pipeline
        
        Args:
            specific_years: Optional list of years to process (default: all)
        """
        print("\n" + "=" * 60)
        print("SENTINEL-2 INGESTION PIPELINE")
        print("=" * 60)
        print(f"Raw data directory: {self.raw_dir}")
        print(f"Processed data directory: {self.processed_dir}")
        print(f"Overwrite existing: {self.overwrite}")
        print()
        
        # Discover SAFE files
        grouped_files = self.discover_and_group()
        
        if not grouped_files:
            print("No SAFE files found to process")
            return
        
        # Filter by specific years if requested
        if specific_years:
            grouped_files = {year: files for year, files in grouped_files.items() 
                           if year in specific_years}
            print(f"\nProcessing only years: {specific_years}")
        
        # Process each SAFE file
        print("\n" + "=" * 60)
        print("STEP 2-10: Processing SAFE files")
        print("=" * 60)
        
        all_metadata = []
        
        for year, safe_files in sorted(grouped_files.items()):
            print(f"\n--- Processing Year {year} ({len(safe_files)} files) ---")

            for safe_path in safe_files:
                metadata = self.process_single_safe(safe_path)
                if metadata:
                    all_metadata.append(metadata)

        # Phase 4: Spatial alignment verification across scenes
        if all_metadata and len(all_metadata) > 1:
            alignment_results = self.verify_spatial_alignment_across_scenes(all_metadata)
            if alignment_results:
                self.stats["spatial_alignment"] = alignment_results

        # Print summary
        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)
        print(f"Total SAFE files found: {self.stats['total_safe_files']}")
        print(f"Successfully processed: {self.stats['successfully_processed']}")
        print(f"Failed processing: {self.stats['failed_processing']}")
        print(f"Total bands processed: {self.stats['total_bands_processed']}")
        print(f"Total quality masks: {self.stats['total_quality_masks']}")
        print(f"Total RGB previews: {self.stats['total_rgb_previews']}")
        print(f"Quality stats calculated: {self.stats.get('quality_stats_calculated', 0)}")
        print(f"Bands normalized: {self.stats.get('bands_normalized', 0)}")
        print(f"Bands masked: {self.stats.get('bands_masked', 0)}")
        if "spatial_alignment" in self.stats:
            print(f"Spatial alignment: {self.stats['spatial_alignment']['overall_alignment']}")
        print()

        # Save overall summary
        summary = {
            "pipeline_run": datetime.now().isoformat(),
            "configuration": {
                "raw_dir": str(self.raw_dir),
                "processed_dir": str(self.processed_dir),
                "overwrite": self.overwrite,
                "phase4_settings": {
                    "apply_quality_mask_to_bands": APPLY_QUALITY_MASK_TO_BANDS,
                    "cloud_shadow_buffer": CLOUD_SHADOW_BUFFER_SIZE,
                    "reflectance_normalization": REFLECTANCE_NORMALIZATION,
                    "spatial_alignment_check": SPATIAL_ALIGNMENT_CHECK
                }
            },
            "statistics": self.stats,
            "processed_scenes": [m["scene_id"] for m in all_metadata]
        }
        
        summary_path = self.processed_dir / "ingestion_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"Summary saved to: {summary_path}")
        print("\nPipeline complete!")


def main():
    """Main entry point for ingestion pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sentinel-2 Ingestion Pipeline")
    parser.add_argument("--raw-dir", type=str, default=str(RAW_DATA_DIR),
                       help="Directory containing raw SAFE files")
    parser.add_argument("--processed-dir", type=str, default=str(PROCESSED_DATA_DIR),
                       help="Directory for processed output")
    parser.add_argument("--overwrite", action="store_true",
                       help="Overwrite existing processed files")
    parser.add_argument("--years", type=int, nargs="+",
                       help="Specific years to process (default: all)")
    
    args = parser.parse_args()
    
    # Run pipeline
    pipeline = Sentinel2IngestionPipeline(
        raw_dir=Path(args.raw_dir),
        processed_dir=Path(args.processed_dir),
        overwrite=args.overwrite
    )
    
    pipeline.run_pipeline(specific_years=args.years)


if __name__ == "__main__":
    main()