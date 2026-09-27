"""
Phase 4 - Standalone Quality Processing Pipeline
=================================================
Operates on already-ingested GeoTIFFs produced by Phase 2/3.
Does NOT re-read raw SAFE/JP2 files.

Reuses (does NOT duplicate):
    ImageProcessor          - create_valid_mask(), _get_geotiff_info(), _resample_array()
    QualityProcessor        - calculate_quality_statistics(), apply_cloud_shadow_buffer(),
                              normalize_reflectance(), apply_quality_mask_to_band(),
                              verify_spatial_alignment()
    MetadataExtractor       - save_metadata() / load_metadata()
    ingestion_config        - all SCL class lists, L2A scaling constants, feature flags

Pipeline per scene
------------------
    existing SCL.tif
        ↓
    validate SCL found + CRS/dims intact
        ↓
    (optional) morphological cloud/shadow buffer
        ↓
    valid_mask.tif  (1 = valid, 0 = invalid)
        ↓
    quality statistics  (per SCL class + group totals)
        ↓
    (optional) reflectance normalization -> normalized/{band}_normalized.tif
        ↓
    (optional) apply mask to bands      -> masked/{band}_masked.tif
        ↓
    quality_report.json  (per scene, appended to existing metadata.json)

Cross-scene (after all scenes processed)
-----------------------------------------
    spatial alignment verification across 2022 / 2023 / 2024
        ↓
    phase4_summary.json
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# ---------------------------------------------------------------------------
# Path bootstrap - allows running as __main__ from backend/
# ---------------------------------------------------------------------------
sys.path.append(str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Reuse existing utilities - do NOT copy/rewrite these
# ---------------------------------------------------------------------------
from utils.image_processor import ImageProcessor
from utils.quality_processor import QualityProcessor
from utils.metadata_extractor import load_metadata, MetadataExtractor
from utils.safe_parser import SAFEParser, discover_safe_files, group_safe_by_year

from config.ingestion_config import (
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    SCL_CLASSES,
    VALID_SCL_CLASSES,
    SCL_CLASS_GROUPS,
    CLOUD_SHADOW_BUFFER_CLASSES,
    L2A_SCALE_FACTOR,
    L2A_REFLECTANCE_OFFSET,
    APPLY_QUALITY_MASK_TO_BANDS,
    CLOUD_SHADOW_BUFFER_SIZE,
    REFLECTANCE_NORMALIZATION,
    SPATIAL_ALIGNMENT_CHECK,
    OVERWRITE_EXISTING,
)


# ===========================================================================
# SceneQualityProcessor - per-scene logic
# ===========================================================================

class SceneQualityProcessor:
    """
    Applies Phase 4 quality steps to a single already-processed scene.

    All heavy lifting is delegated to the existing ImageProcessor and
    QualityProcessor instances that are passed in - zero duplication.
    """

    def __init__(
        self,
        image_processor: ImageProcessor,
        quality_processor: QualityProcessor,
        overwrite: bool = False,
        cloud_buffer_size: int = CLOUD_SHADOW_BUFFER_SIZE,
        apply_normalization: bool = REFLECTANCE_NORMALIZATION,
        apply_mask_to_bands: bool = APPLY_QUALITY_MASK_TO_BANDS,
        scale_factor: float = L2A_SCALE_FACTOR,
        reflectance_offset: float = L2A_REFLECTANCE_OFFSET,
    ):
        """
        Args:
            image_processor:     Shared ImageProcessor (reused from Phase 2/3)
            quality_processor:   Shared QualityProcessor (reused from Phase 2/3)
            overwrite:           Re-create outputs even if they exist
            cloud_buffer_size:   Morphological dilation radius in pixels (0 = disabled)
            apply_normalization: Write float32 reflectance copies of each band
            apply_mask_to_bands: Write cloud-masked copies of each band
            scale_factor:        Sentinel-2 L2A DN-to-reflectance scale
            reflectance_offset:  Additive offset after scaling (baseline ≥ N04.00 -> -0.1)
        """
        self.ip = image_processor
        self.qp = quality_processor
        self.overwrite = overwrite
        self.cloud_buffer_size = cloud_buffer_size
        self.apply_normalization = apply_normalization
        self.apply_mask_to_bands = apply_mask_to_bands
        self.scale_factor = scale_factor
        self.reflectance_offset = reflectance_offset

    # ------------------------------------------------------------------
    # Step 1 - Validate that the existing SCL.tif is usable
    # ------------------------------------------------------------------
    def validate_scl(self, scl_path: Path) -> Dict:
        """
        Confirm that the SCL GeoTIFF produced by Phase 2/3 is readable
        and has valid geospatial metadata.

        Returns:
            geo_info dict from ImageProcessor._get_geotiff_info()

        Raises:
            FileNotFoundError if SCL.tif is missing
        """
        if not scl_path.exists():
            raise FileNotFoundError(
                f"SCL.tif not found at {scl_path}. "
                "Run Phase 2/3 ingestion first."
            )
        # Reuse existing _get_geotiff_info - no duplication
        geo_info = self.ip._get_geotiff_info(scl_path)
        if geo_info["crs"] is None:
            raise ValueError(f"SCL.tif has no CRS: {scl_path}")
        return geo_info

    # ------------------------------------------------------------------
    # Step 2 - (Optional) cloud/shadow buffer
    # ------------------------------------------------------------------
    def run_cloud_buffer(self, scl_path: Path, quality_dir: Path) -> Tuple[Path, Optional[Dict]]:
        """
        Apply morphological dilation around cloud/shadow pixels.

        If buffer_size == 0 the original SCL is returned unchanged.

        Returns:
            (effective_scl_path, geo_info_or_None)
        """
        if self.cloud_buffer_size == 0:
            print("  [buffer] Disabled (cloud_buffer_size=0)")
            return scl_path, None

        buffered_path = quality_dir / "SCL_buffered.tif"
        # Reuse QualityProcessor.apply_cloud_shadow_buffer()
        geo = self.qp.apply_cloud_shadow_buffer(
            scl_path=scl_path,
            output_path=buffered_path,
            buffer_size=self.cloud_buffer_size,
            cloud_shadow_classes=CLOUD_SHADOW_BUFFER_CLASSES,
            overwrite=self.overwrite,
        )
        print(f"  [buffer] Cloud/shadow buffer applied ({self.cloud_buffer_size}px) -> {buffered_path.name}")
        return buffered_path, geo

    # ------------------------------------------------------------------
    # Step 3 - Regenerate valid_mask.tif from (optionally buffered) SCL
    # ------------------------------------------------------------------
    def regenerate_valid_mask(
        self, effective_scl_path: Path, quality_dir: Path
    ) -> Tuple[Path, Dict]:
        """
        Create valid_mask.tif where 1 = valid pixel, 0 = invalid.

        Preserves CRS / transform / resolution / width / height from SCL.
        Reuses ImageProcessor.create_valid_mask().

        Returns:
            (valid_mask_path, geo_info)
        """
        # If a buffer was applied use a distinct filename to not overwrite the
        # Phase 2/3 base mask - keeps provenance clean.
        if self.cloud_buffer_size > 0:
            mask_path = quality_dir / "valid_mask_buffered.tif"
        else:
            mask_path = quality_dir / "valid_mask.tif"

        geo = self.ip.create_valid_mask(
            scl_path=effective_scl_path,
            output_path=mask_path,
            valid_classes=VALID_SCL_CLASSES,
            overwrite=self.overwrite,
        )
        print(f"  [mask]   valid_mask -> {mask_path.name}  "
              f"(valid classes: {VALID_SCL_CLASSES})")
        return mask_path, geo

    # ------------------------------------------------------------------
    # Step 4 - Quality statistics
    # ------------------------------------------------------------------
    def compute_quality_stats(self, scl_path: Path) -> Dict:
        """
        Compute per-class and group statistics from SCL.

        Produces:
            total_pixels, valid_pixels, invalid_pixels, valid_percentage,
            cloud_all %, cloud_shadow %, snow_ice %, vegetation %, water %
            and a full class_breakdown.

        Reuses QualityProcessor.calculate_quality_statistics().
        """
        stats = self.qp.calculate_quality_statistics(scl_path, SCL_CLASSES, SCL_CLASS_GROUPS)

        # Surface the most important numbers for easy reading
        pct = stats.get("valid_percentage", 0.0)
        cloud_pct = stats["group_statistics"].get("cloud_all", {}).get("percentage", 0.0)
        shadow_pct = stats["group_statistics"].get("cloud_shadow", {}).get("percentage", 0.0)
        snow_pct = stats["group_statistics"].get("snow_ice", {}).get("percentage", 0.0)

        print(
            f"  [stats]  valid={pct:.1f}%  cloud={cloud_pct:.1f}%  "
            f"shadow={shadow_pct:.1f}%  snow={snow_pct:.1f}%"
        )
        return stats

    # ------------------------------------------------------------------
    # Step 5 - (Optional) reflectance normalization
    # ------------------------------------------------------------------
    def normalize_bands(
        self, band_paths: Dict[str, Path], year_dir: Path
    ) -> Dict[str, Dict]:
        """
        Write float32 reflectance copies of each band.

        Formula:  reflectance = DN × scale_factor + reflectance_offset
        For N05.10 data: reflectance = DN × 0.0001 - 0.1

        Output dir: {year_dir}/normalized/
        Reuses QualityProcessor.normalize_reflectance().

        Returns:
            dict mapping band_name -> {"source", "output", "status"}
        """
        if not self.apply_normalization:
            print("  [norm]   Disabled (REFLECTANCE_NORMALIZATION=False)")
            return {}

        normalized_dir = year_dir / "normalized"
        normalized_dir.mkdir(parents=True, exist_ok=True)
        results: Dict[str, Dict] = {}

        print(
            f"  [norm]   scale={self.scale_factor}  offset={self.reflectance_offset}  "
            f"-> {normalized_dir.name}/"
        )

        for band_name, band_path in band_paths.items():
            out_path = normalized_dir / f"{band_name}_normalized.tif"
            try:
                self.qp.normalize_reflectance(
                    band_path=band_path,
                    output_path=out_path,
                    scale_factor=self.scale_factor,
                    offset=self.reflectance_offset,
                    overwrite=self.overwrite,
                )
                results[band_name] = {
                    "source": str(band_path),
                    "output": str(out_path),
                    "status": "success",
                }
            except Exception as exc:
                print(f"    [norm]   WARN: {band_name} failed - {exc}")
                results[band_name] = {
                    "source": str(band_path),
                    "output": None,
                    "status": f"failed: {exc}",
                }

        ok = sum(1 for v in results.values() if v["status"] == "success")
        print(f"  [norm]   {ok}/{len(results)} bands normalized")
        return results

    # ------------------------------------------------------------------
    # Step 6 - (Optional) apply valid mask to bands
    # ------------------------------------------------------------------
    def mask_bands(
        self,
        band_paths: Dict[str, Path],
        valid_mask_path: Path,
        year_dir: Path,
    ) -> Dict[str, Dict]:
        """
        Write cloud-masked copies of each band (invalid pixels -> nodata=-9999).

        Output dir: {year_dir}/masked/
        Reuses QualityProcessor.apply_quality_mask_to_band().

        NOTE: Disabled by default (APPLY_QUALITY_MASK_TO_BANDS=False) to avoid
              creating ~3 GB of duplicate files.  Enable via CLI --apply-mask or
              by setting APPLY_QUALITY_MASK_TO_BANDS=True in ingestion_config.py.

        Returns:
            dict mapping band_name -> {"source", "output", "status"}
        """
        if not self.apply_mask_to_bands:
            print("  [mask]   Band masking disabled (APPLY_QUALITY_MASK_TO_BANDS=False)")
            return {}

        masked_dir = year_dir / "masked"
        masked_dir.mkdir(parents=True, exist_ok=True)
        results: Dict[str, Dict] = {}

        print(f"  [mask]   Applying valid_mask -> {masked_dir.name}/")

        for band_name, band_path in band_paths.items():
            out_path = masked_dir / f"{band_name}_masked.tif"
            try:
                self.qp.apply_quality_mask_to_band(
                    band_path=band_path,
                    valid_mask_path=valid_mask_path,
                    output_path=out_path,
                    nodata_value=-9999,
                    overwrite=self.overwrite,
                )
                results[band_name] = {
                    "source": str(band_path),
                    "output": str(out_path),
                    "status": "success",
                }
            except Exception as exc:
                print(f"    [mask]   WARN: {band_name} failed - {exc}")
                results[band_name] = {
                    "source": str(band_path),
                    "output": None,
                    "status": f"failed: {exc}",
                }

        ok = sum(1 for v in results.values() if v["status"] == "success")
        print(f"  [mask]   {ok}/{len(results)} bands masked")
        return results


# ===========================================================================
# Phase4Pipeline - multi-scene orchestrator
# ===========================================================================

class Phase4Pipeline:
    """
    Standalone Phase 4 pipeline that reads already-processed data from Phase 2/3.

    One reusable pipeline applied identically to 2022, 2023, and 2024 scenes.
    No per-year duplicated code.

    Usage
    -----
    From CLI:
        cd backend
        python -m app.quality.phase4_pipeline

    From Python:
        from app.quality import Phase4Pipeline
        pipeline = Phase4Pipeline()
        pipeline.run()
    """

    def __init__(
        self,
        processed_dir: Path = PROCESSED_DATA_DIR,
        raw_dir: Path = RAW_DATA_DIR,
        overwrite: bool = OVERWRITE_EXISTING,
        cloud_buffer_size: int = CLOUD_SHADOW_BUFFER_SIZE,
        apply_normalization: bool = REFLECTANCE_NORMALIZATION,
        apply_mask_to_bands: bool = APPLY_QUALITY_MASK_TO_BANDS,
        spatial_alignment_check: bool = SPATIAL_ALIGNMENT_CHECK,
        scale_factor: float = L2A_SCALE_FACTOR,
        reflectance_offset: float = L2A_REFLECTANCE_OFFSET,
    ):
        self.processed_dir = Path(processed_dir)
        self.raw_dir = Path(raw_dir)
        self.overwrite = overwrite
        self.spatial_alignment_check = spatial_alignment_check

        # Shared processor instances - reused from Phase 2/3 code, not duplicated
        self._image_processor = ImageProcessor(quality_check=True)
        self._quality_processor = QualityProcessor(self._image_processor)

        # Per-scene worker (holds all Phase 4 step logic)
        self._scene_processor = SceneQualityProcessor(
            image_processor=self._image_processor,
            quality_processor=self._quality_processor,
            overwrite=overwrite,
            cloud_buffer_size=cloud_buffer_size,
            apply_normalization=apply_normalization,
            apply_mask_to_bands=apply_mask_to_bands,
            scale_factor=scale_factor,
            reflectance_offset=reflectance_offset,
        )

        self._stats: Dict = {
            "scenes_found": 0,
            "scenes_processed": 0,
            "scenes_failed": 0,
            "bands_normalized": 0,
            "bands_masked": 0,
        }

    # ------------------------------------------------------------------
    # Scene discovery - delegate to existing safe_parser utilities
    # ------------------------------------------------------------------
    def _discover_processed_scenes(self) -> List[Tuple[int, Path]]:
        """
        Find all year-folders that contain a quality/SCL.tif.

        Returns list of (year, year_dir) sorted by year.
        """
        scenes: List[Tuple[int, Path]] = []
        if not self.processed_dir.exists():
            print(f"[ERROR] Processed directory not found: {self.processed_dir}")
            return scenes

        for year_dir in sorted(self.processed_dir.iterdir()):
            if not year_dir.is_dir():
                continue
            try:
                year = int(year_dir.name)
            except ValueError:
                continue  # skip non-year directories (e.g. ingestion_summary.json)

            scl_path = year_dir / "quality" / "SCL.tif"
            if scl_path.exists():
                scenes.append((year, year_dir))
                print(f"  Found scene: {year}  ({year_dir})")
            else:
                print(f"  WARN: No SCL.tif for year {year} - skipping")

        return scenes

    # ------------------------------------------------------------------
    # Band file discovery - read paths from existing metadata.json
    # ------------------------------------------------------------------
    def _load_band_paths(self, year_dir: Path) -> Dict[str, Path]:
        """
        Read the list of processed band GeoTIFFs from the metadata.json
        that Phase 2/3 already wrote.  Returns only files that exist on disk.

        Reuses load_metadata() from metadata_extractor - no duplication.
        """
        metadata_path = year_dir / "metadata.json"
        band_paths: Dict[str, Path] = {}

        if not metadata_path.exists():
            # Fallback: scan bands/ directory directly
            bands_dir = year_dir / "bands"
            if bands_dir.exists():
                for tif in sorted(bands_dir.glob("*.tif")):
                    band_name = tif.stem   # e.g. "B02"
                    band_paths[band_name] = tif
            return band_paths

        try:
            metadata = load_metadata(metadata_path)
            for band_name, band_data in metadata.get("bands", {}).items():
                processed_file = band_data.get("processed_file")
                if processed_file:
                    p = Path(processed_file)
                    if p.exists():
                        band_paths[band_name] = p
        except Exception as exc:
            print(f"  WARN: Could not read metadata.json ({exc}). Scanning bands/ dir.")
            bands_dir = year_dir / "bands"
            if bands_dir.exists():
                for tif in sorted(bands_dir.glob("*.tif")):
                    band_paths[tif.stem] = tif

        return band_paths

    # ------------------------------------------------------------------
    # Per-scene quality report writer
    # ------------------------------------------------------------------
    @staticmethod
    def _save_quality_report(report: Dict, output_path: Path) -> None:
        """
        Persist per-scene Phase 4 quality report to JSON.
        Reuses json serialisation pattern from MetadataExtractor.save_metadata().
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as fh:
            json.dump(report, fh, indent=2, default=str)
        print(f"  [report] Saved -> {output_path}")

    # ------------------------------------------------------------------
    # Core: process a single scene
    # ------------------------------------------------------------------
    def _process_scene(self, year: int, year_dir: Path) -> Optional[Dict]:
        """
        Run the full Phase 4 sequence for one scene year-folder.

        Returns the quality_report dict on success, or None on failure.
        """
        print(f"\n{'-'*60}")
        print(f"  Scene {year}  ({year_dir.name})")
        print(f"{'-'*60}")

        quality_dir = year_dir / "quality"
        scl_path = quality_dir / "SCL.tif"

        report: Dict = {
            "year": year,
            "scene_dir": str(year_dir),
            "phase4_timestamp": datetime.now().isoformat(),
            "processing_steps": {},
            "quality_statistics": None,
            "spatial_info": None,
        }

        try:
            # ----------------------------------------------------------
            # Step 1 - Validate SCL
            # ----------------------------------------------------------
            print("  Step 1: Validating SCL.tif ...")
            scl_geo = self._scene_processor.validate_scl(scl_path)
            report["spatial_info"] = {
                "crs":        scl_geo["crs"],
                "resolution": list(scl_geo["resolution"]),
                "width":      scl_geo["width"],
                "height":     scl_geo["height"],
                "bounds": {
                    "left":   scl_geo["bounds"].left,
                    "bottom": scl_geo["bounds"].bottom,
                    "right":  scl_geo["bounds"].right,
                    "top":    scl_geo["bounds"].top,
                },
            }
            print(f"  [ok]  CRS={scl_geo['crs']}  "
                  f"{scl_geo['width']}×{scl_geo['height']}  "
                  f"res={scl_geo['resolution'][0]}m")

            # ----------------------------------------------------------
            # Step 2 - (Optional) cloud/shadow buffer
            # ----------------------------------------------------------
            print("  Step 2: Cloud/shadow buffer ...")
            effective_scl, buffer_geo = self._scene_processor.run_cloud_buffer(
                scl_path, quality_dir
            )
            if buffer_geo:
                report["processing_steps"]["cloud_buffer"] = {
                    "output": str(quality_dir / "SCL_buffered.tif"),
                    "buffer_px": self._scene_processor.cloud_buffer_size,
                    "status": "success",
                }

            # ----------------------------------------------------------
            # Step 3 - valid_mask.tif
            # ----------------------------------------------------------
            print("  Step 3: Generating valid_mask.tif ...")
            valid_mask_path, mask_geo = self._scene_processor.regenerate_valid_mask(
                effective_scl, quality_dir
            )
            report["processing_steps"]["valid_mask"] = {
                "output": str(valid_mask_path),
                "valid_classes": VALID_SCL_CLASSES,
                "crs": mask_geo["crs"],
                "width": mask_geo["width"],
                "height": mask_geo["height"],
                "resolution": list(mask_geo["resolution"]),
                "status": "success",
            }

            # ----------------------------------------------------------
            # Step 4 - Quality statistics
            # ----------------------------------------------------------
            print("  Step 4: Computing quality statistics ...")
            quality_stats = self._scene_processor.compute_quality_stats(effective_scl)
            report["quality_statistics"] = quality_stats

            # ----------------------------------------------------------
            # Step 5 - (Optional) reflectance normalization
            # ----------------------------------------------------------
            print("  Step 5: Reflectance normalization ...")
            band_paths = self._load_band_paths(year_dir)
            if not band_paths:
                print("  WARN: No band files found - skipping normalization & masking")
            else:
                norm_results = self._scene_processor.normalize_bands(band_paths, year_dir)
                if norm_results:
                    report["processing_steps"]["normalization"] = norm_results
                    self._stats["bands_normalized"] += sum(
                        1 for v in norm_results.values() if v["status"] == "success"
                    )

                # ----------------------------------------------------------
                # Step 6 - (Optional) apply mask to bands
                # ----------------------------------------------------------
                print("  Step 6: Applying quality mask to bands ...")
                mask_results = self._scene_processor.mask_bands(
                    band_paths, valid_mask_path, year_dir
                )
                if mask_results:
                    report["processing_steps"]["band_masking"] = mask_results
                    self._stats["bands_masked"] += sum(
                        1 for v in mask_results.values() if v["status"] == "success"
                    )

            # ----------------------------------------------------------
            # Save per-scene quality report
            # ----------------------------------------------------------
            report_path = quality_dir / "quality_report.json"
            self._save_quality_report(report, report_path)

            self._stats["scenes_processed"] += 1
            print(f"  [OK] Scene {year} complete")
            return report

        except Exception as exc:
            print(f"  [FAIL] Scene {year} failed: {exc}")
            report["error"] = str(exc)
            self._stats["scenes_failed"] += 1
            return None

    # ------------------------------------------------------------------
    # Cross-scene spatial alignment verification
    # ------------------------------------------------------------------
    def _verify_alignment(self, scene_reports: List[Dict]) -> Dict:
        """
        Check CRS / resolution / bounds consistency across all processed scenes.

        Collects the valid_mask.tif paths from each scene's quality report
        (same grid as SCL) and passes them to the existing
        QualityProcessor.verify_spatial_alignment() - no duplication.

        Returns the alignment results dict.
        """
        if not self.spatial_alignment_check:
            print("\n[alignment] Spatial alignment check disabled.")
            return {"status": "disabled"}

        print(f"\n{'='*60}")
        print("SPATIAL ALIGNMENT VERIFICATION")
        print(f"{'='*60}")

        reference_files: List[Path] = []
        for report in scene_reports:
            if report is None:
                continue
            vm = report.get("processing_steps", {}).get("valid_mask", {}).get("output")
            if vm:
                p = Path(vm)
                if p.exists():
                    reference_files.append(p)

        if len(reference_files) < 2:
            print("[alignment] Need at least 2 scenes - skipping.")
            return {"status": "insufficient_data"}

        # Reuse QualityProcessor.verify_spatial_alignment()
        results = self._quality_processor.verify_spatial_alignment(reference_files)

        overall = results.get("overall_alignment", "unknown")
        print(f"  Overall alignment: {overall}")
        for name, comp in results.get("comparisons", {}).items():
            status = comp.get("status", "?")
            print(f"  {name}: {status}", end="")
            if status == "misaligned":
                print(f"  (CRS={comp['crs_match']}, "
                      f"res={comp['resolution_match']}, "
                      f"dims={comp['dimensions_match']}, "
                      f"bounds={comp['bounds_match']})", end="")
            print()

        return results

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def run(self, specific_years: Optional[List[int]] = None) -> Dict:
        """
        Execute Phase 4 for all discovered scenes (or a subset of years).

        Args:
            specific_years: Optional list of years to process.  If None,
                            all years with a valid SCL.tif are processed.

        Returns:
            phase4_summary dict (also written to data/processed/phase4_summary.json)
        """
        print("\n" + "="*60)
        print("PHASE 4 - QUALITY PROCESSING PIPELINE")
        print("="*60)
        print(f"  Processed dir : {self.processed_dir}")
        print(f"  Overwrite     : {self.overwrite}")
        print(f"  Buffer size   : {self._scene_processor.cloud_buffer_size}px")
        print(f"  Normalize     : {self._scene_processor.apply_normalization}")
        print(f"  Scale / Offset: {self._scene_processor.scale_factor} / "
              f"{self._scene_processor.reflectance_offset}")
        print(f"  Mask bands    : {self._scene_processor.apply_mask_to_bands}")
        print(f"  Align check   : {self.spatial_alignment_check}")
        print()

        # 1 - Discover scenes
        print("Discovering processed scenes ...")
        all_scenes = self._discover_processed_scenes()

        if not all_scenes:
            print("[ERROR] No processed scenes found. Run Phase 2/3 ingestion first.")
            return {}

        self._stats["scenes_found"] = len(all_scenes)

        # 2 - Optional year filter
        if specific_years:
            all_scenes = [(yr, d) for yr, d in all_scenes if yr in specific_years]
            print(f"Year filter applied: {specific_years}")

        # 3 - Process each scene with the SAME pipeline (no per-year duplication)
        print(f"\nProcessing {len(all_scenes)} scene(s) ...")
        scene_reports: List[Optional[Dict]] = []
        for year, year_dir in all_scenes:
            report = self._process_scene(year, year_dir)
            scene_reports.append(report)

        successful_reports = [r for r in scene_reports if r is not None]

        # 4 - Cross-scene spatial alignment
        alignment_results = self._verify_alignment(successful_reports)
        self._stats["spatial_alignment"] = alignment_results

        # 5 - Build and save summary
        summary = {
            "phase": "Phase 4 - Quality Processing",
            "pipeline_run": datetime.now().isoformat(),
            "configuration": {
                "processed_dir": str(self.processed_dir),
                "overwrite": self.overwrite,
                "cloud_buffer_size": self._scene_processor.cloud_buffer_size,
                "reflectance_normalization": self._scene_processor.apply_normalization,
                "scale_factor": self._scene_processor.scale_factor,
                "reflectance_offset": self._scene_processor.reflectance_offset,
                "apply_mask_to_bands": self._scene_processor.apply_mask_to_bands,
                "spatial_alignment_check": self.spatial_alignment_check,
                "valid_scl_classes": VALID_SCL_CLASSES,
                "cloud_buffer_classes": CLOUD_SHADOW_BUFFER_CLASSES,
            },
            "statistics": self._stats,
            "scenes": [r for r in scene_reports if r is not None],
            "spatial_alignment": alignment_results,
        }

        summary_path = self.processed_dir / "phase4_summary.json"
        with open(summary_path, "w") as fh:
            json.dump(summary, fh, indent=2, default=str)

        # 6 - Print final summary
        print("\n" + "="*60)
        print("PHASE 4 SUMMARY")
        print("="*60)
        print(f"  Scenes found     : {self._stats['scenes_found']}")
        print(f"  Scenes processed : {self._stats['scenes_processed']}")
        print(f"  Scenes failed    : {self._stats['scenes_failed']}")
        print(f"  Bands normalized : {self._stats['bands_normalized']}")
        print(f"  Bands masked     : {self._stats['bands_masked']}")
        overall_align = alignment_results.get("overall_alignment", alignment_results.get("status", "?"))
        print(f"  Spatial align    : {overall_align}")
        print(f"\n  Summary -> {summary_path}")
        print("\nPhase 4 complete!")

        return summary


