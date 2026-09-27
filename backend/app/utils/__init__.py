"""
Utility modules for Sentinel-2 processing
"""

from .safe_parser import SAFEParser, discover_safe_files, group_safe_by_year, SAFEParseError

# Lazy imports for modules with heavy dependencies
def get_image_processor():
    from .image_processor import ImageProcessor, match_resolution, get_rgb_bands
    return ImageProcessor, match_resolution, get_rgb_bands

def get_metadata_extractor():
    from .metadata_extractor import MetadataExtractor, load_metadata
    return MetadataExtractor, load_metadata

def get_quality_processor():
    from .quality_processor import QualityProcessor
    return QualityProcessor

__all__ = [
    'SAFEParser',
    'discover_safe_files', 
    'group_safe_by_year',
    'SAFEParseError',
    'get_image_processor',
    'get_metadata_extractor',
    'get_quality_processor'
]