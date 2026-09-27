"""
Quality processing utilities for Sentinel-2 imagery
Extends existing Phase 2/3 functionality with advanced quality analysis
"""

import rasterio
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .image_processor import ImageProcessor


class QualityProcessor:
    """Advanced quality processing for Sentinel-2 imagery"""
    
    def __init__(self, image_processor: ImageProcessor):
        """
        Initialize quality processor
        
        Args:
            image_processor: Existing ImageProcessor instance for reuse
        """
        self.image_processor = image_processor
    
    def calculate_quality_statistics(self, scl_path: Path, 
                                     scl_classes: Dict[int, str],
                                     class_groups: Dict[str, List[int]]) -> Dict:
        """
        Calculate quality statistics from SCL mask
        
        Args:
            scl_path: Path to SCL GeoTIFF
            scl_classes: Dictionary mapping SCL values to class names
            class_groups: Dictionary grouping SCL classes for statistics
            
        Returns:
            Dictionary with quality statistics
        """
        with rasterio.open(scl_path) as src:
            scl_data = src.read(1)
            total_pixels = scl_data.size
            
            # Count pixels per class
            class_counts = {}
            for class_value, class_name in scl_classes.items():
                count = np.sum(scl_data == class_value)
                class_counts[class_name] = {
                    "count": int(count),
                    "percentage": float(count / total_pixels * 100) if total_pixels > 0 else 0.0
                }
            
            # Calculate group statistics
            group_stats = {}
            for group_name, class_values in class_groups.items():
                group_count = 0
                for class_value in class_values:
                    group_count += np.sum(scl_data == class_value)
                
                group_stats[group_name] = {
                    "count": int(group_count),
                    "percentage": float(group_count / total_pixels * 100) if total_pixels > 0 else 0.0
                }
            
            # Calculate overall valid/invalid statistics
            valid_classes = [2, 4, 5, 6]  # Dark features, vegetation, not vegetated, water
            invalid_classes = [0, 1, 3, 7, 8, 9, 10, 11]  # No data, saturated, cloud shadow, unclassified, cloud, cirrus, snow, overlapping
            
            valid_count = sum(np.sum(scl_data == cls) for cls in valid_classes)
            invalid_count = sum(np.sum(scl_data == cls) for cls in invalid_classes)
            
            return {
                "total_pixels": int(total_pixels),
                "valid_pixels": int(valid_count),
                "invalid_pixels": int(invalid_count),
                "valid_percentage": float(valid_count / total_pixels * 100) if total_pixels > 0 else 0.0,
                "invalid_percentage": float(invalid_count / total_pixels * 100) if total_pixels > 0 else 0.0,
                "class_breakdown": class_counts,
                "group_statistics": group_stats
            }
    
    def apply_cloud_shadow_buffer(self, scl_path: Path, 
                                 output_path: Path,
                                 buffer_size: int = 3,
                                 cloud_shadow_classes: List[int] = [3, 8, 9, 10],
                                 overwrite: bool = False) -> Dict:
        """
        Apply morphological dilation around cloud/shadow pixels
        
        Args:
            scl_path: Path to SCL mask
            output_path: Path to output buffered mask
            buffer_size: Buffer radius in pixels
            cloud_shadow_classes: SCL classes to buffer around
            overwrite: Whether to overwrite existing file
            
        Returns:
            Dictionary with output geospatial metadata
        """
        if buffer_size == 0:
            print("Cloud shadow buffering disabled (buffer_size = 0)")
            return self.image_processor._get_geotiff_info(scl_path)
        
        if output_path.exists() and not overwrite:
            print(f"Buffered mask already exists, skipping: {output_path}")
            return self.image_processor._get_geotiff_info(output_path)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read SCL
        with rasterio.open(scl_path) as src:
            scl_data = src.read(1)
            profile = src.profile
            profile.update(driver='GTiff')
        
        # Create mask of cloud/shadow pixels
        cloud_shadow_mask = np.isin(scl_data, cloud_shadow_classes).astype(np.uint8)
        
        # Apply morphological dilation using scipy
        from scipy.ndimage import binary_dilation
        struct_element = np.ones((buffer_size * 2 + 1, buffer_size * 2 + 1), dtype=np.uint8)
        buffered_mask = binary_dilation(cloud_shadow_mask, structure=struct_element).astype(np.uint8)
        
        # Update SCL: mark buffered areas as invalid (use class 3 = cloud shadow)
        scl_buffered = scl_data.copy()
        scl_buffered[buffered_mask == 1] = 3
        
        # Write buffered SCL
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(scl_buffered, 1)
        
        print(f"Applied cloud shadow buffer (size={buffer_size}px)")
        return self.image_processor._get_geotiff_info(output_path)
    
    def normalize_reflectance(self, band_path: Path, 
                            output_path: Path,
                            scale_factor: float = 0.0001,
                            offset: float = 0.0,
                            overwrite: bool = False) -> Dict:
        """
        Apply Sentinel-2 L2A reflectance normalization
        
        Args:
            band_path: Path to input band GeoTIFF
            output_path: Path to output normalized band
            scale_factor: Scaling factor (typically 0.0001 for Sentinel-2 L2A)
            offset: Offset value (typically 0.0 for Sentinel-2 L2A)
            overwrite: Whether to overwrite existing file
            
        Returns:
            Dictionary with output geospatial metadata
        """
        if output_path.exists() and not overwrite:
            print(f"Normalized band already exists, skipping: {output_path}")
            return self.image_processor._get_geotiff_info(output_path)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read input band
        with rasterio.open(band_path) as src:
            data = src.read()
            profile = src.profile
            
            # Apply normalization: reflectance = (DN * scale) + offset
            normalized_data = (data.astype(np.float32) * scale_factor) + offset
            
            # Update profile for float data
            profile.update(dtype=rasterio.float32)
        
        # Write normalized band
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(normalized_data)
        
        print(f"Applied reflectance normalization (scale={scale_factor}, offset={offset})")
        return self.image_processor._get_geotiff_info(output_path)
    
    def apply_quality_mask_to_band(self, band_path: Path,
                                  valid_mask_path: Path,
                                  output_path: Path,
                                  nodata_value: float = -9999,
                                  overwrite: bool = False) -> Dict:
        """
        Apply valid mask to a band, setting invalid pixels to nodata
        
        Args:
            band_path: Path to input band GeoTIFF
            valid_mask_path: Path to valid mask (1=valid, 0=invalid)
            output_path: Path to output masked band
            nodata_value: Value to use for invalid pixels
            overwrite: Whether to overwrite existing file
            
        Returns:
            Dictionary with output geospatial metadata
        """
        if output_path.exists() and not overwrite:
            print(f"Masked band already exists, skipping: {output_path}")
            return self.image_processor._get_geotiff_info(output_path)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read band and mask
        with rasterio.open(band_path) as src:
            band_data = src.read()
            profile = src.profile
        
        with rasterio.open(valid_mask_path) as mask_src:
            valid_mask = mask_src.read(1)
        
        # Resample mask if needed
        if valid_mask.shape != band_data.shape[1:]:
            from scipy.ndimage import zoom
            factors = (band_data.shape[1] / valid_mask.shape[0], band_data.shape[2] / valid_mask.shape[1])
            valid_mask = zoom(valid_mask, factors, order=0)  # Nearest neighbor
        
        # Apply mask (set invalid pixels to nodata)
        masked_data = band_data.copy()
        for i in range(band_data.shape[0]):
            masked_data[i] = np.where(valid_mask == 0, nodata_value, band_data[i])
        
        # Update profile with nodata value
        profile.update(nodata=nodata_value)
        
        # Write masked band
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(masked_data)
        
        print(f"Applied quality mask to band")
        return self.image_processor._get_geotiff_info(output_path)
    
    def verify_spatial_alignment(self, scene_paths: List[Path]) -> Dict[str, Dict]:
        """
        Verify spatial alignment across multiple scenes
        
        Args:
            scene_paths: List of paths to scene metadata files or band files
            
        Returns:
            Dictionary with alignment verification results
        """
        alignment_results = {}
        
        # Read geospatial info from each scene
        scene_geo_info = {}
        for i, scene_path in enumerate(scene_paths):
            try:
                geo_info = self.image_processor._get_geotiff_info(scene_path)
                scene_geo_info[f"scene_{i}"] = geo_info
            except Exception as e:
                print(f"Error reading geospatial info from {scene_path}: {e}")
                scene_geo_info[f"scene_{i}"] = None
        
        if not scene_geo_info:
            return {"error": "No valid geospatial information found"}
        
        # Use first scene as reference
        reference_scene = next(iter(scene_geo_info.values()))
        if reference_scene is None:
            return {"error": "Reference scene has no geospatial information"}
        
        reference_crs = reference_scene.get("crs")
        reference_resolution = reference_scene.get("resolution")
        reference_bounds = reference_scene.get("bounds")
        reference_dimensions = {"width": reference_scene.get("width"), "height": reference_scene.get("height")}
        
        # Compare each scene to reference
        alignment_results["reference"] = {
            "crs": reference_crs,
            "resolution": reference_resolution,
            "bounds": reference_bounds,
            "dimensions": reference_dimensions
        }
        
        alignment_results["comparisons"] = {}
        all_aligned = True
        
        for scene_name, geo_info in scene_geo_info.items():
            if geo_info is None:
                alignment_results["comparisons"][scene_name] = {"status": "error", "message": "No geospatial info"}
                all_aligned = False
                continue
            
            # Check CRS
            crs_match = geo_info.get("crs") == reference_crs
            
            # Check resolution (allow small tolerance)
            res = geo_info.get("resolution")
            res_match = (abs(res[0] - reference_resolution[0]) < 0.1 and 
                        abs(res[1] - reference_resolution[1]) < 0.1)
            
            # Check dimensions
            dims_match = (geo_info.get("width") == reference_dimensions["width"] and
                         geo_info.get("height") == reference_dimensions["height"])
            
            # Check bounds (allow small tolerance for registration differences)
            bounds = geo_info.get("bounds")
            bounds_match = (abs(bounds.left - reference_bounds.left) < 10 and
                          abs(bounds.right - reference_bounds.right) < 10 and
                          abs(bounds.top - reference_bounds.top) < 10 and
                          abs(bounds.bottom - reference_bounds.bottom) < 10)
            
            scene_aligned = crs_match and res_match and dims_match and bounds_match
            all_aligned = all_aligned and scene_aligned
            
            alignment_results["comparisons"][scene_name] = {
                "status": "aligned" if scene_aligned else "misaligned",
                "crs_match": crs_match,
                "resolution_match": res_match,
                "dimensions_match": dims_match,
                "bounds_match": bounds_match,
                "crs": geo_info.get("crs"),
                "resolution": res,
                "dimensions": {"width": geo_info.get("width"), "height": geo_info.get("height")},
                "bounds": bounds
            }
        
        alignment_results["overall_alignment"] = "aligned" if all_aligned else "misaligned"
        
        return alignment_results