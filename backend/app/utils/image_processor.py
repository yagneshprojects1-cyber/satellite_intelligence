"""
Utilities for processing Sentinel-2 imagery: JP2 to GeoTIFF conversion, 
RGB generation, and quality mask processing
"""

import rasterio
from rasterio.transform import Affine
from rasterio.crs import CRS
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional
import warnings

warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)


class ImageProcessor:
    """Processor for Sentinel-2 imagery conversion and manipulation"""
    
    def __init__(self, quality_check: bool = True):
        """
        Initialize image processor
        
        Args:
            quality_check: Whether to perform quality checks on output
        """
        self.quality_check = quality_check
    
    def jp2_to_geotiff(self, 
                      input_path: Path, 
                      output_path: Path,
                      overwrite: bool = False) -> Dict:
        """
        Convert JP2 file to GeoTIFF while preserving all geospatial information
        
        Args:
            input_path: Path to input JP2 file
            output_path: Path to output GeoTIFF file
            overwrite: Whether to overwrite existing file
            
        Returns:
            Dictionary with geospatial metadata
        """
        if output_path.exists() and not overwrite:
            print(f"Output file already exists, skipping: {output_path}")
            return self._get_geotiff_info(output_path)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read input JP2
        with rasterio.open(input_path) as src:
            # Get source metadata
            profile = src.profile
            profile.update(driver='GTiff')
            
            # Read data
            data = src.read()
            
            # Write output GeoTIFF
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(data)
        
        # Verify output
        if self.quality_check:
            geo_info = self._get_geotiff_info(output_path)
            if geo_info["crs"] is None:
                print(f"Warning: Output file lacks CRS: {output_path}")
        
        return self._get_geotiff_info(output_path)
    
    def _get_geotiff_info(self, geotiff_path: Path) -> Dict:
        """
        Extract geospatial information from GeoTIFF
        
        Args:
            geotiff_path: Path to GeoTIFF file
            
        Returns:
            Dictionary with geospatial metadata
        """
        with rasterio.open(geotiff_path) as src:
            return {
                "crs": str(src.crs) if src.crs else None,
                "transform": src.transform,
                "resolution": (src.res[0], src.res[1]),
                "width": src.width,
                "height": src.height,
                "bounds": src.bounds,
                "nodata": src.nodata,
                "count": src.count,
                "dtype": str(src.dtypes[0])
            }
    
    def create_rgb_composite(self,
                            red_band_path: Path,
                            green_band_path: Path, 
                            blue_band_path: Path,
                            output_path: Path,
                            overwrite: bool = False) -> Dict:
        """
        Create RGB composite from individual bands
        
        Args:
            red_band_path: Path to red band (B04)
            green_band_path: Path to green band (B03)
            blue_band_path: Path to blue band (B02)
            output_path: Path to output RGB GeoTIFF
            overwrite: Whether to overwrite existing file
            
        Returns:
            Dictionary with output geospatial metadata
        """
        if output_path.exists() and not overwrite:
            print(f"RGB composite already exists, skipping: {output_path}")
            return self._get_geotiff_info(output_path)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read reference band for geospatial info
        with rasterio.open(red_band_path) as red_src:
            profile = red_src.profile
            profile.update(count=3, driver='GTiff')
            
            # Read all bands
            red = red_src.read(1)
        
        with rasterio.open(green_band_path) as green_src:
            green = green_src.read(1)
        
        with rasterio.open(blue_band_path) as blue_src:
            blue = blue_src.read(1)
        
        # Handle different shapes (resample if needed)
        target_shape = red.shape
        if green.shape != target_shape:
            green = self._resample_array(green, target_shape)
        if blue.shape != target_shape:
            blue = self._resample_array(blue, target_shape)
        
        # Stack bands
        rgb = np.stack([red, green, blue])
        
        # Write RGB composite
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(rgb)
        
        return self._get_geotiff_info(output_path)
    
    def _resample_array(self, array: np.ndarray, target_shape: Tuple[int, int]) -> np.ndarray:
        """
        Simple resampling using nearest neighbor (for quality masks)
        
        Args:
            array: Input array
            target_shape: Target (height, width)
            
        Returns:
            Resampled array
        """
        from scipy.ndimage import zoom
        
        factors = (target_shape[0] / array.shape[0], target_shape[1] / array.shape[1])
        return zoom(array, factors, order=0)  # Nearest neighbor
    
    def create_valid_mask(self,
                         scl_path: Path,
                         output_path: Path,
                         valid_classes: list,
                         overwrite: bool = False) -> Dict:
        """
        Create valid/invalid mask from SCL (Scene Classification Layer)
        
        Args:
            scl_path: Path to SCL quality mask
            output_path: Path to output valid mask GeoTIFF
            valid_classes: List of valid SCL class values
            overwrite: Whether to overwrite existing file
            
        Returns:
            Dictionary with output geospatial metadata
        """
        if output_path.exists() and not overwrite:
            print(f"Valid mask already exists, skipping: {output_path}")
            return self._get_geotiff_info(output_path)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read SCL
        with rasterio.open(scl_path) as src:
            scl_data = src.read(1)
            profile = src.profile
            profile.update(count=1, driver='GTiff', dtype=rasterio.uint8)
        
        # Create valid mask (1 = valid, 0 = invalid)
        valid_mask = np.isin(scl_data, valid_classes).astype(np.uint8)
        
        # Write valid mask
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(valid_mask, 1)
        
        return self._get_geotiff_info(output_path)
    
    def process_band_collection(self,
                               band_files: Dict[str, Path],
                               output_dir: Path,
                               overwrite: bool = False) -> Dict[str, Dict]:
        """
        Process a collection of bands from JP2 to GeoTIFF

        Args:
            band_files: Dictionary mapping band names to input paths
            output_dir: Directory for output GeoTIFFs
            overwrite: Whether to overwrite existing files

        Returns:
            Dictionary mapping band names to geospatial metadata
        """
        results = {}

        for band_name, input_path in band_files.items():
            # Convert to Path if it's a string
            if isinstance(input_path, str):
                input_path = Path(input_path)

            output_path = output_dir / f"{band_name}.tif"

            try:
                geo_info = self.jp2_to_geotiff(input_path, output_path, overwrite)
                results[band_name] = geo_info
                print(f"  Processed {band_name}: {input_path.name} -> {output_path.name}")

            except Exception as e:
                print(f"  Error processing {band_name}: {e}")
                results[band_name] = None

        return results


def match_resolution(target_resolution: str, 
                     available_resolutions: Dict[str, Dict[str, Path]]) -> Dict[str, Path]:
    """
    Get bands for a specific resolution
    
    Args:
        target_resolution: Target resolution (e.g., "10m", "20m", "60m")
        available_resolutions: Available bands by resolution
        
    Returns:
        Dictionary of band names to paths for target resolution
    """
    if target_resolution not in available_resolutions:
        print(f"Warning: Resolution {target_resolution} not available")
        return {}
    
    return available_resolutions[target_resolution]


def get_rgb_bands(band_files: Dict[str, Path], 
                 rgb_mapping: Dict[str, str]) -> Optional[Dict[str, Path]]:
    """
    Get RGB bands from available band files
    
    Args:
        band_files: Dictionary of available band files
        rgb_mapping: RGB channel to band name mapping
        
    Returns:
        Dictionary mapping channel names to band paths, or None if bands missing
    """
    rgb_bands = {}
    
    for channel, band_name in rgb_mapping.items():
        if band_name in band_files:
            rgb_bands[channel] = band_files[band_name]
        else:
            print(f"Warning: RGB band {band_name} not available")
            return None
    
    return rgb_bands