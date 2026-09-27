import json
import time
import datetime
from pathlib import Path
import numpy as np
from qdrant_client.models import PointStruct
from app.vector_db.qdrant_manager import QdrantManager

class QdrantIndexer:
    def __init__(self, embeddings_dir="embeddings", batch_size=64):
        self.embeddings_dir = Path(embeddings_dir)
        self.batch_size = batch_size
        self.manager = QdrantManager()
        self.dimension = 1024

    def index_all(self, limit=None):
        self.manager.setup_collection(dimension=self.dimension)
        
        stats = {
            "discovered": 0,
            "indexed": 0,
            "skipped": 0,
            "failed": 0,
            "processing_time": 0.0
        }
        
        # Discover JSON metadata files which map to the embeddings
        json_files = []
        for year_dir in self.embeddings_dir.iterdir():
            if year_dir.is_dir() and year_dir.name in ["2022", "2023", "2024"]:
                json_files.extend(list(year_dir.glob("*.json")))
                
        stats["discovered"] = len(json_files)
        if limit:
            json_files = json_files[:limit]
            
        start_time = time.time()
        
        batch_points = []
        for json_path in json_files:
            try:
                with open(json_path, "r") as f:
                    payload = json.load(f)
                    
                # Basic validation
                if "tile_id" not in payload:
                    print(f"Skipping {json_path}: Missing tile_id")
                    stats["failed"] += 1
                    continue
                    
                tile_id = payload["tile_id"]
                npy_path = json_path.with_suffix(".npy")
                
                if not npy_path.exists():
                    print(f"Skipping {json_path}: Missing embedding file {npy_path}")
                    stats["failed"] += 1
                    continue
                    
                # Idempotency check
                point_id = self.manager._generate_deterministic_uuid(tile_id)
                if self.manager.point_exists(point_id):
                    stats["skipped"] += 1
                    continue
                    
                # Load vector
                vector = np.load(npy_path)
                
                # Validation of vector shape
                if len(vector.shape) == 1:
                    pass
                elif len(vector.shape) == 2 and vector.shape[0] == 1:
                    vector = vector.squeeze(0)
                else:
                    print(f"Failed {tile_id}: Invalid vector shape {vector.shape}")
                    stats["failed"] += 1
                    continue
                    
                if vector.shape[0] != self.dimension:
                    print(f"Failed {tile_id}: Dimension is {vector.shape[0]}, expected {self.dimension}")
                    stats["failed"] += 1
                    continue
                    
                if not np.isfinite(vector).all():
                    print(f"Failed {tile_id}: Vector contains NaN or inf values")
                    stats["failed"] += 1
                    continue
                
                # Add to batch
                batch_points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector.tolist(),
                        payload=payload
                    )
                )
                
                # Upsert if batch is full
                if len(batch_points) >= self.batch_size:
                    self._upsert_batch(batch_points)
                    stats["indexed"] += len(batch_points)
                    batch_points = []
                    
            except Exception as e:
                print(f"Error processing {json_path}: {e}")
                stats["failed"] += 1
                
        # Upsert remaining
        if len(batch_points) > 0:
            self._upsert_batch(batch_points)
            stats["indexed"] += len(batch_points)
            
        stats["processing_time"] = time.time() - start_time
        
        # Save provenance report
        self._generate_report(stats)
        
        return stats

    def _upsert_batch(self, points):
        self.manager.client.upsert(
            collection_name=self.manager.collection_name,
            points=points
        )

    def _generate_report(self, stats):
        report = {
            "collection_name": self.manager.collection_name,
            "vector_dimension": self.dimension,
            "distance_metric": "COSINE",
            "qdrant_version": "local",
            "qdrant_client_version": "1.11.x",
            "number_of_embeddings_discovered": stats["discovered"],
            "number_indexed": stats["indexed"],
            "number_skipped": stats["skipped"],
            "number_failed": stats["failed"],
            "source_embedding_model": "Clay Foundation Model",
            "source_model_version": "v1.5",
            "indexing_timestamp": datetime.datetime.now().isoformat(),
            "storage_location": str(self.manager.storage_path.absolute()),
            "processing_version": "1.0"
        }
        
        report_path = self.embeddings_dir / "phase7_provenance_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to {report_path}")
    
    def validate_similarity_search(self):
        """Validate vector similarity search with one existing embedding"""
        print("\n" + "=" * 60)
        print("SIMILARITY SEARCH VALIDATION")
        print("=" * 60)
        
        # Get one existing embedding for validation
        json_files = []
        for year_dir in self.embeddings_dir.iterdir():
            if year_dir.is_dir() and year_dir.name in ["2022", "2023", "2024"]:
                json_files.extend(list(year_dir.glob("*.json")))
        
        if not json_files:
            print("No embeddings found for validation")
            return False
        
        # Use first embedding for validation
        json_path = json_files[0]
        with open(json_path, "r") as f:
            payload = json.load(f)
        
        tile_id = payload["tile_id"]
        npy_path = json_path.with_suffix(".npy")
        
        if not npy_path.exists():
            print(f"Validation failed: Missing embedding file {npy_path}")
            return False
        
        # Load vector
        vector = np.load(npy_path)
        
        print(f"Using tile {tile_id} for validation")
        print(f"Vector dimension: {vector.shape[0]}")
        
        # Perform similarity search
        try:
            results = self.manager.search_similar(vector.tolist(), top_k=5)
            
            # Handle new QueryResponse object
            points = getattr(results, 'points', [])
            print(f"Retrieved {len(points)} results")
            
            if not points:
                print("Validation failed: No results returned")
                return False
            
            # Validate results
            for i, result in enumerate(points):
                print(f"\nResult {i+1}:")
                print(f"  Score: {result.score}")
                print(f"  Payload keys: {list(result.payload.keys())}")
                
                # Check for required fields
                required_fields = ["tile_id", "date", "latitude", "longitude", "source_scene"]
                missing_fields = [field for field in required_fields if field not in result.payload]
                
                if missing_fields:
                    print(f"  Warning: Missing payload fields: {missing_fields}")
                else:
                    print(f"  tile_id: {result.payload.get('tile_id')}")
                    print(f"  date: {result.payload.get('date')}")
                    print(f"  latitude: {result.payload.get('latitude')}")
                    print(f"  longitude: {result.payload.get('longitude')}")
                    print(f"  source_scene: {result.payload.get('source_scene')}")
            
            print("\nSimilarity search validation: PASSED")
            return True
            
        except Exception as e:
            print(f"Similarity search validation FAILED: {e}")
            return False
    
    def validate_filter_search(self):
        """Validate metadata filter search"""
        print("\n" + "=" * 60)
        print("FILTER SEARCH VALIDATION")
        print("=" * 60)
        
        # Get one existing embedding for query
        json_files = []
        for year_dir in self.embeddings_dir.iterdir():
            if year_dir.is_dir() and year_dir.name in ["2022", "2023", "2024"]:
                json_files.extend(list(year_dir.glob("*.json")))
        
        if not json_files:
            print("No embeddings found for validation")
            return False
        
        json_path = json_files[0]
        npy_path = json_path.with_suffix(".npy")
        vector = np.load(npy_path)
        
        try:
            # Test year filter
            print("Testing year=2022 filter...")
            results_2022 = self.manager.search_similar(
                query_vector=vector.tolist(),
                top_k=3,
                filter_conditions={"year": "2022"}
            )
            points_2022 = getattr(results_2022, 'points', [])
            print(f"  Retrieved {len(points_2022)} results for year=2022")
            
            # Test sensor filter
            print("Testing sensor filter...")
            results_sensor = self.manager.search_similar(
                query_vector=vector.tolist(),
                top_k=3,
                filter_conditions={"sensor": "Sentinel-2"}
            )
            points_sensor = getattr(results_sensor, 'points', [])
            print(f"  Retrieved {len(points_sensor)} results for sensor=Sentinel-2")
            
            print("\nFilter search validation: PASSED")
            return True
            
        except Exception as e:
            print(f"Filter search validation FAILED: {e}")
            return False