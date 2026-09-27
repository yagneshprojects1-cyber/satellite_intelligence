"""
Automated validation tests for SIH pipeline stability
Tests all core AI pipeline components
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import sys
sys.path.append(str(Path(__file__).parent.parent))

from app.vector_db.qdrant_manager import QdrantManager


class PipelineValidator:
    """Validates all pipeline components"""
    
    def __init__(self, backend_dir: Path):
        self.backend_dir = backend_dir
        self.tiles_dir = backend_dir / "data/tiles"
        self.embeddings_dir = backend_dir / "embeddings"
        self.qdrant_storage = backend_dir / "qdrant_storage"
        
        self.results = {
            "clay_embeddings": {"expected": 983, "actual": 0, "status": "FAILED"},
            "qdrant_clay": {"expected": 983, "actual": 0, "status": "FAILED"},
            "qdrant_clip": {"expected": 983, "actual": 0, "status": "FAILED"},
            "temporal_pairs": {"expected": 544, "actual": 0, "status": "FAILED"},
            "change_results": {"expected": ">=0", "actual": 0, "status": "FAILED"},
            "metadata_consistency": {"status": "FAILED"},
            "tile_id_consistency": {"status": "FAILED"},
            "geospatial_metadata": {"status": "FAILED"},
            "embedding_dimensions": {"status": "FAILED"},
            "no_duplicate_ids": {"status": "FAILED"}
        }
    
    def count_tiles(self) -> int:
        """Count total valid tiles"""
        count = 0
        for year in ["2022", "2023", "2024"]:
            year_dir = self.tiles_dir / year
            if year_dir.exists():
                for tile_dir in year_dir.iterdir():
                    if tile_dir.is_dir() and (tile_dir / "metadata.json").exists():
                        count += 1
        return count
    
    def count_clay_embeddings(self) -> int:
        """Count Clay embedding files"""
        count = 0
        for year in ["2022", "2023", "2024"]:
            year_dir = self.embeddings_dir / year
            if year_dir.exists():
                count += len(list(year_dir.glob("*.npy")))
        return count
    
    def count_qdrant_vectors(self, collection_name: str) -> int:
        """Count vectors in Qdrant collection"""
        try:
            qm = QdrantManager(collection_name=collection_name)
            info = qm.get_collection_info()
            if info:
                return info.points_count
        except Exception as e:
            print(f"Error checking {collection_name}: {e}")
        return 0
    
    def count_temporal_pairs(self) -> int:
        """Count temporal pair files"""
        pairs_dir = self.backend_dir / "data/temporal_pairs"
        count = 0
        for year_comb in ["2022_2023", "2023_2024", "2022_2024"]:
            year_dir = pairs_dir / year_comb
            if year_dir.exists():
                count += len(list(year_dir.glob("*.json")))
        return count
    
    def count_change_results(self) -> int:
        """Count change detection results"""
        results_dir = self.backend_dir / "data/change_results"
        count = 0
        for year_comb in ["2022_2023", "2023_2024", "2022_2024"]:
            year_dir = results_dir / year_comb
            if year_dir.exists():
                count += len(list(year_dir.glob("*_result.json")))
        return count
    
    def validate_embedding_dimensions(self) -> bool:
        """Validate all Clay embeddings are 1024-D"""
        for year in ["2022", "2023", "2024"]:
            year_dir = self.embeddings_dir / year
            if year_dir.exists():
                for npy_file in year_dir.glob("*.npy"):
                    try:
                        emb = np.load(npy_file)
                        if emb.shape[0] != 1024:
                            print(f"Invalid dimension in {npy_file}: {emb.shape[0]}")
                            return False
                    except Exception as e:
                        print(f"Error loading {npy_file}: {e}")
                        return False
        return True
    
    def validate_metadata_consistency(self) -> bool:
        """Validate metadata between tiles and embeddings"""
        # Check that each embedding has corresponding tile metadata
        for year in ["2022", "2023", "2024"]:
            year_dir = self.embeddings_dir / year
            if year_dir.exists():
                for json_file in year_dir.glob("*.json"):
                    try:
                        with open(json_file, 'r') as f:
                            meta = json.load(f)
                        
                        # Check required fields
                        required = ["tile_id", "year", "date", "latitude", "longitude", "bbox"]
                        for field in required:
                            if field not in meta:
                                print(f"Missing field {field} in {json_file}")
                                return False
                        
                        # Check corresponding .npy exists
                        npy_file = json_file.with_suffix(".npy")
                        if not npy_file.exists():
                            print(f"Missing .npy for {json_file}")
                            return False
                            
                    except Exception as e:
                        print(f"Error validating {json_file}: {e}")
                        return False
        return True
    
    def validate_tile_id_consistency(self) -> bool:
        """Validate tile_id consistency across components"""
        tile_ids = set()
        
        # Collect tile IDs from tiles
        for year in ["2022", "2023", "2024"]:
            year_dir = self.tiles_dir / year
            if year_dir.exists():
                for tile_dir in year_dir.iterdir():
                    if tile_dir.is_dir() and (tile_dir / "metadata.json").exists():
                        with open(tile_dir / "metadata.json", 'r') as f:
                            meta = json.load(f)
                        tile_ids.add(meta["tile_id"])
        
        # Check embeddings match
        for year in ["2022", "2023", "2024"]:
            year_dir = self.embeddings_dir / year
            if year_dir.exists():
                for json_file in year_dir.glob("*.json"):
                    with open(json_file, 'r') as f:
                        meta = json.load(f)
                    if meta["tile_id"] not in tile_ids:
                        print(f"Embedding tile_id not in tiles: {meta['tile_id']}")
                        return False
        
        return True
    
    def validate_geospatial_metadata(self) -> bool:
        """Validate geospatial metadata format"""
        for year in ["2022", "2023", "2024"]:
            year_dir = self.embeddings_dir / year
            if year_dir.exists():
                for json_file in year_dir.glob("*.json"):
                    with open(json_file, 'r') as f:
                        meta = json.load(f)
                    
                    # Check bbox format
                    bbox = meta.get("bbox", {})
                    required_bbox_keys = ["min_lon", "min_lat", "max_lon", "max_lat"]
                    for key in required_bbox_keys:
                        if key not in bbox:
                            print(f"Missing bbox key {key} in {json_file}")
                            return False
                    
                    # Check lat/lon are numeric
                    try:
                        lat = float(meta["latitude"])
                        lon = float(meta["longitude"])
                        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                            print(f"Invalid lat/lon in {json_file}")
                            return False
                    except (ValueError, TypeError):
                        print(f"Invalid lat/lon format in {json_file}")
                        return False
        
        return True
    
    def validate_no_duplicate_ids(self) -> bool:
        """Validate no duplicate tile IDs"""
        tile_ids = []
        
        for year in ["2022", "2023", "2024"]:
            year_dir = self.tiles_dir / year
            if year_dir.exists():
                for tile_dir in year_dir.iterdir():
                    if tile_dir.is_dir() and (tile_dir / "metadata.json").exists():
                        with open(tile_dir / "metadata.json", 'r') as f:
                            meta = json.load(f)
                        tile_ids.append(meta["tile_id"])
        
        if len(tile_ids) != len(set(tile_ids)):
            duplicates = [tid for tid in tile_ids if tile_ids.count(tid) > 1]
            print(f"Duplicate tile IDs found: {set(duplicates)}")
            return False
        
        return True
    
    def run_all_tests(self) -> Dict:
        """Run all validation tests"""
        print("=" * 60)
        print("PIPELINE VALIDATION TESTS")
        print("=" * 60)
        
        # Test 1: Count tiles
        total_tiles = self.count_tiles()
        print(f"\n1. Total tiles: {total_tiles} (expected: 983)")
        self.results["clay_embeddings"]["expected"] = total_tiles
        
        # Test 2: Count Clay embeddings
        clay_emb_count = self.count_clay_embeddings()
        print(f"2. Clay embeddings: {clay_emb_count} (expected: {total_tiles})")
        self.results["clay_embeddings"]["actual"] = clay_emb_count
        self.results["clay_embeddings"]["status"] = "PASS" if clay_emb_count == total_tiles else "FAIL"
        
        # Test 3: Count Qdrant Clay vectors
        qdrant_clay_count = self.count_qdrant_vectors("satellite_tiles")
        print(f"3. Qdrant Clay vectors: {qdrant_clay_count} (expected: {total_tiles})")
        self.results["qdrant_clay"]["actual"] = qdrant_clay_count
        self.results["qdrant_clay"]["expected"] = total_tiles
        self.results["qdrant_clay"]["status"] = "PASS" if qdrant_clay_count == total_tiles else "FAIL"
        
        # Test 4: Count Qdrant CLIP vectors
        qdrant_clip_count = self.count_qdrant_vectors("satellite_tiles_clip")
        print(f"4. Qdrant CLIP vectors: {qdrant_clip_count} (expected: {total_tiles})")
        self.results["qdrant_clip"]["actual"] = qdrant_clip_count
        self.results["qdrant_clip"]["expected"] = total_tiles
        self.results["qdrant_clip"]["status"] = "PASS" if qdrant_clip_count == total_tiles else "FAIL"
        
        # Test 5: Count temporal pairs
        temporal_count = self.count_temporal_pairs()
        print(f"5. Temporal pairs: {temporal_count} (expected: 544)")
        self.results["temporal_pairs"]["actual"] = temporal_count
        self.results["temporal_pairs"]["status"] = "PASS" if temporal_count == 544 else "FAIL"
        
        # Test 6: Count change results
        change_count = self.count_change_results()
        print(f"6. Change results: {change_count} (expected: >=0)")
        self.results["change_results"]["actual"] = change_count
        self.results["change_results"]["status"] = "PASS"
        
        # Test 7: Validate embedding dimensions
        print("7. Validating embedding dimensions...")
        dim_valid = self.validate_embedding_dimensions()
        print(f"   Result: {'PASS' if dim_valid else 'FAIL'}")
        self.results["embedding_dimensions"]["status"] = "PASS" if dim_valid else "FAIL"
        
        # Test 8: Validate metadata consistency
        print("8. Validating metadata consistency...")
        meta_valid = self.validate_metadata_consistency()
        print(f"   Result: {'PASS' if meta_valid else 'FAIL'}")
        self.results["metadata_consistency"]["status"] = "PASS" if meta_valid else "FAIL"
        
        # Test 9: Validate tile ID consistency
        print("9. Validating tile ID consistency...")
        id_valid = self.validate_tile_id_consistency()
        print(f"   Result: {'PASS' if id_valid else 'FAIL'}")
        self.results["tile_id_consistency"]["status"] = "PASS" if id_valid else "FAIL"
        
        # Test 10: Validate geospatial metadata
        print("10. Validating geospatial metadata...")
        geo_valid = self.validate_geospatial_metadata()
        print(f"   Result: {'PASS' if geo_valid else 'FAIL'}")
        self.results["geospatial_metadata"]["status"] = "PASS" if geo_valid else "FAIL"
        
        # Test 11: Validate no duplicate IDs
        print("11. Validating no duplicate tile IDs...")
        dup_valid = self.validate_no_duplicate_ids()
        print(f"   Result: {'PASS' if dup_valid else 'FAIL'}")
        self.results["no_duplicate_ids"]["status"] = "PASS" if dup_valid else "FAIL"
        
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        
        for test_name, result in self.results.items():
            status = result["status"]
            expected = result.get("expected", "N/A")
            actual = result.get("actual", "N/A")
            print(f"{test_name:25s}: {status:6s} (expected: {expected}, actual: {actual})")
        
        # Overall status
        all_pass = all(r["status"] == "PASS" for r in self.results.values())
        print(f"\nOverall: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
        
        return self.results


if __name__ == "__main__":
    backend_dir = Path(__file__).parent.parent
    validator = PipelineValidator(backend_dir)
    results = validator.run_all_tests()
    
    # Save results
    results_file = backend_dir / "test" / "validation_results.json"
    results_file.parent.mkdir(exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {results_file}")
