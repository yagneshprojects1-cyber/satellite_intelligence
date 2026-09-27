"""
Database module for satellite intelligence
Phase 14: PostgreSQL/PostGIS Database and Provenance
"""

from .connection import get_db_session, engine
from .models import Base, Scene, Tile, TemporalPair, ChangeResult, EarliestChange, ClusterAssignment, AnalystReview, ProcessingHistory
from .repository import SceneRepository, TileRepository, TemporalPairRepository, ChangeResultRepository, ClusterAssignmentRepository, AnalystReviewRepository, ProcessingHistoryRepository

__all__ = [
    'get_db_session',
    'engine',
    'Base',
    'Scene',
    'Tile',
    'TemporalPair',
    'ChangeResult',
    'EarliestChange',
    'ClusterAssignment',
    'AnalystReview',
    'ProcessingHistory',
    'SceneRepository',
    'TileRepository',
    'TemporalPairRepository',
    'ChangeResultRepository',
    'ClusterAssignmentRepository',
    'AnalystReviewRepository',
    'ProcessingHistoryRepository'
]
