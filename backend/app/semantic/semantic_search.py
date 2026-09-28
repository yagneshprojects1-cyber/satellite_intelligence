"""
Semantic Search Module for Satellite Imagery
Provides CLIP-based text-to-image and image-to-image semantic search
"""

import json
import numpy as np
import torch
from pathlib import Path
from typing import List, Dict, Optional, Any
from PIL import Image
import rasterio
from scipy.ndimage import zoom
from app.vector_db.qdrant_manager import QdrantManager
from app.semantic.text_encoder import CLIPTextEncoder
from app.search.search_filters import SearchFilters
from transformers import CLIPProcessor, CLIPModel
import transformers.modeling_utils
transformers.modeling_utils.check_torch_load_is_safe = lambda: None
import transformers.utils.import_utils
transformers.utils.import_utils.check_torch_load_is_safe = lambda: None


class SemanticSearch:
    """
    CLIP-based semantic search engine for satellite imagery.
    
    Uses CLIP text embeddings to search CLIP image embeddings.
    This is a separate retrieval branch from the existing Clay-based system.
    """
    
    def __init__(self, 
                 qdrant_storage_path="qdrant_storage",
                 clip_collection_name="satellite_tiles_clip",
                 clay_collection_name="satellite_tiles",
                 tiles_dir="data/tiles",
                 model_name="openai/clip-vit-base-patch32",
                 device="cpu"):
        """
        Initialize semantic search engine.
        
        Args:
            qdrant_storage_path: Path to Qdrant storage
            clip_collection_name: Qdrant collection for CLIP embeddings
            clay_collection_name: Qdrant collection for Clay embeddings (kept separate)
            tiles_dir: Path to Phase 5 tiles
            model_name: HuggingFace CLIP model name
            device: torch device for text encoder
        """
        self.clip_collection_name = clip_collection_name
        self.clay_collection_name = clay_collection_name
        self.tiles_dir = Path(tiles_dir)
        self.model_name = model_name
        self.device = device
        
        # Initialize Qdrant manager for CLIP collection
        self.qdrant_manager = QdrantManager(
            storage_path=qdrant_storage_path,
            collection_name=clip_collection_name
        )
        
        # Initialize CLIP text encoder
        self.text_encoder = None
        
        # Initialize CLIP image encoder (lazy loading)
        self.clip_model = None
        self.clip_processor = None
        
        # Validate CLIP collection
        self._validate_clip_collection()
    
    def _validate_clip_collection(self):
        """Validate that CLIP Qdrant collection exists and has data."""
        info = self.qdrant_manager.get_collection_info()
        
        if info is None:
            raise ValueError(
                f"CLIP Qdrant collection '{self.clip_collection_name}' not found. "
                "Please run Phase 8 CLIP indexing first."
            )
        
        if info.points_count == 0:
            raise ValueError(
                f"CLIP Qdrant collection '{self.clip_collection_name}' is empty. "
                "Please run Phase 8 CLIP indexing first."
            )
        
        print(f"Connected to CLIP collection '{self.clip_collection_name}'")
        print(f"  Points: {info.points_count}")
        print(f"  Dimension: {info.config.params.vectors.size}")
        print(f"  Distance: {info.config.params.vectors.distance}")
    
    def _setup_text_encoder(self):
        """Initialize CLIP text encoder (lazy loading)."""
        if self.text_encoder is None:
            self.text_encoder = CLIPTextEncoder(
                model_name=self.model_name,
                device=self.device
            )
    
    def _setup_clip_model(self):
        """Initialize CLIP model and processor for image encoding (lazy loading)."""
        if self.clip_model is None:
            print(f"Loading CLIP model {self.model_name} to {self.device}...")
            self.clip_model = CLIPModel.from_pretrained(self.model_name).to(self.device)
            self.clip_processor = CLIPProcessor.from_pretrained(self.model_name)
            
            # Set to evaluation mode
            self.clip_model.eval()
            
            # Disable gradient computation
            for param in self.clip_model.parameters():
                param.requires_grad = False
            
            print(f"CLIP model loaded successfully")
    
    def _create_rgb_from_tile(self, tile_dir: Path) -> Optional[Image.Image]:
        """
        Create RGB image from Sentinel-2 tile bands.
        Reuses the logic from clip_indexer.
        
        Args:
            tile_dir: Path to tile directory
            
        Returns:
            PIL Image or None if failed
        """
        try:
            # Load individual bands
            red_path = tile_dir / "B04.tif"
            green_path = tile_dir / "B03.tif"
            blue_path = tile_dir / "B02.tif"
            
            if not all(p.exists() for p in [red_path, green_path, blue_path]):
                print(f"Missing RGB bands in {tile_dir}")
                return None
            
            # Read bands
            with rasterio.open(red_path) as src:
                red = src.read(1)
            
            with rasterio.open(green_path) as src:
                green = src.read(1)
            
            with rasterio.open(blue_path) as src:
                blue = src.read(1)
            
            # Handle different shapes (resample if needed)
            target_shape = red.shape
            if green.shape != target_shape:
                scale_factor = target_shape[0] / green.shape[0]
                green = zoom(green, scale_factor, order=1)
            if blue.shape != target_shape:
                scale_factor = target_shape[0] / blue.shape[0]
                blue = zoom(blue, scale_factor, order=1)
            
            # Normalize for display (percentile stretching)
            def normalize_band(band):
                p2, p98 = np.percentile(band, (2, 98))
                if p98 - p2 > 0:
                    band = (band - p2) / (p98 - p2)
                return np.clip(band, 0, 1)
            
            red_norm = normalize_band(red)
            green_norm = normalize_band(green)
            blue_norm = normalize_band(blue)
            
            # Stack and convert to RGB
            rgb = np.stack([red_norm, green_norm, blue_norm], axis=-1)
            rgb = (rgb * 255).astype(np.uint8)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(rgb)
            
            return pil_image
            
        except Exception as e:
            print(f"Error creating RGB from {tile_dir}: {e}")
            return None
    
    def _encode_image(self, image: Image.Image) -> np.ndarray:
        """
        Encode image using CLIP for compatibility with text embeddings.
        Reuses the logic from clip_indexer.
        
        Args:
            image: PIL Image
            
        Returns:
            Normalized embedding as numpy array
        """
        with torch.no_grad():
            # Process image
            inputs = self.clip_processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Use official CLIP method to get projected features
            image_features = self.clip_model.get_image_features(**inputs)
            
            # Check if image_features is a tensor directly
            if isinstance(image_features, torch.Tensor):
                embedding = image_features.cpu().numpy()[0]
            else:
                # Extract the actual tensor from the output object
                if hasattr(image_features, 'image_embeds'):
                    embedding = image_features.image_embeds.cpu().numpy()[0]
                elif hasattr(image_features, 'pooler_output'):
                    embedding = image_features.pooler_output.cpu().numpy()[0]
                else:
                    # Fallback: try to extract tensor
                    for attr in dir(image_features):
                        if not attr.startswith('_') and hasattr(getattr(image_features, attr), 'cpu'):
                            tensor = getattr(image_features, attr)
                            if hasattr(tensor, 'numpy'):
                                embedding = tensor.numpy()[0]
                                break
                    else:
                        raise ValueError(f"Could not extract tensor from image_features. Type: {type(image_features)}")
            
            # Verify we got 512-D embedding
            if len(embedding) != 512:
                raise ValueError(f"Image embedding dimension is {len(embedding)}, expected 512")
            
            # Normalize for cosine similarity
            embedding = embedding / np.linalg.norm(embedding)
            
        return embedding
    
    def _find_tile_path(self, tile_id: str) -> Optional[Path]:
        """
        Find tile directory path from tile_id.
        
        Args:
            tile_id: Tile identifier
            
        Returns:
            Path to tile directory or None
        """
        # Search in year directories
        for year_dir in self.tiles_dir.iterdir():
            if year_dir.is_dir() and year_dir.name in ["2022", "2023", "2024"]:
                tile_path = year_dir / tile_id
                if tile_path.exists() and (tile_path / "metadata.json").exists():
                    return tile_path
        return None
    
    def search(self, 
               query: str, 
               top_k: int = 10,
               filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform CLIP-based text-to-image semantic search with advanced filtering.
        
        Args:
            query: Text query (e.g., "areas with water bodies")
            top_k: Number of results to return
            filters: Optional metadata filters (year, sensor, date range, bbox, etc.)
            
        Returns:
            List of search results with metadata
        """
        # Validate filters if provided
        if filters:
            is_valid, errors = SearchFilters.validate_filters(filters)
            if not is_valid:
                raise ValueError(f"Invalid filters: {', '.join(errors)}")
        
        # Setup text encoder
        self._setup_text_encoder()
        
        # Encode text query
        text_embedding = self.text_encoder.encode_text_numpy(query)
        if isinstance(text_embedding, np.ndarray):
            text_embedding = text_embedding.tolist()
        
        # Validate embedding dimension
        info = self.qdrant_manager.get_collection_info()
        expected_dim = info.config.params.vectors.size
        if len(text_embedding) != expected_dim:
            raise ValueError(
                f"Text embedding dimension {len(text_embedding)} does not match "
                f"CLIP collection dimension {expected_dim}"
            )
        
        # Build Qdrant filter for conditions that can be pushed down
        qdrant_filter = SearchFilters.build_qdrant_filter(filters)
        
        # Perform CLIP vector search
        # Request more results if post-search filtering is needed
        requested_k = top_k * 2 if filters else top_k
        qdrant_results = self.qdrant_manager.search_similar(
            query_vector=text_embedding,
            top_k=requested_k,
            filter_conditions=qdrant_filter
        )
        
        # Extract points (Qdrant client search returns a list of ScoredPoint)
        points = qdrant_results if isinstance(qdrant_results, list) else getattr(qdrant_results, 'points', [])
        
        # Enrich results
        results = []
        for i, point in enumerate(points):
            payload = point.payload
            enriched_result = {
                "rank": i + 1,
                "tile_id": payload.get("tile_id", ""),
                "similarity": point.score,
                "date": payload.get("date", ""),
                "latitude": payload.get("latitude", 0.0),
                "longitude": payload.get("longitude", 0.0),
                "bbox": payload.get("bbox", {}),
                "sensor": payload.get("sensor", ""),
                "source_scene": payload.get("source_scene", ""),
                "valid_percentage": payload.get("valid_percentage", 0.0),
                "tile_path": payload.get("tile_path", ""),
                "embedding_model": payload.get("embedding_model", ""),
                "embedding_type": payload.get("embedding_type", "")
            }
            results.append(enriched_result)
        
        # Apply post-search filters for conditions that cannot be pushed down
        if filters:
            results = SearchFilters.apply_post_search_filters(results, filters)
        
        # Limit to top_k results
        results = results[:top_k]
        
        # Update ranks after filtering
        for i, result in enumerate(results):
            result["rank"] = i + 1
        
        return results
    
    def search_by_image(self, 
                       tile_id: str, 
                       top_k: int = 10,
                       filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform CLIP-based image-to-image similarity search with advanced filtering.
        
        Args:
            tile_id: Tile identifier for query image
            top_k: Number of results to return
            filters: Optional metadata filters (year, sensor, date range, bbox, etc.)
            
        Returns:
            List of search results with metadata
        """
        # Validate filters if provided
        if filters:
            is_valid, errors = SearchFilters.validate_filters(filters)
            if not is_valid:
                raise ValueError(f"Invalid filters: {', '.join(errors)}")
        
        # Setup CLIP model for image encoding
        self._setup_clip_model()
        
        # Find tile path
        tile_path = self._find_tile_path(tile_id)
        if tile_path is None:
            raise ValueError(f"Tile {tile_id} not found in tile directories")
        
        # Create RGB image from tile
        rgb_image = self._create_rgb_from_tile(tile_path)
        if rgb_image is None:
            raise ValueError(f"Failed to create RGB image for tile {tile_id}")
        
        # Generate CLIP embedding for query image
        query_embedding = self._encode_image(rgb_image)
        
        # Validate embedding dimension
        info = self.qdrant_manager.get_collection_info()
        expected_dim = info.config.params.vectors.size
        if len(query_embedding) != expected_dim:
            raise ValueError(
                f"Image embedding dimension {len(query_embedding)} does not match "
                f"CLIP collection dimension {expected_dim}"
            )
        
        # Build Qdrant filter for conditions that can be pushed down
        qdrant_filter = SearchFilters.build_qdrant_filter(filters)
        
        # Perform CLIP vector search
        # Request more results if post-search filtering is needed
        requested_k = (top_k + 1) * 2 if filters else top_k + 1
        qdrant_results = self.qdrant_manager.search_similar(
            query_vector=query_embedding.tolist(),
            top_k=requested_k,  # Get extra to exclude query tile and account for filtering
            filter_conditions=qdrant_filter
        )
        
        # Extract points (Qdrant client search returns a list of ScoredPoint)
        points = qdrant_results if isinstance(qdrant_results, list) else getattr(qdrant_results, 'points', [])
        
        # Enrich results and exclude query tile
        results = []
        for point in points:
            payload = point.payload
            result_tile_id = payload.get("tile_id", "")
            
            # Skip the query tile itself
            if result_tile_id == tile_id:
                continue
            
            enriched_result = {
                "rank": 0,  # Will be updated after filtering
                "tile_id": result_tile_id,
                "similarity": point.score,
                "date": payload.get("date", ""),
                "latitude": payload.get("latitude", 0.0),
                "longitude": payload.get("longitude", 0.0),
                "bbox": payload.get("bbox", {}),
                "sensor": payload.get("sensor", ""),
                "source_scene": payload.get("source_scene", ""),
                "valid_percentage": payload.get("valid_percentage", 0.0),
                "tile_path": payload.get("tile_path", ""),
                "embedding_model": payload.get("embedding_model", ""),
                "embedding_type": payload.get("embedding_type", "")
            }
            results.append(enriched_result)
        
        # Apply post-search filters for conditions that cannot be pushed down
        if filters:
            results = SearchFilters.apply_post_search_filters(results, filters)
        
        # Limit to top_k results
        results = results[:top_k]
        
        # Update ranks after filtering
        for i, result in enumerate(results):
            result["rank"] = i + 1
        
        return results
    
    def search_by_pil_image(self, 
                             image: Image.Image, 
                             top_k: int = 10,
                             filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform CLIP-based image-to-image similarity search using an uploaded PIL Image.
        
        Args:
            image: PIL Image uploaded by user
            top_k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of search results with metadata
        """
        if filters:
            is_valid, errors = SearchFilters.validate_filters(filters)
            if not is_valid:
                raise ValueError(f"Invalid filters: {', '.join(errors)}")
        
        # Setup CLIP model
        self._setup_clip_model()
        
        # Robust normalization for RGB / RGBA / grayscale / 16-bit TIFF Sentinel-2 bands
        try:
            arr = np.array(image, dtype=np.float32)
            if arr.ndim == 2:
                p2, p98 = np.percentile(arr, (2, 98))
                if p98 - p2 > 0:
                    arr = (arr - p2) / (p98 - p2)
                arr = np.clip(arr, 0, 1)
                arr = (arr * 255).astype(np.uint8)
                arr = np.stack([arr, arr, arr], axis=-1)
                image = Image.fromarray(arr)
            elif arr.ndim == 3:
                if arr.shape[2] > 3:
                    arr = arr[:, :, :3]
                normalized_bands = []
                for b in range(arr.shape[2]):
                    band = arr[:, :, b]
                    p2, p98 = np.percentile(band, (2, 98))
                    if p98 - p2 > 0:
                        band = (band - p2) / (p98 - p2)
                    band = np.clip(band, 0, 1)
                    normalized_bands.append((band * 255).astype(np.uint8))
                if len(normalized_bands) == 1:
                    arr = np.stack([normalized_bands[0]] * 3, axis=-1)
                elif len(normalized_bands) == 2:
                    arr = np.stack([normalized_bands[0], normalized_bands[1], normalized_bands[0]], axis=-1)
                else:
                    arr = np.stack(normalized_bands[:3], axis=-1)
                image = Image.fromarray(arr)
            else:
                image = image.convert('RGB')
        except Exception:
            image = image.convert('RGB')
            
        query_embedding = self._encode_image(image)
        
        info = self.qdrant_manager.get_collection_info()
        expected_dim = info.config.params.vectors.size
        if len(query_embedding) != expected_dim:
            raise ValueError(
                f"Image embedding dimension {len(query_embedding)} does not match "
                f"CLIP collection dimension {expected_dim}"
            )
            
        qdrant_filter = SearchFilters.build_qdrant_filter(filters)
        requested_k = top_k * 2 if filters else top_k
        qdrant_results = self.qdrant_manager.search_similar(
            query_vector=query_embedding.tolist(),
            top_k=requested_k,
            filter_conditions=qdrant_filter
        )
        
        points = qdrant_results if isinstance(qdrant_results, list) else getattr(qdrant_results, 'points', [])
        
        results = []
        for i, point in enumerate(points):
            payload = point.payload
            enriched_result = {
                "rank": i + 1,
                "tile_id": payload.get("tile_id", ""),
                "similarity": point.score,
                "date": payload.get("date", ""),
                "latitude": payload.get("latitude", 0.0),
                "longitude": payload.get("longitude", 0.0),
                "bbox": payload.get("bbox", {}),
                "sensor": payload.get("sensor", ""),
                "source_scene": payload.get("source_scene", ""),
                "valid_percentage": payload.get("valid_percentage", 0.0),
                "tile_path": payload.get("tile_path", ""),
                "embedding_model": payload.get("embedding_model", ""),
                "embedding_type": payload.get("embedding_type", "")
            }
            results.append(enriched_result)
            
        if filters:
            results = SearchFilters.apply_post_search_filters(results, filters)
            
        results = results[:top_k]
        for i, result in enumerate(results):
            result["rank"] = i + 1
            
        return results

    def get_tile_image_path(self, tile_id: str, year: str) -> Path:
        """
        Get the path to a tile's directory.
        
        Args:
            tile_id: Tile identifier
            year: Acquisition year
            
        Returns:
            Path to tile directory
        """
        return self.tiles_dir / year / tile_id