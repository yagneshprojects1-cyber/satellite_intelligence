"""
Utilities for extracting and managing metadata from Sentinel-2 scenes
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from .safe_parser import SAFEParser


class MetadataExtractor:
    """Extractor for Sentinel-2 scene metadata"""
    
    def __init__(self, safe_parser: SAFEParser):
        """
        Initialize metadata extractor
        
        Args:
            safe_parser: Initialized SAFEParser instance
        """
        self.parser = safe_parser
        self.filename_info = safe_parser.parse_filename()
    
    def extract_metadata(self,
                        band_info: Dict[str, Dict[str, Dict]],
                        quality_info: Dict[str, Dict],
                        geo_info: Dict[str, Dict],
                        quality_stats: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Extract complete metadata for a scene

        Args:
            band_info: Information about processed bands
            quality_info: Information about quality masks
            geo_info: Geospatial information for each band
            quality_stats: Optional quality statistics from QualityProcessor

        Returns:
            Complete metadata dictionary
        """
        # Base information from filename
        metadata = {
            "scene_id": self.filename_info["scene_id"],
            "satellite": self.filename_info["satellite"],
            "mission_id": self.filename_info["mission_id"],
            "product_level": self.filename_info["product_level"],
            "acquisition_date": self.filename_info["acquisition_date"],
            "acquisition_datetime": self.filename_info["acquisition_datetime"],
            "processing_baseline": self.filename_info["processing_baseline"],
            "relative_orbit": self.filename_info["relative_orbit"],
            "tile_id": self.filename_info["tile_id"],
            "year": self.filename_info["year"],
            "source": str(self.parser.safe_path),
            "granule_path": str(self.parser.find_granule_dir()),
            "processing_timestamp": datetime.now().isoformat()
        }

        # Band information
        metadata["bands"] = self._extract_band_info(band_info, geo_info)

        # Quality information
        metadata["quality"] = self._extract_quality_info(quality_info, geo_info)

        # Add quality statistics if provided
        if quality_stats:
            metadata["quality"]["statistics"] = quality_stats

        # RGB preview information
        metadata["previews"] = self._extract_preview_info(geo_info)

        # Geospatial summary (use first band as reference)
        if geo_info:
            first_band_geo = next(iter(geo_info.values()))
            if first_band_geo:
                metadata["geospatial"] = {
                    "crs": first_band_geo.get("crs"),
                    "resolution_summary": self._summarize_resolutions(band_info),
                    "bounds": self._format_bounds(first_band_geo.get("bounds")),
                    "tile_dimensions": {
                        "width": first_band_geo.get("width"),
                        "height": first_band_geo.get("height")
                    }
                }

        return metadata
    
    def _extract_band_info(self,
                          band_info: Dict[str, Dict[str, Dict]],
                          geo_info: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Extract band-specific information

        Args:
            band_info: Band processing information
            geo_info: Geospatial information

        Returns:
            Band metadata dictionary
        """
        bands_metadata = {}

        for resolution, bands in band_info.items():
            for band_name, band_data in bands.items():
                geo_key = f"{band_name}_{resolution}"

                # Convert Path to string for JSON serialization
                source = band_data.get("source", "unknown")
                if isinstance(source, Path):
                    source = str(source)

                output = band_data.get("output", "unknown")
                if isinstance(output, Path):
                    output = str(output)

                bands_metadata[band_name] = {
                    "resolution": resolution,
                    "source_file": source,
                    "processed_file": output,
                    "status": band_data.get("status", "unknown")
                }

                # Add geospatial info if available
                if geo_key in geo_info and geo_info[geo_key]:
                    bands_metadata[band_name]["geospatial"] = {
                        "crs": geo_info[geo_key].get("crs"),
                        "resolution": geo_info[geo_key].get("resolution"),
                        "width": geo_info[geo_key].get("width"),
                        "height": geo_info[geo_key].get("height")
                    }

        return bands_metadata
    
    def _extract_quality_info(self,
                             quality_info: Dict[str, Dict],
                             geo_info: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Extract quality mask information

        Args:
            quality_info: Quality mask processing information
            geo_info: Geospatial information

        Returns:
            Quality metadata dictionary
        """
        quality_metadata = {}

        for quality_type, quality_data in quality_info.items():
            geo_key = f"{quality_type}_quality"

            # Convert Path to string for JSON serialization
            source = quality_data.get("source", "unknown")
            if isinstance(source, Path):
                source = str(source)

            output = quality_data.get("output", "unknown")
            if isinstance(output, Path):
                output = str(output)

            quality_metadata[quality_type] = {
                "source_file": source,
                "processed_file": output,
                "status": quality_data.get("status", "unknown")
            }

            # Add geospatial info if available
            if geo_key in geo_info and geo_info[geo_key]:
                quality_metadata[quality_type]["geospatial"] = {
                    "crs": geo_info[geo_key].get("crs"),
                    "resolution": geo_info[geo_key].get("resolution"),
                    "width": geo_info[geo_key].get("width"),
                    "height": geo_info[geo_key].get("height")
                }

        return quality_metadata
    
    def _extract_preview_info(self, geo_info: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Extract preview image information
        
        Args:
            geo_info: Geospatial information
            
        Returns:
            Preview metadata dictionary
        """
        preview_metadata = {}
        
        if "rgb_preview" in geo_info and geo_info["rgb_preview"]:
            preview_metadata["rgb"] = {
                "file": "rgb.tif",
                "status": "created",
                "geospatial": {
                    "crs": geo_info["rgb_preview"].get("crs"),
                    "resolution": geo_info["rgb_preview"].get("resolution"),
                    "width": geo_info["rgb_preview"].get("width"),
                    "height": geo_info["rgb_preview"].get("height")
                }
            }
        else:
            preview_metadata["rgb"] = {
                "file": "rgb.tif",
                "status": "not_created"
            }
        
        return preview_metadata
    
    def _summarize_resolutions(self, band_info: Dict[str, Dict[str, Dict]]) -> Dict[str, int]:
        """
        Summarize available resolutions

        Args:
            band_info: Band processing information

        Returns:
            Dictionary mapping resolution to band count
        """
        resolution_summary = {}

        for resolution, bands in band_info.items():
            resolution_summary[resolution] = len(bands)

        return resolution_summary
    
    def _format_bounds(self, bounds) -> Dict[str, float]:
        """
        Format bounding box information
        
        Args:
            bounds: Rasterio bounds object
            
        Returns:
            Formatted bounds dictionary
        """
        if bounds is None:
            return {}
        
        return {
            "left": float(bounds.left),
            "bottom": float(bounds.bottom),
            "right": float(bounds.right),
            "top": float(bounds.top)
        }
    
    def save_metadata(self, metadata: Dict[str, Any], output_path: Path):
        """
        Save metadata to JSON file
        
        Args:
            metadata: Metadata dictionary
            output_path: Path to output JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        print(f"Metadata saved to: {output_path}")


def load_metadata(metadata_path: Path) -> Dict[str, Any]:
    """
    Load metadata from JSON file
    
    Args:
        metadata_path: Path to metadata JSON file
        
    Returns:
        Metadata dictionary
    """
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    
    with open(metadata_path, 'r') as f:
        return json.load(f)