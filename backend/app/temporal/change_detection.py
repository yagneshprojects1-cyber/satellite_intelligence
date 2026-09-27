"""
Multi-Temporal Change Detection - Phase 11
Detects meaningful changes between before and after satellite images
"""

import json
import time
import numpy as np
import torch
import rasterio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from scipy.ndimage import binary_dilation, label


class ChangeType(Enum):
    """Binary change type classifications (for ChangeFormer)"""
    NO_CHANGE = "No Change"
    CHANGE = "Change"


@dataclass
class ChangeResult:
    """Data class for change detection result"""
    pair_id: str
    before_date: str
    after_date: str
    bbox: Dict[str, float]
    change_mask_path: str
    change_percentage: float
    confidence: float
    model_used: str
    processing_time: float
    change_type: str
    before_path: str
    after_path: str
    crs: str
    resolution: float
    width: int
    height: int


class ChangeDetector:
    """
    Detects changes between before and after satellite images.
    Implements both baseline and deep learning methods.
    """
    
    def __init__(self, 
                 pairs_dir: Path = Path("data/temporal_pairs"),
                 output_dir: Path = Path("data/change_results"),
                 changeformer_path: Optional[Path] = None,
                 changeformer_repo: Optional[Path] = None,
                 cloud_shadow_buffer: int = 0,
                 min_valid_percentage: float = 50.0,
                 quality_threshold: float = 0.7):
        """
        Initialize change detector.
        
        Args:
            pairs_dir: Directory containing temporal pairs from Phase 10
            output_dir: Directory for change detection results
            changeformer_path: Optional path to ChangeFormer model checkpoint
            changeformer_repo: Optional path to ChangeFormer repository
            cloud_shadow_buffer: Buffer size for cloud/shadow masking (pixels)
            min_valid_percentage: Minimum valid pixel percentage for processing
            quality_threshold: Minimum quality score for change detection
        """
        self.pairs_dir = Path(pairs_dir)
        self.output_dir = Path(output_dir)
        self.changeformer_path = changeformer_path
        self.changeformer_repo = changeformer_repo
        self.cloud_shadow_buffer = cloud_shadow_buffer
        self.min_valid_percentage = min_valid_percentage
        self.quality_threshold = quality_threshold
        
        # SCL valid classes (Sentinel-2)
        self.valid_scl_classes = [0, 1, 2, 3, 4, 5, 7]  # No data, saturated, dark, cloud shadow, vegetation, water, unclassified
        self.cloud_scl_classes = [8, 9, 10, 11]  # Cloud, cirrus, snow, water
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "2022_2023").mkdir(exist_ok=True)
        (self.output_dir / "2023_2024").mkdir(exist_ok=True)
        (self.output_dir / "2022_2024").mkdir(exist_ok=True)
        
        # Initialize ChangeFormer if path provided
        self.changeformer_model = None
        self.changeformer_device = None
        if changeformer_path and changeformer_path.exists():
            self._load_changeformer()
    
    def _load_changeformer(self):
        """Load ChangeFormer model from checkpoint."""
        try:
            print(f"Loading ChangeFormer model from {self.changeformer_path}")
            
            # Add ChangeFormer repo to path if provided
            if self.changeformer_repo and self.changeformer_repo.exists():
                import sys
                sys.path.insert(0, str(self.changeformer_repo))
            
            # Import ChangeFormer components
            from models.networks import define_G
            
            # Determine device
            self.changeformer_device = torch.device("cpu")  # Force CPU for now
            
            # Create model directly
            class Args:
                def __init__(self):
                    self.n_class = 2
                    self.embed_dim = 256
                    self.net_G = 'ChangeFormerV6'
                    self.gpu_ids = []  # Empty for CPU
            
            args = Args()
            
            # Initialize model
            self.changeformer_model = define_G(args=args, gpu_ids=args.gpu_ids)
            self.changeformer_model.to(self.changeformer_device)
            self.changeformer_model.eval()
            
            # Load checkpoint (weights_only=False for compatibility with older checkpoints)
            checkpoint = torch.load(self.changeformer_path, map_location=self.changeformer_device, weights_only=False)
            self.changeformer_model.load_state_dict(checkpoint['model_G_state_dict'])
            
            print(f"ChangeFormer model loaded successfully on {self.changeformer_device}")
            
        except Exception as e:
            print(f"Error loading ChangeFormer: {e}")
            print("Falling back to baseline method")
            self.changeformer_model = None
    
    def _load_pair(self, pair_file: Path) -> Optional[Dict]:
        """
        Load temporal pair metadata.
        
        Args:
            pair_file: Path to pair JSON file
            
        Returns:
            Pair metadata dictionary or None if failed
        """
        try:
            with open(pair_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading pair from {pair_file}: {e}")
            return None
    
    def _load_tile_band(self, tile_path: Path, band_name: str) -> Optional[np.ndarray]:
        """
        Load a specific band from a tile.
        
        Args:
            tile_path: Path to tile directory
            band_name: Band filename (e.g., "B04.tif")
            
        Returns:
            Band array or None if failed
        """
        band_file = tile_path / band_name
        if not band_file.exists():
            return None
        
        try:
            with rasterio.open(band_file) as src:
                return src.read(1)
        except Exception as e:
            print(f"Error loading band {band_name} from {tile_path}: {e}")
            return None
    
    def _load_quality_mask(self, tile_path: Path) -> Optional[np.ndarray]:
        """
        Load quality mask (SCL) from tile with improved false alarm reduction.
        
        Args:
            tile_path: Path to tile directory
            
        Returns:
            Quality mask array or None if failed
        """
        scl_file = tile_path / "SCL.tif"
        if not scl_file.exists():
            # If no SCL, assume all pixels are valid
            return None
        
        try:
            with rasterio.open(scl_file) as src:
                scl = src.read(1)
                
                # Valid pixels based on SCL classes
                valid_mask = np.isin(scl, self.valid_scl_classes)
                
                # Apply cloud/shadow buffering if enabled
                if self.cloud_shadow_buffer > 0:
                    valid_mask = self._apply_cloud_shadow_buffer(scl, valid_mask)
                
                return valid_mask.astype(np.uint8)
        except Exception as e:
            print(f"Error loading SCL from {tile_path}: {e}")
            return None
    
    def _apply_cloud_shadow_buffer(self, scl: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
        """
        Apply buffer around cloud and shadow pixels to reduce false alarms.
        
        Args:
            scl: SCL classification array
            valid_mask: Current valid mask
            
        Returns:
            Updated valid mask with buffer applied
        """
        from scipy.ndimage import binary_dilation
        
        # Create cloud/shadow mask
        cloud_shadow_mask = np.isin(scl, self.cloud_scl_classes)
        
        # Dilate cloud/shadow mask by buffer size
        if self.cloud_shadow_buffer > 0:
            dilated_mask = binary_dilation(cloud_shadow_mask, iterations=self.cloud_shadow_buffer)
            # Mark dilated areas as invalid
            valid_mask = valid_mask & ~dilated_mask
        
        return valid_mask
    
    def _normalize_band(self, band: np.ndarray) -> np.ndarray:
        """
        Normalize band using percentile stretching.
        
        Args:
            band: Band array
            
        Returns:
            Normalized band array
        """
        p2, p98 = np.percentile(band, (2, 98))
        if p98 - p2 > 0:
            band = (band - p2) / (p98 - p2)
        return np.clip(band, 0, 1)
    
    def _calculate_rgb_composite(self, tile_path: Path, for_changeformer: bool = False) -> Optional[np.ndarray]:
        """
        Calculate RGB composite from Sentinel-2 bands.
        
        Args:
            tile_path: Path to tile directory
            for_changeformer: If True, use different normalization for ChangeFormer
            
        Returns:
            RGB composite array or None if failed
        """
        red = self._load_tile_band(tile_path, "B04.tif")
        green = self._load_tile_band(tile_path, "B03.tif")
        blue = self._load_tile_band(tile_path, "B02.tif")
        
        if red is None or green is None or blue is None:
            return None
        
        if for_changeformer:
            # For ChangeFormer, use percentile-based scaling to [0, 255]
            # to handle varying Sentinel-2 reflectance ranges (already 0-1 normalized)
            def scale_to_255(band):
                # Use percentile stretching to utilize full dynamic range
                p2, p98 = np.percentile(band, (2, 98))
                if p98 - p2 > 0:
                    band = (band - p2) / (p98 - p2)
                band = np.clip(band, 0, 1)
                scaled = (band * 255).astype(np.uint8)
                return scaled
            
            red_scaled = scale_to_255(red)
            green_scaled = scale_to_255(green)
            blue_scaled = scale_to_255(blue)
            
            rgb = np.stack([red_scaled, green_scaled, blue_scaled], axis=-1)
        else:
            # Normalize bands for baseline method
            red_norm = self._normalize_band(red)
            green_norm = self._normalize_band(green)
            blue_norm = self._normalize_band(blue)
            
            # Stack
            rgb = np.stack([red_norm, green_norm, blue_norm], axis=-1)
        
        return rgb
    
    def _changeformer_change_detection(self, 
                                       before_rgb: np.ndarray,
                                       after_rgb: np.ndarray,
                                       before_mask: Optional[np.ndarray] = None,
                                       after_mask: Optional[np.ndarray] = None) -> Tuple[np.ndarray, float]:
        """
        ChangeFormer-based change detection.
        
        Args:
            before_rgb: Before RGB image
            after_rgb: After RGB image
            before_mask: Before quality mask (optional)
            after_mask: After quality mask (optional)
            
        Returns:
            Tuple of (change_mask, confidence)
        """
        try:
            print("Running ChangeFormer inference...")
            
            # Prepare input tensors (changeformer expects [B, C, H, W])
            # ChangeFormer expects RGB in range [0, 255]
            before_tensor = torch.from_numpy(before_rgb).permute(2, 0, 1).unsqueeze(0).float()
            after_tensor = torch.from_numpy(after_rgb).permute(2, 0, 1).unsqueeze(0).float()
            
            print(f"Input shapes: before={before_tensor.shape}, after={after_tensor.shape}")
            print(f"Input ranges: before=[{before_tensor.min():.2f}, {before_tensor.max():.2f}], after=[{after_tensor.min():.2f}, {after_tensor.max():.2f}]")
            
            # Normalize to [0, 1] then to [-1, 1] for ChangeFormer
            before_tensor = before_tensor / 255.0
            after_tensor = after_tensor / 255.0
            
            print(f"After [0,1] normalization: before=[{before_tensor.min():.2f}, {before_tensor.max():.2f}], after=[{after_tensor.min():.2f}, {after_tensor.max():.2f}]")
            
            # Normalize to [-1, 1] as per ChangeFormer preprocessing
            before_tensor = (before_tensor - 0.5) / 0.5
            after_tensor = (after_tensor - 0.5) / 0.5
            
            print(f"After [-1,1] normalization: before=[{before_tensor.min():.2f}, {before_tensor.max():.2f}], after=[{after_tensor.min():.2f}, {after_tensor.max():.2f}]")
            
            # Move to device
            before_tensor = before_tensor.to(self.changeformer_device)
            after_tensor = after_tensor.to(self.changeformer_device)
            
            # Run inference
            with torch.no_grad():
                # ChangeFormer expects inputs as (img_in1, img_in2)
                # Output is list of feature maps, last one is the prediction
                print(f"Running model forward pass...")
                output = self.changeformer_model(before_tensor, after_tensor)
                print(f"Model output type: {type(output)}")
                
                if isinstance(output, list):
                    pred = output[-1]  # Last layer is the prediction
                else:
                    pred = output
                
                print(f"Prediction shape: {pred.shape}")
                
                # Get probability map (softmax for binary classification)
                pred_prob = torch.softmax(pred, dim=1)
                change_prob = pred_prob[:, 1, :, :]  # Probability of change class
                
                # Convert to numpy
                change_prob_np = change_prob.cpu().numpy()[0]
            
            print(f"Change probability range: [{change_prob_np.min():.3f}, {change_prob_np.max():.3f}]")
            
            # Apply quality masks if available
            if before_mask is not None:
                change_prob_np = change_prob_np * before_mask
            if after_mask is not None:
                change_prob_np = change_prob_np * after_mask
            
            # Threshold to create binary mask
            threshold = 0.5
            change_mask = (change_prob_np > threshold).astype(np.uint8)
            
            # Calculate confidence as mean change probability
            confidence = float(np.mean(change_prob_np[change_mask == 1])) if np.any(change_mask == 1) else 0.0
            
            print(f"ChangeFormer inference completed. Changed pixels: {np.sum(change_mask)}")
            
            return change_mask, confidence
            
        except Exception as e:
            print(f"Error in ChangeFormer inference: {e}")
            import traceback
            traceback.print_exc()
            print("Falling back to baseline method")
            return self._baseline_change_detection(before_rgb, after_rgb, before_mask, after_mask)
    
    def _baseline_change_detection(self, 
                                    before_rgb: np.ndarray,
                                    after_rgb: np.ndarray,
                                    before_mask: Optional[np.ndarray] = None,
                                    after_mask: Optional[np.ndarray] = None) -> Tuple[np.ndarray, float]:
        """
        Baseline change detection using normalized difference.
        
        Args:
            before_rgb: Before RGB image
            after_rgb: After RGB image
            before_mask: Before quality mask (optional)
            after_mask: After quality mask (optional)
            
        Returns:
            Tuple of (change_mask, confidence)
        """
        # Calculate mean RGB for each image
        before_mean = np.mean(before_rgb, axis=-1)
        after_mean = np.mean(after_rgb, axis=-1)
        
        # Calculate absolute difference
        diff = np.abs(before_mean - after_mean)
        
        # Normalize difference
        diff_norm = diff / (np.max(diff) + 1e-8)
        
        # Apply quality masks if available
        if before_mask is not None:
            diff_norm = diff_norm * before_mask
        if after_mask is not None:
            diff_norm = diff_norm * after_mask
        
        # Threshold for change detection
        threshold = 0.2
        change_mask = (diff_norm > threshold).astype(np.uint8)
        
        # Calculate confidence based on difference magnitude
        confidence = float(np.mean(diff_norm[change_mask == 1])) if np.any(change_mask == 1) else 0.0
        
        return change_mask, confidence
    
    def _calculate_change_percentage(self, change_mask: np.ndarray, 
                                     valid_mask: Optional[np.ndarray] = None) -> float:
        """
        Calculate percentage of changed pixels.
        
        Args:
            change_mask: Binary change mask
            valid_mask: Optional valid pixel mask
            
        Returns:
            Change percentage
        """
        if valid_mask is not None:
            total_valid = np.sum(valid_mask)
            changed_pixels = np.sum(change_mask * valid_mask)
        else:
            total_valid = change_mask.size
            changed_pixels = np.sum(change_mask)
        
        if total_valid > 0:
            return (changed_pixels / total_valid) * 100.0
        return 0.0
    
    def _validate_change_quality(self, 
                                change_mask: np.ndarray,
                                before_mask: Optional[np.ndarray],
                                after_mask: Optional[np.ndarray],
                                confidence: float) -> Tuple[bool, str]:
        """
        Validate change quality to reduce false alarms.
        
        Args:
            change_mask: Binary change mask
            before_mask: Before quality mask
            after_mask: After quality mask
            confidence: Change confidence score
            
        Returns:
            Tuple of (is_valid, reason)
        """
        # Check confidence threshold
        if confidence < self.quality_threshold:
            return False, f"Confidence {confidence:.2f} below threshold {self.quality_threshold}"
        
        # Check if change occurs in valid pixels only
        if before_mask is not None and after_mask is not None:
            combined_valid = before_mask & after_mask
            change_in_valid = np.sum(change_mask * combined_valid)
            total_change = np.sum(change_mask)
            
            if total_change > 0:
                valid_ratio = change_in_valid / total_change
                if valid_ratio < 0.5:  # Less than 50% of change in valid pixels
                    return False, f"Change mostly in invalid pixels (valid ratio: {valid_ratio:.2f})"
        
        # Check for isolated pixels (noise)
        from scipy.ndimage import label
        labeled, num_features = label(change_mask)
        if num_features > 50:  # Too many isolated change regions
            return False, f"Too many isolated change regions ({num_features})"
        
        return True, "Valid"
    
    def _apply_temporal_consistency(self, 
                                   change_mask: np.ndarray,
                                   before_rgb: np.ndarray,
                                   after_rgb: np.ndarray) -> np.ndarray:
        """
        Apply temporal consistency check to reduce false alarms.
        
        Changes that are only due to illumination differences (brightness)
        rather than actual land cover changes are filtered out.
        
        Args:
            change_mask: Binary change mask
            before_rgb: Before RGB image
            after_rgb: After RGB image
            
        Returns:
            Filtered change mask
        """
        # Calculate brightness difference
        before_brightness = np.mean(before_rgb, axis=-1)
        after_brightness = np.mean(after_rgb, axis=-1)
        brightness_diff = np.abs(before_brightness - after_brightness)
        
        # Normalize brightness difference
        brightness_diff_norm = brightness_diff / (np.max(brightness_diff) + 1e-8)
        
        # Filter out changes in areas with only brightness differences
        # (threshold: changes where brightness diff > 0.3 are likely illumination)
        illumination_mask = brightness_diff_norm > 0.3
        
        # Apply filter: keep changes that are NOT illumination-only
        filtered_mask = change_mask & ~illumination_mask
        
        return filtered_mask
    
    def _save_change_mask(self, change_mask: np.ndarray, output_path: Path, 
                          crs: str, transform, width: int, height: int):
        """
        Save change mask as GeoTIFF.
        
        Args:
            change_mask: Change mask array
            output_path: Output file path
            crs: Coordinate reference system
            transform: Affine transform
            width: Image width
            height: Image height
        """
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype=change_mask.dtype,
            crs=crs,
            transform=transform,
            compress='lzw'
        ) as dst:
            dst.write(change_mask, 1)
    
    def detect_change(self, pair_data: Dict, method: str = "baseline") -> Optional[ChangeResult]:
        """
        Detect change for a temporal pair.
        
        Args:
            pair_data: Temporal pair metadata
            method: Detection method ("baseline" or "changeformer")
            
        Returns:
            ChangeResult or None if failed
        """
        start_time = time.time()
        
        before_path = Path(pair_data['before_path'])
        after_path = Path(pair_data['after_path'])
        
        # Load RGB composites (use different normalization for ChangeFormer)
        use_changeformer = (method == "changeformer" and self.changeformer_model is not None)
        before_rgb = self._calculate_rgb_composite(before_path, for_changeformer=use_changeformer)
        after_rgb = self._calculate_rgb_composite(after_path, for_changeformer=use_changeformer)
        
        if before_rgb is None or after_rgb is None:
            print(f"Failed to load RGB for pair {pair_data['pair_id']}")
            return None
        
        # Load quality masks
        before_mask = self._load_quality_mask(before_path)
        after_mask = self._load_quality_mask(after_path)
        
        # Combine quality masks
        combined_mask = None
        if before_mask is not None and after_mask is not None:
            combined_mask = before_mask & after_mask
        elif before_mask is not None:
            combined_mask = before_mask
        elif after_mask is not None:
            combined_mask = after_mask
        
        # Perform change detection
        if method == "changeformer" and self.changeformer_model is not None:
            change_mask, confidence = self._changeformer_change_detection(
                before_rgb, after_rgb, before_mask, after_mask
            )
            model_used = "changeformer"
        else:
            # For baseline, ensure RGB is in [0, 1] range
            if before_rgb.max() > 1.0:
                before_rgb = before_rgb / 255.0
            if after_rgb.max() > 1.0:
                after_rgb = after_rgb / 255.0
            change_mask, confidence = self._baseline_change_detection(
                before_rgb, after_rgb, before_mask, after_mask
            )
            model_used = "baseline"
        
        # Apply temporal consistency check
        change_mask = self._apply_temporal_consistency(change_mask, before_rgb, after_rgb)
        
        # Calculate change percentage
        change_percentage = float(self._calculate_change_percentage(change_mask, combined_mask))
        
        # Validate change quality
        is_valid, validation_reason = self._validate_change_quality(
            change_mask, before_mask, after_mask, confidence
        )
        
        if not is_valid:
            print(f"Change validation failed for {pair_data['pair_id']}: {validation_reason}")
            # Set change percentage to 0 if validation fails
            change_percentage = 0.0
            change_mask = np.zeros_like(change_mask)
        
        # Determine change type
        if change_percentage > 5.0:
            change_type = ChangeType.CHANGE.value
        else:
            change_type = ChangeType.NO_CHANGE.value
        
        # Save change mask
        output_subdir = self.output_dir / f"{pair_data['before_year']}_{pair_data['after_year']}"
        change_mask_path = output_subdir / f"{pair_data['pair_id']}_change_mask.tif"
        
        # Get geospatial info from before tile
        with rasterio.open(before_path / "B04.tif") as src:
            crs = str(src.crs)
            transform = src.transform
            width = src.width
            height = src.height
        
        self._save_change_mask(change_mask, change_mask_path, crs, transform, width, height)
        
        processing_time = float(time.time() - start_time)
        
        # Create result
        result = ChangeResult(
            pair_id=pair_data['pair_id'],
            before_date=pair_data['before_date'],
            after_date=pair_data['after_date'],
            bbox=pair_data['bbox'],
            change_mask_path=str(change_mask_path),
            change_percentage=change_percentage,
            confidence=confidence,
            model_used=model_used,
            processing_time=processing_time,
            change_type=change_type,
            before_path=pair_data['before_path'],
            after_path=pair_data['after_path'],
            crs=crs,
            resolution=pair_data['resolution'],
            width=width,
            height=height
        )
        
        return result
    
    def _save_result(self, result: ChangeResult, output_subdir: Path):
        """
        Save change detection result to JSON file.
        
        Args:
            result: ChangeResult object
            output_subdir: Output subdirectory path
        """
        output_file = output_subdir / f"{result.pair_id}_result.json"
        
        # Check if result already exists (incremental)
        if output_file.exists():
            return
        
        with open(output_file, 'w') as f:
            json.dump(asdict(result), f, indent=2)
    
    def process_pair_directory(self, 
                               year_combination: str, 
                               limit: Optional[int] = None,
                               method: str = "baseline") -> Tuple[List[ChangeResult], Dict[str, int]]:
        """
        Process all pairs in a specific year combination directory.
        
        Args:
            year_combination: Year combination (e.g., "2022_2023")
            limit: Optional limit on number of pairs to process
            method: Detection method
            
        Returns:
            Tuple of (results list, statistics dict)
        """
        pair_dir = self.pairs_dir / year_combination
        output_dir = self.output_dir / year_combination
        
        if not pair_dir.exists():
            print(f"Pair directory not found: {pair_dir}")
            return [], {"total": 0, "processed": 0, "failed": 0}
        
        # Get all pair files
        pair_files = list(pair_dir.glob("*.json"))
        
        if limit:
            pair_files = pair_files[:limit]
        
        print(f"Processing {len(pair_files)} pairs from {year_combination}")
        
        results = []
        failed = 0
        
        for i, pair_file in enumerate(pair_files):
            print(f"  Processing {i+1}/{len(pair_files)}: {pair_file.name}")
            
            pair_data = self._load_pair(pair_file)
            if pair_data is None:
                failed += 1
                continue
            
            result = self.detect_change(pair_data, method=method)
            if result is None:
                failed += 1
                continue
            
            self._save_result(result, output_dir)
            results.append(result)
        
        stats = {
            "total": len(pair_files),
            "processed": len(results),
            "failed": failed
        }
        
        return results, stats
    
    def process_all_pairs(self, 
                          method: str = "baseline",
                          limit: Optional[int] = None) -> Dict[str, any]:
        """
        Process all temporal pairs for all year combinations.
        
        Args:
            method: Detection method
            limit: Optional limit per year combination
            
        Returns:
            Summary dictionary
        """
        print("=" * 60)
        print("PHASE 11: MULTI-TEMPORAL CHANGE DETECTION")
        print("=" * 60)
        print(f"Pairs directory: {self.pairs_dir}")
        print(f"Output directory: {self.output_dir}")
        print(f"Method: {method}")
        print()
        
        all_results = []
        all_stats = {}
        
        # Process each year combination
        for year_comb in ["2022_2023", "2023_2024", "2022_2024"]:
            print(f"Processing pairs: {year_comb}")
            results, stats = self.process_pair_directory(year_comb, limit, method)
            
            all_results.extend(results)
            all_stats[year_comb] = stats
            print(f"  Processed: {stats['processed']}")
            print(f"  Failed: {stats['failed']}")
            print()
        
        # Save summary
        summary = {
            "total_pairs_processed": len(all_results),
            "pairs_by_year_combination": {
                "2022_2023": all_stats["2022_2023"]["processed"],
                "2023_2024": all_stats["2023_2024"]["processed"],
                "2022_2024": all_stats["2022_2024"]["processed"]
            },
            "statistics": all_stats,
            "method": method
        }
        
        summary_file = self.output_dir / "change_detection_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("=" * 60)
        print("CHANGE DETECTION SUMMARY")
        print("=" * 60)
        print(f"Total pairs processed: {len(all_results)}")
        print(f"  2022 to 2023: {all_stats['2022_2023']['processed']}")
        print(f"  2023 to 2024: {all_stats['2023_2024']['processed']}")
        print(f"  2022 to 2024: {all_stats['2022_2024']['processed']}")
        print(f"Summary saved to: {summary_file}")
        print("=" * 60)
        
        return summary
