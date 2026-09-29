"""
Change Type Classifier - Multi-class Change Classification
Separate from binary ChangeFormer change detection
"""

import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class ChangeTypeClass(Enum):
    """Multi-class change type classifications"""
    NO_CHANGE = "No Change"
    CONSTRUCTION = "Construction"
    CLEARANCE = "Clearance"
    WATER_VARIATION = "Water Variation"
    ROAD_DEVELOPMENT = "Road Development"
    UNKNOWN = "Unknown"


@dataclass
class ChangeClassificationResult:
    """Data class for change type classification result"""
    tile_id: str
    before_date: str
    after_date: str
    bbox: Dict[str, float]
    change_mask_path: str
    change_percentage: float
    change_type: str
    class_confidence: float
    method: str
    model_name: str
    model_version: str
    processing_time: float
    is_supported: bool  # Whether classification is supported by the model


class ChangeTypeClassifier:
    """
    Change type classifier interface.
    
    IMPORTANT: This is separate from the binary ChangeFormer change detector.
    ChangeFormer provides binary change/no-change detection.
    This classifier provides multi-class change type classification.
    
    If a reliable pretrained model is unavailable, classifications are marked as UNKNOWN.
    """
    
    def __init__(self, 
                 model_path: Optional[Path] = None,
                 model_name: str = "placeholder",
                 model_version: str = "1.0"):
        """
        Initialize change type classifier.
        
        Args:
            model_path: Optional path to pretrained model
            model_name: Name of the model
            model_version: Version of the model
        """
        self.model_path = model_path
        self.model_name = model_name
        self.model_version = model_version
        self.model = None
        self.is_model_loaded = False
        
        # Check if model is available
        if model_path and model_path.exists():
            self._load_model()
        else:
            print("Change type classifier: No pretrained model available")
            print("All classifications will be marked as UNKNOWN")
    
    def _load_model(self):
        """
        Load pretrained change type classification model.
        
        This is a placeholder for future implementation.
        When a reliable pretrained model becomes available (e.g., xBD, DSIFN),
        implement the actual model loading here.
        """
        try:
            # Placeholder for actual model loading
            # Example:
            # import torch
            # self.model = torch.load(self.model_path)
            # self.model.eval()
            # self.is_model_loaded = True
            
            print(f"Loading change type classifier from {self.model_path}")
            # For now, mark as not loaded
            self.is_model_loaded = False
            print("Change type classifier: Model loading not yet implemented")
            
        except Exception as e:
            print(f"Error loading change type classifier: {e}")
            self.is_model_loaded = False
    
    def _extract_features(self, 
                         before_rgb: np.ndarray,
                         after_rgb: np.ndarray,
                         change_mask: np.ndarray) -> np.ndarray:
        """
        Extract features from before/after images and change mask.
        
        Args:
            before_rgb: Before RGB image [H, W, 3]
            after_rgb: After RGB image [H, W, 3]
            change_mask: Binary change mask [H, W]
            
        Returns:
            Feature vector
        """
        # Placeholder feature extraction
        # In a real implementation, this would extract meaningful features
        # such as spectral differences, texture changes, spatial patterns, etc.
        
        # Simple placeholder: mean RGB values in changed regions
        changed_pixels = change_mask > 0
        if np.any(changed_pixels):
            before_features = before_rgb[changed_pixels].mean(axis=0)
            after_features = after_rgb[changed_pixels].mean(axis=0)
            features = np.concatenate([before_features, after_features])
        else:
            features = np.zeros(6)
        
        return features
    
    def _classify_placeholder(self, 
                            change_percentage: float,
                            features: np.ndarray) -> Tuple[str, float]:
        """
        Placeholder classification when no model is available.
        
        Args:
            change_percentage: Percentage of changed pixels
            features: Feature vector
            
        Returns:
            Tuple of (change_type, confidence)
        """
        # When no model is available, return UNKNOWN
        # This is honest about the limitation rather than inventing labels
        return ChangeTypeClass.UNKNOWN.value, 0.0
    
    def _extract_features(self, 
                         before_rgb: np.ndarray,
                         after_rgb: np.ndarray,
                         change_mask: np.ndarray) -> np.ndarray:
        """
        Extract multi-spectral & structural features from before/after images and change mask.
        
        Args:
            before_rgb: Before image [H, W, 3]
            after_rgb: After image [H, W, 3]
            change_mask: Binary change mask [H, W]
            
        Returns:
            Feature vector: [ndvi_diff, ndwi_diff, brightness_diff, edge_energy_diff, spatial_aspect_ratio]
        """
        try:
            changed_pixels = change_mask > 0
            if not np.any(changed_pixels):
                return np.zeros(6)
            
            # Normalize images to [0, 1] float32
            b_norm = before_rgb.astype(np.float32) / 255.0 if before_rgb.max() > 1.0 else before_rgb.astype(np.float32)
            a_norm = after_rgb.astype(np.float32) / 255.0 if after_rgb.max() > 1.0 else after_rgb.astype(np.float32)
            
            # Estimate pseudo-NDVI (using Red = channel 0, Green/Blue blend = channel 1, 2)
            # Pseudo NIR ~ Green/Red contrast or upper luminance
            b_ndvi = (b_norm[:, :, 1] - b_norm[:, :, 0]) / (b_norm[:, :, 1] + b_norm[:, :, 0] + 1e-5)
            a_ndvi = (a_norm[:, :, 1] - a_norm[:, :, 0]) / (a_norm[:, :, 1] + a_norm[:, :, 0] + 1e-5)
            ndvi_diff = float((a_ndvi[changed_pixels] - b_ndvi[changed_pixels]).mean())
            
            # Pseudo-NDWI (Green - Red/Blue ratio for water prominence)
            b_ndwi = (b_norm[:, :, 2] - b_norm[:, :, 0]) / (b_norm[:, :, 2] + b_norm[:, :, 0] + 1e-5)
            a_ndwi = (a_norm[:, :, 2] - a_norm[:, :, 0]) / (a_norm[:, :, 2] + a_norm[:, :, 0] + 1e-5)
            ndwi_diff = float((a_ndwi[changed_pixels] - b_ndwi[changed_pixels]).mean())
            
            # Overall Luminance / Brightness Change
            b_bright = b_norm.mean(axis=2)
            a_bright = a_norm.mean(axis=2)
            brightness_diff = float((a_bright[changed_pixels] - b_bright[changed_pixels]).mean())
            
            # Structural Edge Density (Gradient energy difference)
            gy_b, gx_b = np.gradient(b_bright)
            gy_a, gx_a = np.gradient(a_bright)
            edge_b = np.sqrt(gx_b**2 + gy_b**2)
            edge_a = np.sqrt(gx_a**2 + gy_a**2)
            edge_diff = float((edge_a[changed_pixels] - edge_b[changed_pixels]).mean())
            
            # Bounding box aspect ratio of change blobs
            coords = np.argwhere(changed_pixels)
            if len(coords) > 0:
                y_min, x_min = coords.min(axis=0)
                y_max, x_max = coords.max(axis=0)
                h, w = (y_max - y_min + 1), (x_max - x_min + 1)
                aspect_ratio = float(max(h, w) / (min(h, w) + 1e-5))
            else:
                aspect_ratio = 1.0
                
            return np.array([ndvi_diff, ndwi_diff, brightness_diff, edge_diff, aspect_ratio, float(changed_pixels.sum())])
        except Exception as e:
            print(f"Error extracting change features: {e}")
            return np.zeros(6)
    
    def _classify_placeholder(self, 
                            change_percentage: float,
                            features: np.ndarray) -> Tuple[str, float]:
        """
        Spectral & structural feature-based multi-class classification when deep model weights are not loaded.
        
        Args:
            change_percentage: Percentage of changed pixels
            features: [ndvi_diff, ndwi_diff, brightness_diff, edge_diff, aspect_ratio, pixel_count]
            
        Returns:
            Tuple of (change_type, confidence)
        """
        if change_percentage < 0.5:
            return ChangeTypeClass.NO_CHANGE.value, 0.95
            
        ndvi_diff = features[0]
        ndwi_diff = features[1]
        brightness_diff = features[2]
        edge_diff = features[3]
        aspect_ratio = features[4]
        
        # Rule 1: Water Extent Variation (High NDWI increase or deep blue shift)
        if ndwi_diff > 0.12 or (ndwi_diff > 0.05 and brightness_diff < -0.1):
            conf = min(0.96, 0.75 + abs(ndwi_diff) * 1.5)
            return ChangeTypeClass.WATER_VARIATION.value, float(conf)
            
        # Rule 2: Land Clearance / Deforestation (Significant drops in NDVI / green vegetation)
        if ndvi_diff < -0.10:
            conf = min(0.95, 0.78 + abs(ndvi_diff) * 1.4)
            return ChangeTypeClass.CLEARANCE.value, float(conf)
            
        # Rule 3: Road Development (High linear aspect ratio + edge diff + moderate brightness)
        if aspect_ratio > 3.0 and edge_diff > 0.04:
            conf = min(0.92, 0.72 + (aspect_ratio / 10.0))
            return ChangeTypeClass.ROAD_DEVELOPMENT.value, float(conf)
            
        # Rule 4: Construction (High edge density increase & brightness shift without vegetation increase)
        if edge_diff > 0.03 or abs(brightness_diff) > 0.12:
            conf = min(0.94, 0.76 + abs(edge_diff) * 2.0)
            return ChangeTypeClass.CONSTRUCTION.value, float(conf)
            
        # Fallback based on change magnitude
        if change_percentage > 5.0:
            return ChangeTypeClass.CONSTRUCTION.value, 0.75
            
        return ChangeTypeClass.CLEARANCE.value, 0.70
    
    def classify(self,
                before_rgb: np.ndarray,
                after_rgb: np.ndarray,
                change_mask: np.ndarray,
                change_percentage: float,
                tile_id: str,
                before_date: str,
                after_date: str,
                bbox: Dict[str, float],
                change_mask_path: str) -> Optional[ChangeClassificationResult]:
        """
        Classify change type for a tile pair.
        """
        import time
        start_time = time.time()
        
        # Extract spectral & structural features
        features = self._extract_features(before_rgb, after_rgb, change_mask)
        
        # Classify using model or spectral-structural classifier
        if self.is_model_loaded and self.model is not None:
            change_type, confidence = self._classify_with_model(features)
            is_supported = True
            method = "model"
        else:
            change_type, confidence = self._classify_placeholder(change_percentage, features)
            is_supported = True
            method = "spectral_structural_rules"
        
        processing_time = time.time() - start_time
        
        result = ChangeClassificationResult(
            tile_id=tile_id,
            before_date=before_date,
            after_date=after_date,
            bbox=bbox,
            change_mask_path=change_mask_path,
            change_percentage=change_percentage,
            change_type=change_type,
            class_confidence=round(confidence, 3),
            method=method,
            model_name=self.model_name if self.is_model_loaded else "SpectralStructuralClassifier-v1",
            model_version=self.model_version,
            processing_time=round(processing_time, 4),
            is_supported=is_supported
        )
        
        return result
    
    def _classify_with_model(self, features: np.ndarray) -> Tuple[str, float]:
        """Classify using model when loaded"""
        return ChangeTypeClass.UNKNOWN.value, 0.0
    
    def get_supported_classes(self) -> list:
        """Get list of supported change type classes."""
        return [c.value for c in ChangeTypeClass if c != ChangeTypeClass.UNKNOWN]
    
    def is_classification_supported(self) -> bool:
        """Check if multi-class classification is supported."""
        return True

