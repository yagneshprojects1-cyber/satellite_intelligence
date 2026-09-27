"""
Database repository classes for data access
Phase 14: PostgreSQL/PostGIS Database
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from .models import Scene, Tile, TemporalPair, ChangeResult, EarliestChange, ClusterAssignment, AnalystReview, ProcessingHistory


class SceneRepository:
    """Repository for Scene operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, scene_data: Dict[str, Any]) -> Scene:
        """Create a new scene"""
        scene = Scene(**scene_data)
        self.session.add(scene)
        self.session.commit()
        self.session.refresh(scene)
        return scene
    
    def get_by_scene_id(self, scene_id: str) -> Optional[Scene]:
        """Get scene by scene_id"""
        return self.session.query(Scene).filter(Scene.scene_id == scene_id).first()
    
    def get_or_create(self, scene_data: Dict[str, Any]) -> Scene:
        """Get existing scene or create new one"""
        existing = self.get_by_scene_id(scene_data['scene_id'])
        if existing:
            return existing
        return self.create(scene_data)
    
    def list_all(self) -> List[Scene]:
        """List all scenes"""
        return self.session.query(Scene).all()


class TileRepository:
    """Repository for Tile operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, tile_data: Dict[str, Any]) -> Tile:
        """Create a new tile"""
        tile = Tile(**tile_data)
        self.session.add(tile)
        self.session.commit()
        self.session.refresh(tile)
        return tile
    
    def get_by_tile_id(self, tile_id: str) -> Optional[Tile]:
        """Get tile by tile_id"""
        return self.session.query(Tile).filter(Tile.tile_id == tile_id).first()
    
    def get_or_create(self, tile_data: Dict[str, Any]) -> Tile:
        """Get existing tile or create new one"""
        existing = self.get_by_tile_id(tile_data['tile_id'])
        if existing:
            return existing
        return self.create(tile_data)
    
    def list_by_year(self, year: str) -> List[Tile]:
        """List tiles by year"""
        return self.session.query(Tile).filter(Tile.year == year).all()
    
    def list_all(self) -> List[Tile]:
        """List all tiles"""
        return self.session.query(Tile).all()


class TemporalPairRepository:
    """Repository for TemporalPair operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, pair_data: Dict[str, Any]) -> TemporalPair:
        """Create a new temporal pair"""
        pair = TemporalPair(**pair_data)
        self.session.add(pair)
        self.session.commit()
        self.session.refresh(pair)
        return pair
    
    def get_by_pair_id(self, pair_id: str) -> Optional[TemporalPair]:
        """Get pair by pair_id"""
        return self.session.query(TemporalPair).filter(TemporalPair.pair_id == pair_id).first()
    
    def get_or_create(self, pair_data: Dict[str, Any]) -> TemporalPair:
        """Get existing pair or create new one"""
        existing = self.get_by_pair_id(pair_data['pair_id'])
        if existing:
            return existing
        return self.create(pair_data)
    
    def list_all(self) -> List[TemporalPair]:
        """List all temporal pairs"""
        return self.session.query(TemporalPair).all()


class ChangeResultRepository:
    """Repository for ChangeResult operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, result_data: Dict[str, Any]) -> ChangeResult:
        """Create a new change result"""
        result = ChangeResult(**result_data)
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        return result
    
    def get_by_pair_id(self, pair_id: str) -> List[ChangeResult]:
        """Get change results by pair_id"""
        from sqlalchemy import and_
        
        return self.session.query(ChangeResult).join(
            TemporalPair
        ).filter(
            TemporalPair.pair_id == pair_id
        ).all()
    
    def list_by_method(self, method: str) -> List[ChangeResult]:
        """List change results by method"""
        return self.session.query(ChangeResult).filter(ChangeResult.method == method).all()
    
    def list_all(self) -> List[ChangeResult]:
        """List all change results"""
        return self.session.query(ChangeResult).all()


class ClusterAssignmentRepository:
    """Repository for ClusterAssignment operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, assignment_data: Dict[str, Any]) -> ClusterAssignment:
        """Create a new cluster assignment"""
        assignment = ClusterAssignment(**assignment_data)
        self.session.add(assignment)
        self.session.commit()
        self.session.refresh(assignment)
        return assignment
    
    def get_by_tile_id(self, tile_id: str) -> Optional[ClusterAssignment]:
        """Get cluster assignment by tile_id"""
        return self.session.query(ClusterAssignment).filter(ClusterAssignment.tile_id == tile_id).first()
    
    def get_or_create(self, assignment_data: Dict[str, Any]) -> ClusterAssignment:
        """Get existing assignment or create new one"""
        existing = self.get_by_tile_id(assignment_data['tile_id'])
        if existing:
            return existing
        return self.create(assignment_data)
    
    def list_by_cluster(self, cluster_id: int) -> List[ClusterAssignment]:
        """List assignments by cluster"""
        return self.session.query(ClusterAssignment).filter(ClusterAssignment.cluster_id == cluster_id).all()
    
    def list_all(self) -> List[ClusterAssignment]:
        """List all cluster assignments"""
        return self.session.query(ClusterAssignment).all()


class AnalystReviewRepository:
    """Repository for AnalystReview operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, review_data: Dict[str, Any]) -> AnalystReview:
        """Create a new analyst review"""
        review = AnalystReview(**review_data)
        self.session.add(review)
        self.session.commit()
        self.session.refresh(review)
        return review
    
    def get_by_change_result_id(self, change_result_id: str) -> List[AnalystReview]:
        """Get reviews by change result id"""
        return self.session.query(AnalystReview).filter(AnalystReview.change_result_id == change_result_id).all()
    
    def list_by_decision(self, decision: str) -> List[AnalystReview]:
        """List reviews by decision"""
        return self.session.query(AnalystReview).filter(AnalystReview.decision == decision).all()
    
    def list_all(self) -> List[AnalystReview]:
        """List all analyst reviews"""
        return self.session.query(AnalystReview).all()


class ProcessingHistoryRepository:
    """Repository for ProcessingHistory operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, history_data: Dict[str, Any]) -> ProcessingHistory:
        """Create a new processing history entry"""
        history = ProcessingHistory(**history_data)
        self.session.add(history)
        self.session.commit()
        self.session.refresh(history)
        return history
    
    def get_by_entity(self, entity_type: str, entity_id: str) -> List[ProcessingHistory]:
        """Get processing history for an entity"""
        return self.session.query(ProcessingHistory).filter(
            ProcessingHistory.entity_type == entity_type,
            ProcessingHistory.entity_id == entity_id
        ).order_by(ProcessingHistory.created_at.desc()).all()
    
    def get_by_phase(self, phase: str) -> List[ProcessingHistory]:
        """Get processing history for a phase"""
        return self.session.query(ProcessingHistory).filter(
            ProcessingHistory.phase == phase
        ).order_by(ProcessingHistory.created_at.desc()).all()
    
    def list_all(self) -> List[ProcessingHistory]:
        """List all processing history"""
        return self.session.query(ProcessingHistory).all()