# ===========================================================================
# CLI entry point
# ===========================================================================

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Phase 4 - Sentinel-2 Quality Processing Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--processed-dir", type=str, default=str(PROCESSED_DATA_DIR),
        help="Directory containing Phase 2/3 processed output",
    )
    p.add_argument(
        "--overwrite", action="store_true",
        help="Re-create outputs even if they already exist",
    )
    p.add_argument(
        "--years", type=int, nargs="+", metavar="YEAR",
        help="Process only these years (default: all discovered)",
    )
    p.add_argument(
        "--buffer-size", type=int, default=CLOUD_SHADOW_BUFFER_SIZE,
        help="Morphological dilation radius around cloud/shadow in pixels "
             "(0 = disabled)",
    )
    p.add_argument(
        "--no-normalize", action="store_true",
        help="Skip reflectance normalization",
    )
    p.add_argument(
        "--apply-mask", action="store_true",
        help="Write cloud-masked band copies (default: off - saves ~3 GB)",
    )
    p.add_argument(
        "--no-alignment-check", action="store_true",
        help="Skip multi-temporal spatial alignment verification",
    )
    p.add_argument(
        "--scale-factor", type=float, default=L2A_SCALE_FACTOR,
        help="Sentinel-2 L2A DN->reflectance scale factor",
    )
    p.add_argument(
        "--reflectance-offset", type=float, default=L2A_REFLECTANCE_OFFSET,
        help="Additive offset after scaling (baseline >= N04.00 -> -0.1)",
    )
    return p


def main():
    args = _build_arg_parser().parse_args()

    pipeline = Phase4Pipeline(
        processed_dir=Path(args.processed_dir),
        overwrite=args.overwrite,
        cloud_buffer_size=args.buffer_size,
        apply_normalization=not args.no_normalize,
        apply_mask_to_bands=args.apply_mask,
        spatial_alignment_check=not args.no_alignment_check,
        scale_factor=args.scale_factor,
        reflectance_offset=args.reflectance_offset,
    )

    pipeline.run(specific_years=args.years)


if __name__ == "__main__":
    main()
