"""
Phase 4 — Quality Processing Module

Provides analysis-ready imagery preparation before AI/ML processing.
Operates on already-ingested GeoTIFFs from Phase 2/3 — does NOT re-read raw JP2 files.

Public API:
    Phase4Pipeline  — main orchestrator for all Phase 4 steps
"""

from .phase4_pipeline import Phase4Pipeline

__all__ = ["Phase4Pipeline"]
