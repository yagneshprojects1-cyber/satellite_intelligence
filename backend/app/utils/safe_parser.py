"""
Utilities for parsing Sentinel-2 SAFE file structure and metadata
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class SAFEParseError(Exception):
    """Custom exception for SAFE parsing errors"""
    pass


class SAFEParser:
    """Parser for Sentinel-2 SAFE files"""
    
    def __init__(self, safe_path: Path):
        """
        Initialize SAFE parser
        
        Args:
            safe_path: Path to the .SAFE directory
        """
        self.safe_path = Path(safe_path)
        if not self.safe_path.exists():
            raise SAFEParseError(f"SAFE directory not found: {self.safe_path}")
        if not self.safe_path.is_dir():
            raise SAFEParseError(f"Path is not a directory: {self.safe_path}")
        if not self.safe_path.name.endswith(".SAFE"):
            raise SAFEParseError(f"Directory does not have .SAFE extension: {self.safe_path}")
    
    def parse_filename(self) -> Dict[str, str]:
        """
        Parse Sentinel-2 filename to extract metadata
        
        Returns:
            Dictionary with parsed metadata fields
        """
        filename = self.safe_path.name.replace(".SAFE", "")
        
        # Standard Sentinel-2 naming convention:
        # MMM_MSIXXX_YYYYMMDDTHHMMSS_NPPPP_RRRR_TTTTTTTT_YYYYMMDDTHHMMSS.SAFE
        pattern = r"([A-Z0-9]+)_MSI([A-Z0-9]+)_(\d{8}T\d{6})_([A-Z0-9]+)_([A-Z0-9]+)_([A-Z0-9]+)_(\d{8}T\d{6})"
        
        match = re.match(pattern, filename)
        if not match:
            raise SAFEParseError(f"Could not parse SAFE filename: {filename}")
        
        satellite, product_level, start_time, baseline, relative_orbit, tile_id, end_time = match.groups()
        
        # Parse date
        acquisition_date = datetime.strptime(start_time.split("T")[0], "%Y%m%d")
        
        return {
            "satellite": "Sentinel-2A" if satellite.startswith("S2A") else "Sentinel-2B",
            "mission_id": satellite,
            "product_level": f"L{product_level}",
            "acquisition_date": acquisition_date.strftime("%Y-%m-%d"),
            "acquisition_datetime": start_time,
            "processing_baseline": baseline,
            "relative_orbit": relative_orbit,
            "tile_id": tile_id,
            "scene_id": filename,
            "year": acquisition_date.year
        }
    
    def find_granule_dir(self) -> Path:
        """
        Automatically find the GRANULE directory inside SAFE
        
        Returns:
            Path to the GRANULE directory
            
        Raises:
            SAFEParseError if GRANULE directory not found
        """
        granule_dir = self.safe_path / "GRANULE"
        if not granule_dir.exists():
            raise SAFEParseError(f"GRANULE directory not found in {self.safe_path}")
        
        # Find the actual granule folder (usually L2A_...)
        granule_folders = [f for f in granule_dir.iterdir() if f.is_dir() and f.name.startswith("L2A_")]
        
        if not granule_folders:
            raise SAFEParseError(f"No L2A granule folder found in {granule_dir}")
        
        if len(granule_folders) > 1:
            print(f"Warning: Multiple granule folders found, using first: {granule_folders[0].name}")
        
        return granule_folders[0]
    
    def find_img_data_dirs(self, granule_path: Path) -> Dict[str, Path]:
        """
        Find IMG_DATA directories for different resolutions

        Args:
            granule_path: Path to the granule directory

        Returns:
            Dictionary mapping resolution to IMG_DATA path (keys: "10m", "20m", "60m")
        """
        img_data_base = granule_path / "IMG_DATA"
        if not img_data_base.exists():
            raise SAFEParseError(f"IMG_DATA directory not found in {granule_path}")

        resolutions = {}
        for res in ["R10m", "R20m", "R60m"]:
            res_dir = img_data_base / res
            if res_dir.exists():
                resolutions[res] = res_dir  # "R10m" -> "R10m"

        if not resolutions:
            raise SAFEParseError(f"No resolution directories found in {img_data_base}")

        return resolutions
    
    def find_band_files(self, img_data_dir: Path, tile_id: str) -> Dict[str, Path]:
        """
        Find band files in IMG_DATA directory
        
        Args:
            img_data_dir: Path to IMG_DATA directory (e.g., R10m)
            tile_id: Tile identifier from filename
            
        Returns:
            Dictionary mapping band name to file path
        """
        band_files = {}
        
        # Try multiple patterns to handle different naming conventions
        patterns = [
            # Standard pattern: {TILE_ID}_{DATETIME}_{BAND}_{RESOLUTION}.jp2
            re.compile(rf"{tile_id}_\d{{8}}T\d{{6}}_([A-Z0-9]+)_\d+m\.jp2"),
            # More flexible pattern: {TILE_ID}_{DATETIME}_{BAND}.jp2
            re.compile(rf"{tile_id}_\d{{8}}T\d{{6}}_([A-Z0-9]+)\.jp2"),
            # Even more flexible: {TILE_ID}_.*_{BAND}_.*.jp2
            re.compile(rf"{tile_id}_.*_([A-Z0-9]+)_.*\.jp2")
        ]
        
        for file_path in img_data_dir.glob("*.jp2"):
            for pattern in patterns:
                match = pattern.match(file_path.name)
                if match:
                    band_name = match.group(1)
                    band_files[band_name] = file_path
                    break
        
        return band_files
    
    def get_quality_masks(self, granule_path: Path) -> Dict[str, Path]:
        """
        Find quality mask files (SCL, cloud masks, etc.)

        Args:
            granule_path: Path to the granule directory

        Returns:
            Dictionary mapping quality mask type to file path
        """
        quality_masks = {}

        # First look in QI_DATA directory
        quality_dir = granule_path / "QI_DATA"
        if quality_dir.exists():
            # Look for cloud probability masks
            for cloud_file in quality_dir.glob("*CLDPRB*.jp2"):
                resolution = "R20m" if "20m" in cloud_file.name else "R60m"
                quality_masks[f"CLDPRB_{resolution}"] = cloud_file

            # Look for snow probability masks
            for snow_file in quality_dir.glob("*SNWPRB*.jp2"):
                resolution = "R20m" if "20m" in snow_file.name else "R60m"
                quality_masks[f"SNWPRB_{resolution}"] = snow_file

        # Look for SCL in IMG_DATA directories (it's typically at 20m and 60m)
        img_data_base = granule_path / "IMG_DATA"
        if img_data_base.exists():
            for res_dir in ["R20m", "R60m"]:
                res_path = img_data_base / res_dir
                if res_path.exists():
                    for scl_file in res_path.glob("*SCL*.jp2"):
                        quality_masks[f"SCL_{res_dir}"] = scl_file  # "SCL_R20m"

        return quality_masks
    
    def parse_metadata_xml(self) -> Dict:
        """
        Parse Sentinel-2 metadata XML file
        
        Returns:
            Dictionary with metadata information
        """
        # Try to find MTD_MSIL2A.xml in the SAFE root
        metadata_file = self.safe_path / "MTD_MSIL2A.xml"
        
        if not metadata_file.exists():
            # Try alternative location
            metadata_file = self.safe_path / "MTD_MSIL1C.xml"
        
        if not metadata_file.exists():
            print(f"Warning: Metadata XML not found, using filename parsing only")
            return {}
        
        try:
            tree = ET.parse(metadata_file)
            root = tree.getroot()
            
            # Extract basic metadata (simplified parsing)
            metadata = {}
            
            # You can add more specific XML parsing here based on your needs
            # This is a basic implementation
            
            return metadata
            
        except Exception as e:
            print(f"Warning: Could not parse metadata XML: {e}")
            return {}
    
    def get_safe_info(self) -> Dict:
        """
        Get complete information about the SAFE file

        Returns:
            Dictionary with all SAFE information
        """
        # Parse filename
        filename_info = self.parse_filename()

        # Find directories
        granule_path = self.find_granule_dir()
        img_data_dirs = self.find_img_data_dirs(granule_path)

        # Find band files for each resolution
        all_bands = {}
        for resolution, img_dir in img_data_dirs.items():
            bands = self.find_band_files(img_dir, filename_info["tile_id"])
            all_bands[resolution] = bands

        # Get quality masks
        quality_masks = self.get_quality_masks(granule_path)

        # Parse XML metadata
        xml_metadata = self.parse_metadata_xml()

        return {
            "source_path": str(self.safe_path),
            "granule_path": str(granule_path),
            "filename_info": filename_info,
            "img_data_dirs": {k: str(v) for k, v in img_data_dirs.items()},
            "bands": {k: {b: p for b, p in v.items()} for k, v in all_bands.items()},  # Keep Path objects
            "quality_masks": {k: str(v) for k, v in quality_masks.items()},
            "xml_metadata": xml_metadata
        }


def discover_safe_files(raw_dir: Path) -> List[Path]:
    """
    Discover all SAFE files in a directory
    
    Args:
        raw_dir: Path to directory containing SAFE files
        
    Returns:
        List of paths to SAFE directories
    """
    if not raw_dir.exists():
        raise SAFEParseError(f"Raw data directory not found: {raw_dir}")
    
    safe_files = list(raw_dir.glob("*.SAFE"))
    
    if not safe_files:
        print(f"Warning: No .SAFE files found in {raw_dir}")
    
    return sorted(safe_files)


def group_safe_by_year(safe_files: List[Path]) -> Dict[int, List[Path]]:
    """
    Group SAFE files by acquisition year
    
    Args:
        safe_files: List of SAFE file paths
        
    Returns:
        Dictionary mapping year to list of SAFE files
    """
    grouped = {}
    
    for safe_path in safe_files:
        try:
            parser = SAFEParser(safe_path)
            info = parser.parse_filename()
            year = info["year"]
            
            if year not in grouped:
                grouped[year] = []
            grouped[year].append(safe_path)
            
        except SAFEParseError as e:
            print(f"Warning: Could not parse {safe_path}: {e}")
    
    return grouped