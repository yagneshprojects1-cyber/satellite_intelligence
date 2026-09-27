"""
Database models for satellite intelligence
Phase 14: PostgreSQL/PostGIS Database
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


def uuid4():
    return uuid.uuid4()


class Scene(Base):
    """Sentinel-2 source scenes"""
    __tablename__ = 'scenes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scene_id = Column(String(255), unique=True, nullable=False, index=True)
    sensor = Column(String(50), nullable=False)
    satellite = Column(String(50), nullable=False)
    acquisition_date = Column(DateTime, nullable=False, index=True)
    source_path = Column(String(512), nullable=False)
    crs = Column(String(50), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    processing_status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tiles = relationship("Tile", back_populates="scene", cascade="all, delete-orphan")


class Tile(Base):
    """256x256 satellite tiles"""
    __tablename__ = 'tiles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tile_id = Column(String(255), unique=True, nullable=False, index=True)
    scene_id = Column(UUID(as_uuid=True), ForeignKey('scenes.id'), nullable=True)
    year = Column(String(4), nullable=False, index=True)
    acquisition_date = Column(DateTime, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    bbox = Column(Geometry('Polygon', srid=4326), nullable=False)
    crs = Column(String(50), nullable=False)
    resolution = Column(Float, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    valid_percentage = Column(Float, nullable=False)
    source_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scene = relationship("Scene", back_populates="tiles")
    temporal_pairs_before = relationship("TemporalPair", foreign_keys="TemporalPair.before_tile_id", back_populates="before_tile")
    temporal_pairs_after = relationship("TemporalPair", foreign_keys="TemporalPair.after_tile_id", back_populates="after_tile")
    cluster_assignment = relationship("ClusterAssignment", back_populates="tile")


class TemporalPair(Base):
    """Temporal tile pairs for change detection"""
    __tablename__ = 'temporal_pairs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    pair_id = Column(String(255), unique=True, nullable=False, index=True)
    before_tile_id = Column(UUID(as_uuid=True), ForeignKey('tiles.id'), nullable=False)
    after_tile_id = Column(UUID(as_uuid=True), ForeignKey('tiles.id'), nullable=False)
    before_date = Column(DateTime, nullable=False)
    after_date = Column(DateTime, nullable=False)
    bbox = Column(Geometry('Polygon', srid=4326), nullable=False)
    spatial_overlap = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    before_tile = relationship("Tile", foreign_keys=[before_tile_id], back_populates="temporal_pairs_before")
    after_tile = relationship("Tile", foreign_keys=[after_tile_id], back_populates="temporal_pairs_after")
    change_results = relationship("ChangeResult", back_populates="temporal_pair")


class ChangeResult(Base):
    """Change detection results"""
    __tablename__ = 'change_results'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    pair_id = Column(UUID(as_uuid=True), ForeignKey('temporal_pairs.id'), nullable=False)
    method = Column(String(50), nullable=False, index=True)
    change_percentage = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    change_mask_path = Column(String(512), nullable=False)
    result_path = Column(String(512), nullable=False)
    model_name = Column(String(255), nullable=False)
    model_version = Column(String(50), nullable=False)
    processing_time = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    temporal_pair = relationship("TemporalPair", back_populates="change_results")
    analyst_reviews = relationship("AnalystReview", back_populates="change_result")


class EarliestChange(Base):
    """Earliest detected changes"""
    __tablename__ = 'earliest_changes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    location_reference = Column(String(255), nullable=False)  # tile_id or location identifier
    earliest_change_date = Column(DateTime, nullable=False)
    before_date = Column(DateTime, nullable=False)
    after_date = Column(DateTime, nullable=False)
    confidence = Column(Float, nullable=False)
    evidence = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClusterAssignment(Base):
    """HDBSCAN cluster assignments"""
    __tablename__ = 'cluster_assignments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tile_id = Column(UUID(as_uuid=True), ForeignKey('tiles.id'), nullable=False, unique=True)
    cluster_id = Column(Integer, nullable=False, index=True)
    cluster_probability = Column(Float, nullable=False)
    is_noise = Column(Boolean, nullable=False, default=False, index=True)
    embedding_model = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tile = relationship("Tile", back_populates="cluster_assignment")


class AnalystReview(Base):
    """Analyst reviews and decisions"""
    __tablename__ = 'analyst_reviews'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    change_result_id = Column(UUID(as_uuid=True), ForeignKey('change_results.id'), nullable=False)
    decision = Column(SQLEnum('confirmed', 'rejected', name='decision_enum'), nullable=False)
    change_type = Column(SQLEnum('construction', 'clearance', 'water_variation', 'road_development', 'unknown', name='change_type_enum'), nullable=False)
    analyst_comment = Column(String(2000), nullable=True)
    analyst_id = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    change_result = relationship("ChangeResult", back_populates="analyst_reviews")


class ProcessingHistory(Base):
    """Processing provenance and history"""
    __tablename__ = 'processing_history'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_type = Column(String(50), nullable=False, index=True)  # scene, tile, pair, etc.
    entity_id = Column(String(255), nullable=False)
    phase = Column(String(50), nullable=False, index=True)
    operation = Column(String(100), nullable=False)
    model_name = Column(String(255), nullable=True)
    model_version = Column(String(50), nullable=True)
    parameters = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, index=True)  # success, failed, pending
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String(2000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
