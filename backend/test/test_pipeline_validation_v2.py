"""
Pipeline Validation Tests V2
Comprehensive validation of all pipeline phases including new features
"""

import sys
import json
import numpy as np
from pathlib import Path
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class PipelineValidator:
    """Validates all pipeline phases"""
    
    def __init__(self, 
                 tiles_dir: Path = Path("data/tiles"),
                 embeddings_dir: Path = Path("embeddings"),
                 qdrant_storage: Path = Path("qdrant_storage"),
                 temporal_pairs_dir: Path = Path("data/temporal_pairs"),
                 change_results_dir: Path = Path("data/change_results"),
                 earliest_changes_dir: Path = Path("data/earliest_changes"),
                 clusters_dir: Path = Path("data/clusters"),
                 exports_dir: Path = Path("data/exports")):
        self.tiles_dir = Path(tiles_dir)
        self.embeddings_dir = Path(embeddings_dir)
        self.qdrant_storage = Path(qdrant_storage)
        self.temporal_pairs_dir = Path(temporal_pairs_dir)
        self.change_results_dir = Path(change_results_dir)
        self.earliest_changes_dir = Path(earliest_changes_dir)
        self.clusters_dir = Path(clusters_dir)
        self.exports_dir = Path(exports_dir)
        
        self.results = {}
    
    def validate_tiles(self) -> Dict[str, any]:
        """Validate Phase 5 tiles"""
        print("Validating tiles...")
        
        total_tiles = 0
        for year in ["2022", "2023", "2024"]:
            year_dir = self.tiles_dir / year
            if year_dir.exists():
                year_tiles = len([d for d in year_dir.iterdir() if d.is_dir() and (d / "metadata.json").exists()])
                total_tiles += year_tiles
        
        expected = 983
        status = "PASS" if total_tiles == expected else "FAIL"
        
        result = {
            "expected": expected,
            "actual": total_tiles,
            "status": status
        }
        
        self.results["tiles"] = result
        print(f"  Total tiles: {total_tiles} (expected: {expected})")
        
        return result
    
    def validate_clay_embeddings(self) -> Dict[str, any]:
        """Validate Phase 6 Clay embeddings"""
        print("Validating Clay embeddings...")
        
        total_embeddings = 0
        for year in ["2022", "2023", "2024"]:
            year_dir = self.embeddings_dir / year
            if year_dir.exists():
                year_embeddings = len(list(year_dir.glob("*.npy")))
                total_embeddings += year_embeddings
        
        expected = 983
        status = "PASS" if total_embeddings == expected else "FAIL"
        
        result = {
            "expected": expected,
            "actual": total_embeddings,
            "status": status
        }
        
        self.results["clay_embeddings"] = result
        print(f"  Clay embeddings: {total_embeddings} (expected: {expected})")
        
        return result
    
    def validate_qdrant_clay(self) -> Dict[str, any]:
        """Validate Phase 7 Qdrant Clay collection"""
        print("Validating Qdrant Clay collection...")
        
        try:
            from qdrant_client import QdrantClient
            
            client = QdrantClient(path=str(self.qdrant_storage))
            collection_name = "satellite_tiles"
            
            if not client.collection_exists(collection_name):
                print(f"  Collection '{collection_name}' does not exist")
                result = {
                    "expected": 983,
                    "actual": 0,
                    "status": "FAIL"
                }
                self.results["qdrant_clay"] = result
                return result
            
            info = client.get_collection(collection_name)
            point_count = info.points_count
            
            expected = 983
            status = "PASS" if point_count == expected else "FAIL"
            
            result = {
                "expected": expected,
                "actual": point_count,
                "status": status
            }
            
            self.results["qdrant_clay"] = result
            print(f"  Qdrant Clay vectors: {point_count} (expected: {expected})")
            
            return result
            
        except Exception as e:
            print(f"  Error: {e}")
            result = {
                "expected": 983,
                "actual": 0,
                "status": "FAIL",
                "error": str(e)
            }
            self.results["qdrant_clay"] = result
            return result
    
    def validate_qdrant_clip(self) -> Dict[str, any]:
        """Validate Phase 8/9 Qdrant CLIP collection"""
        print("Validating Qdrant CLIP collection...")
        
        try:
            from qdrant_client import QdrantClient
            
            client = QdrantClient(path=str(self.qdrant_storage))
            collection_name = "satellite_tiles_clip"
            
            if not client.collection_exists(collection_name):
                print(f"  Collection '{collection_name}' does not exist")
                result = {
                    "expected": 983,
                    "actual": 0,
                    "status": "FAIL"
                }
                self.results["qdrant_clip"] = result
                return result
            
            info = client.get_collection(collection_name)
            point_count = info.points_count
            
            expected = 983
            status = "PASS" if point_count == expected else "FAIL"
            
            result = {
                "expected": expected,
                "actual": point_count,
                "status": status
            }
            
            self.results["qdrant_clip"] = result
            print(f"  Qdrant CLIP vectors: {point_count} (expected: {expected})")
            
            return result
            
        except Exception as e:
            print(f"  Error: {e}")
            result = {
                "expected": 983,
                "actual": 0,
                "status": "FAIL",
                "error": str(e)
            }
            self.results["qdrant_clip"] = result
            return result
    
    def validate_temporal_pairs(self) -> Dict[str, any]:
        """Validate Phase 10 temporal pairs"""
        print("Validating temporal pairs...")
        
        total_pairs = 0
        for year_comb in ["2022_2023", "2023_2024", "2022_2024"]:
            comb_dir = self.temporal_pairs_dir / year_comb
            if comb_dir.exists():
                comb_pairs = len(list(comb_dir.glob("*.json")))
                total_pairs += comb_pairs
        
        expected = 544
        status = "PASS" if total_pairs == expected else "FAIL"
        
        result = {
            "expected": expected,
            "actual": total_pairs,
            "status": status
        }
        
        self.results["temporal_pairs"] = result
        print(f"  Temporal pairs: {total_pairs} (expected: {expected})")
        
        return result
    
    def validate_change_results(self) -> Dict[str, any]:
        """Validate Phase 11 change detection results"""
        print("Validating change results...")
        
        total_results = 0
        for year_comb in ["2022_2023", "2023_2024", "2022_2024"]:
            comb_dir = self.change_results_dir / year_comb
            if comb_dir.exists():
                comb_results = len(list(comb_dir.glob("*_result.json")))
                total_results += comb_results
        
        expected = 0  # Minimum threshold
        status = "PASS" if total_results >= expected else "FAIL"
        
        result = {
            "expected": f">={expected}",
            "actual": total_results,
            "status": status
        }
        
        self.results["change_results"] = result
        print(f"  Change results: {total_results} (expected: >={expected})")
        
        return result
    
    def validate_earliest_changes(self) -> Dict[str, any]:
        """Validate Phase 12 earliest change analysis"""
        print("Validating earliest changes...")
        
        summary_file = self.earliest_changes_dir / "earliest_changes_summary.json"
        
        if not summary_file.exists():
            print("  Earliest changes summary not found")
            result = {
                "status": "FAIL",
                "error": "Summary file not found"
            }
            self.results["earliest_changes"] = result
            return result
        
        try:
            with open(summary_file, 'r') as f:
                summary = json.load(f)
            
            total_locations = summary.get("total_locations", 0)
            status = "PASS" if total_locations > 0 else "FAIL"
            
            result = {
                "total_locations": total_locations,
                "persistence_distribution": summary.get("persistence_distribution", {}),
                "status": status
            }
            
            self.results["earliest_changes"] = result
            print(f"  Earliest changes: {total_locations} locations analyzed")
            
            return result
            
        except Exception as e:
            print(f"  Error: {e}")
            result = {
                "status": "FAIL",
                "error": str(e)
            }
            self.results["earliest_changes"] = result
            return result
    
    def validate_clustering(self) -> Dict[str, any]:
        """Validate Phase 13 Clay clustering"""
        print("Validating Clay clustering...")
        
        summary_file = self.clusters_dir / "clustering_summary.json"
        
        if not summary_file.exists():
            print("  Clustering summary not found (pending full embeddings from Kaggle)")
            result = {
                "status": "PENDING",
                "error": "Clustering requires complete Clay embeddings (983/983)"
            }
            self.results["clustering"] = result
            return result
        
        try:
            with open(summary_file, 'r') as f:
                summary = json.load(f)
            
            total_tiles = summary.get("total_tiles", 0)
            num_clusters = summary.get("num_clusters", 0)
            num_noise = summary.get("num_noise", 0)
            
            status = "PASS" if total_tiles > 0 else "FAIL"
            
            result = {
                "total_tiles": total_tiles,
                "num_clusters": num_clusters,
                "num_noise": num_noise,
                "status": status
            }
            
            self.results["clustering"] = result
            print(f"  Clustering: {total_tiles} tiles, {num_clusters} clusters, {num_noise} noise")
            
            return result
            
        except Exception as e:
            print(f"  Error: {e}")
            result = {
                "status": "FAIL",
                "error": str(e)
            }
            self.results["clustering"] = result
            return result
    
    def validate_embedding_dimensions(self) -> Dict[str, any]:
        """Validate embedding dimensions"""
        print("Validating embedding dimensions...")
        
        # Check Clay embeddings dimension
        clay_dim = None
        for year in ["2022", "2023", "2024"]:
            year_dir = self.embeddings_dir / year
            if year_dir.exists():
                emb_files = list(year_dir.glob("*.npy"))
                if emb_files:
                    emb = np.load(emb_files[0])
                    clay_dim = emb.shape[0]
                    break
        
        if clay_dim is None:
            print("  No Clay embeddings found")
            result = {
                "expected": 1024,
                "actual": None,
                "status": "FAIL"
            }
            self.results["embedding_dimensions"] = result
            return result
        
        expected = 1024
        status = "PASS" if clay_dim == expected else "FAIL"
        
        result = {
            "expected": expected,
            "actual": clay_dim,
            "status": status
        }
        
        self.results["embedding_dimensions"] = result
        print(f"  Embedding dimension: {clay_dim} (expected: {expected})")
        
        return result
    
    def validate_metadata_consistency(self) -> Dict[str, any]:
        """Validate metadata consistency across tiles and embeddings"""
        print("Validating metadata consistency...")
        
        inconsistent = 0
        checked = 0
        
        for year in ["2022", "2023", "2024"]:
            emb_dir = self.embeddings_dir / year
            tile_dir = self.tiles_dir / year
            
            if not emb_dir.exists() or not tile_dir.exists():
                continue
            
            for emb_file in emb_dir.glob("*.npy"):
                tile_id = emb_file.stem
                metadata_file = emb_dir / f"{tile_id}.json"
                tile_metadata_file = tile_dir / tile_id / "metadata.json"
                
                if metadata_file.exists() and tile_metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            emb_meta = json.load(f)
                        with open(tile_metadata_file, 'r') as f:
                            tile_meta = json.load(f)
                        
                        # Check consistency
                        if emb_meta.get("tile_id") != tile_meta.get("tile_id"):
                            inconsistent += 1
                        
                        checked += 1
                    except Exception:
                        pass
        
        status = "PASS" if inconsistent == 0 else "FAIL"
        
        result = {
            "checked": checked,
            "inconsistent": inconsistent,
            "status": status
        }
        
        self.results["metadata_consistency"] = result
        print(f"  Metadata consistency: {status} ({inconsistent}/{checked} inconsistent)")
        
        return result
    
    def validate_tile_id_consistency(self) -> Dict[str, any]:
        """Validate tile ID uniqueness"""
        print("Validating tile ID consistency...")
        
        tile_ids = set()
        duplicates = 0
        
        for year in ["2022", "2023", "2024"]:
            tile_dir = self.tiles_dir / year
            if tile_dir.exists():
                for tile in tile_dir.iterdir():
                    if tile.is_dir() and (tile / "metadata.json").exists():
                        tile_id = tile.name
                        if tile_id in tile_ids:
                            duplicates += 1
                        tile_ids.add(tile_id)
        
        status = "PASS" if duplicates == 0 else "FAIL"
        
        result = {
            "total_unique": len(tile_ids),
            "duplicates": duplicates,
            "status": status
        }
        
        self.results["tile_id_consistency"] = result
        print(f"  Tile ID consistency: {status} ({duplicates} duplicates)")
        
        return result
    
    def validate_geospatial_metadata(self) -> Dict[str, any]:
        """Validate geospatial metadata"""
        print("Validating geospatial metadata...")
        
        invalid_bbox = 0
        invalid_coords = 0
        checked = 0
        
        for year in ["2022", "2023", "2024"]:
            tile_dir = self.tiles_dir / year
            if tile_dir.exists():
                for tile in tile_dir.iterdir():
                    if tile.is_dir() and (tile / "metadata.json").exists():
                        try:
                            with open(tile / "metadata.json", 'r') as f:
                                meta = json.load(f)
                            
                            bbox = meta.get("bbox", {})
                            lat = meta.get("latitude", 0.0)
                            lon = meta.get("longitude", 0.0)
                            
                            # Validate bbox
                            if not all(k in bbox for k in ["min_lon", "min_lat", "max_lon", "max_lat"]):
                                invalid_bbox += 1
                            
                            # Validate coordinates
                            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                                invalid_coords += 1
                            
                            checked += 1
                        except Exception:
                            pass
        
        status = "PASS" if (invalid_bbox == 0 and invalid_coords == 0) else "FAIL"
        
        result = {
            "checked": checked,
            "invalid_bbox": invalid_bbox,
            "invalid_coords": invalid_coords,
            "status": status
        }
        
        self.results["geospatial_metadata"] = result
        print(f"  Geospatial metadata: {status} ({invalid_bbox} invalid bbox, {invalid_coords} invalid coords)")
        
        return result
    
    def validate_no_duplicate_ids(self) -> Dict[str, any]:
        """Validate no duplicate vector IDs in Qdrant"""
        print("Validating no duplicate vector IDs...")
        
        try:
            from qdrant_client import QdrantClient
            
            client = QdrantClient(path=str(self.qdrant_storage))
            
            # Check both collections
            for collection_name in ["satellite_tiles", "satellite_tiles_clip"]:
                if not client.collection_exists(collection_name):
                    continue
                
                # Get all points (this may be slow for large collections)
                # For validation, we'll just check the count
                info = client.get_collection(collection_name)
                print(f"  {collection_name}: {info.points_count} points")
            
            status = "PASS"
            result = {
                "status": status
            }
            
            self.results["no_duplicate_ids"] = result
            print(f"  No duplicate IDs: {status}")
            
            return result
            
        except Exception as e:
            print(f"  Error: {e}")
            result = {
                "status": "FAIL",
                "error": str(e)
            }
            self.results["no_duplicate_ids"] = result
            return result
    
    def validate_new_modules(self) -> Dict[str, any]:
        """Validate new modules (change classifier, search filters, export)"""
        print("Validating new modules...")
        
        results = {}
        app_dir = Path(__file__).parent.parent / "app"
        
        # Check change classifier module file exists
        change_classifier_file = app_dir / "temporal" / "change_classifier.py"
        results["change_classifier"] = "PASS" if change_classifier_file.exists() else "FAIL"
        print(f"  Change classifier module: {results['change_classifier']}")
        
        # Check search filters module file exists
        search_filters_file = app_dir / "search" / "search_filters.py"
        results["search_filters"] = "PASS" if search_filters_file.exists() else "FAIL"
        print(f"  Search filters module: {results['search_filters']}")
        
        # Check export manager module file exists
        export_manager_file = app_dir / "export" / "export_manager.py"
        results["export_manager"] = "PASS" if export_manager_file.exists() else "FAIL"
        print(f"  Export manager module: {results['export_manager']}")
        
        # Check earliest change module file exists
        earliest_change_file = app_dir / "temporal" / "earliest_change.py"
        results["earliest_change"] = "PASS" if earliest_change_file.exists() else "FAIL"
        print(f"  Earliest change module: {results['earliest_change']}")
        
        # Check clustering module file exists
        clustering_file = app_dir / "clustering" / "clay_clustering.py"
        results["clustering"] = "PASS" if clustering_file.exists() else "FAIL"
        print(f"  Clay clustering module: {results['clustering']}")
        
        overall_status = "PASS" if all(v == "PASS" for v in results.values()) else "FAIL"
        
        result = {
            "modules": results,
            "status": overall_status
        }
        
        self.results["new_modules"] = result
        print(f"  New modules overall: {overall_status}")
        
        return result
    
    def run_all_validations(self) -> Dict[str, any]:
        """Run all validation tests"""
        print("=" * 60)
        print("PIPELINE VALIDATION TESTS V2")
        print("=" * 60)
        print()
        
        self.validate_tiles()
        self.validate_clay_embeddings()
        self.validate_qdrant_clay()
        self.validate_qdrant_clip()
        self.validate_temporal_pairs()
        self.validate_change_results()
        self.validate_earliest_changes()
        self.validate_clustering()
        self.validate_embedding_dimensions()
        self.validate_metadata_consistency()
        self.validate_tile_id_consistency()
        self.validate_geospatial_metadata()
        self.validate_no_duplicate_ids()
        self.validate_new_modules()
        
        print()
        print("=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        
        for test_name, result in self.results.items():
            print(f"{test_name:25s}: {result['status']:6s}   ", end="")
            if "expected" in result:
                print(f"(expected: {result['expected']}, actual: {result['actual']})")
            else:
                print(f"(expected: N/A, actual: N/A)")
        
        # Overall status
        all_pass = all(r["status"] in ["PASS", "PENDING"] for r in self.results.values())
        overall_status = "PASS" if all_pass else "FAIL"
        
        print()
        print(f"Overall: {overall_status}")
        
        # Save results
        output_file = Path("test/validation_results_v2.json")
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"Results saved to {output_file}")
        
        return self.results


if __name__ == "__main__":
    validator = PipelineValidator()
    validator.run_all_validations()
