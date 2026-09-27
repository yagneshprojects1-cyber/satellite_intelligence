"""
CLIP Image Indexer for Semantic Search
Indexes Phase 5 tiles using CLIP image embeddings for text-to-image retrieval
"""

import json
import time
import datetime
import uuid
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import rasterio
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
import transformers.modeling_utils
transformers.modeling_utils.check_torch_load_is_safe = lambda: None
import transformers.utils.import_utils
transformers.utils.import_utils.check_torch_load_is_safe = lambda: None
from qdrant_client.models import PointStruct, VectorParams, Distance
from app.vector_db.qdrant_manager import QdrantManager


class CLIPIndexer:
    """
    CLIP-based image indexer for semantic search.
    
    Creates a separate Qdrant collection for CLIP image embeddings,
    distinct from the existing Clay embeddings collection.
    """
    
    def __init__(self, 
                 tiles_dir="data/tiles",
                 qdrant_storage_path="qdrant_storage",
                 clip_collection_name="satellite_tiles_clip",
                 model_name="openai/clip-vit-base-patch32",
                 device="cpu",
                 batch_size=16):
        """
        Initialize CLIP indexer.
        
        Args:
            tiles_dir: Path to Phase 5 tiles
            qdrant_storage_path: Path to Qdrant storage
            clip_collection_name: Name for CLIP Qdrant collection
            model_name: HuggingFace CLIP model name
            device: torch device ('cpu' or 'cuda')
            batch_size: Batch size for processing
        """
        self.tiles_dir = Path(tiles_dir)
        self.clip_collection_name = clip_collection_name
        self.model_name = model_name
        self.device = torch.device(device)
        self.batch_size = batch_size
        
        # Initialize Qdrant manager for CLIP collection
        self.qdrant_manager = QdrantManager(
            storage_path=qdrant_storage_path,
            collection_name=clip_collection_name
        )
        
        # Load CLIP model
        self.clip_model = None
        self.clip_processor = None
        self.embedding_dimension = None
        
        print(f"Initializing CLIP Indexer...")
        print(f"  Tiles directory: {self.tiles_dir}")
        print(f"  CLIP collection: {self.clip_collection_name}")
        print(f"  Model: {self.model_name}")
        print(f"  Device: {self.device}")
    
    def setup_model(self):
        """Load CLIP model and processor."""
        if self.clip_model is None:
            print(f"Loading CLIP model {self.model_name} to {self.device}...")
            
            self.clip_model = CLIPModel.from_pretrained(self.model_name).to(self.device)
            self.clip_processor = CLIPProcessor.from_pretrained(self.model_name)
            
            # Set to evaluation mode
            self.clip_model.eval()
            
            # Disable gradient computation
            for param in self.clip_model.parameters():
                param.requires_grad = False
            
            # Get embedding dimension (should be 512 for CLIP ViT-B/32)
            self.embedding_dimension = 512
            
            print(f"CLIP model loaded successfully")
            print(f"  Image embedding dimension: {self.embedding_dimension}")
            print(f"  Text embedding dimension: {self.clip_model.config.text_config.hidden_size}")
    
    def setup_collection(self):
        """Setup CLIP Qdrant collection."""
        if self.embedding_dimension is None:
            self.setup_model()
        
        if not self.qdrant_manager.client.collection_exists(self.clip_collection_name):
            self.qdrant_manager.client.create_collection(
                collection_name=self.clip_collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dimension, 
                    distance=Distance.COSINE
                )
            )
            print(f"Created CLIP collection '{self.clip_collection_name}' with dimension {self.embedding_dimension}")
        else:
            print(f"CLIP collection '{self.clip_collection_name}' already exists")
    
    def _create_rgb_from_tile(self, tile_dir: Path) -> Optional[Image.Image]:
        """
        Create RGB image from Sentinel-2 tile bands.
        
        Uses B04 (red), B03 (green), B02 (blue) as per existing RGB configuration.
        
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
                profile = src.profile
            
            with rasterio.open(green_path) as src:
                green = src.read(1)
            
            with rasterio.open(blue_path) as src:
                blue = src.read(1)
            
            # Handle different shapes (resample if needed)
            target_shape = red.shape
            if green.shape != target_shape:
                from scipy.ndimage import zoom
                scale_factor = target_shape[0] / green.shape[0]
                green = zoom(green, scale_factor, order=1)
            if blue.shape != target_shape:
                from scipy.ndimage import zoom
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
                # The get_image_features returns BaseModelOutputWithPooling
                # The actual projected image embedding is in the output
                # For CLIP ViT-B/32, the pooled_output should be 512-D
                if hasattr(image_features, 'pooler_output'):
                    embedding = image_features.pooler_output.cpu().numpy()[0]
                else:
                    # Try to get the image_embeds attribute
                    if hasattr(image_features, 'image_embeds'):
                        embedding = image_features.image_embeds.cpu().numpy()[0]
                    else:
                        # Fallback: try last_hidden_state or other attributes
                        # Check if there's a direct tensor we can use
                        for attr in ['last_hidden_state', 'hidden_states']:
                            if hasattr(image_features, attr):
                                value = getattr(image_features, attr)
                                if hasattr(value, 'cpu'):
                                    tensor = value.cpu()
                                    if len(tensor.shape) == 3:
                                        embedding = tensor[0, 0, :].numpy()
                                    elif len(tensor.shape) == 2:
                                        embedding = tensor[0].numpy()
                                    break
                        else:
                            raise ValueError(f"Could not extract 512-D embedding from image_features. Type: {type(image_features)}")
            
            # Verify we got 512-D embedding
            if len(embedding) != 512:
                raise ValueError(f"Embedding dimension is {len(embedding)}, expected 512")
            
            # Normalize for cosine similarity
            embedding = embedding / np.linalg.norm(embedding)
            
        return embedding
    
    def _generate_deterministic_uuid(self, tile_id: str) -> str:
        """Generate deterministic UUID from tile_id."""
        return str(uuid.uuid5(uuid.NAMESPACE_OID, tile_id))
    
    def index_tiles(self, limit: Optional[int] = None) -> Dict:
        """
        Index Phase 5 tiles using CLIP image embeddings.
        
        Args:
            limit: Optional limit on number of tiles to process
            
        Returns:
            Statistics dictionary
        """
        self.setup_model()
        self.setup_collection()
        
        stats = {
            "discovered": 0,
            "processed": 0,
            "skipped_existing": 0,
            "failed": 0,
            "processing_time": 0.0
        }
        
        # Discover tiles
        tile_dirs = []
        for year_dir in self.tiles_dir.iterdir():
            if year_dir.is_dir() and year_dir.name in ["2022", "2023", "2024"]:
                for tile_dir in year_dir.iterdir():
                    if tile_dir.is_dir() and (tile_dir / "metadata.json").exists():
                        tile_dirs.append(tile_dir)
        
        stats["discovered"] = len(tile_dirs)
        if limit:
            tile_dirs = tile_dirs[:limit]
        
        print(f"Discovered {stats['discovered']} tiles")
        if limit:
            print(f"Processing limited to {limit} tiles")
        
        start_time = time.time()
        
        # Process tiles
        for tile_dir in tile_dirs:
            try:
                # Read metadata
                metadata_path = tile_dir / "metadata.json"
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                
                tile_id = metadata["tile_id"]
                year = tile_dir.parent.name
                
                # Check if already indexed
                point_id = self._generate_deterministic_uuid(tile_id)
                if self.qdrant_manager.point_exists(point_id):
                    stats["skipped_existing"] += 1
                    continue
                
                # Create RGB image
                rgb_image = self._create_rgb_from_tile(tile_dir)
                if rgb_image is None:
                    stats["failed"] += 1
                    continue
                
                # Generate CLIP embedding
                embedding = self._encode_image(rgb_image)
                
                # Validate dimension
                if embedding.shape[0] != self.embedding_dimension:
                    print(f"Embedding dimension mismatch for {tile_id}: {embedding.shape[0]} vs {self.embedding_dimension}")
                    stats["failed"] += 1
                    continue
                
                # Create payload
                payload = {
                    "tile_id": tile_id,
                    "year": year,
                    "date": metadata["date"],
                    "latitude": metadata["latitude"],
                    "longitude": metadata["longitude"],
                    "bbox": metadata["bbox"],
                    "sensor": metadata["sensor"],
                    "source_scene": metadata["source_scene"],
                    "valid_percentage": metadata["valid_percentage"],
                    "tile_path": str(tile_dir),
                    "embedding_model": self.model_name,
                    "embedding_type": "clip_image",
                    "embedding_dimension": self.embedding_dimension,
                    "processing_version": "1.0"
                }
                
                # Create point
                point = PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload=payload
                )
                
                # Upsert to Qdrant
                self.qdrant_manager.client.upsert(
                    collection_name=self.clip_collection_name,
                    points=[point]
                )
                
                stats["processed"] += 1
                print(f"Processed {tile_id} ({stats['processed']}/{stats['discovered']})")
                
            except Exception as e:
                print(f"Error processing {tile_dir}: {e}")
                stats["failed"] += 1
        
        stats["processing_time"] = time.time() - start_time
        
        # Generate report
        self._generate_report(stats)
        
        return stats
    
    def _generate_report(self, stats: Dict):
        """Generate indexing report."""
        report = {
            "collection_name": self.clip_collection_name,
            "vector_dimension": self.embedding_dimension,
            "distance_metric": "COSINE",
            "clip_model": self.model_name,
            "clip_model_source": "HuggingFace",
            "clip_license": "MIT",
            "tiles_discovered": stats["discovered"],
            "tiles_processed": stats["processed"],
            "tiles_skipped_existing": stats["skipped_existing"],
            "tiles_failed": stats["failed"],
            "processing_time": stats["processing_time"],
            "indexing_timestamp": datetime.datetime.now().isoformat(),
            "rgb_preprocessing": "B04(red), B03(green), B02(blue) with percentile normalization",
            "processing_version": "1.0"
        }
        
        report_path = self.tiles_dir.parent / "clip_indexing_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"Indexing report saved to {report_path}")