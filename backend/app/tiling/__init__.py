"""
Phase 5 — Geospatial Tiling Module

Converts quality-controlled Sentinel-2 scenes into smaller AI-searchable
geospatial tiles.
"""

from .phase5_pipeline import Phase5TilingPipeline

__all__ = ["Phase5TilingPipeline"]
