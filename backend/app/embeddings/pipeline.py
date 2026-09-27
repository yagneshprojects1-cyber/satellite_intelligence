import os
import json
import math
import time
import datetime
from pathlib import Path

import torch
import numpy as np
import rasterio
import yaml
from box import Box
from torchvision.transforms import v2

from app.embeddings.clay_embedder import Embedder

def normalize_timestamp(date_obj):
    week = date_obj.isocalendar().week * 2 * np.pi / 52
    hour = date_obj.hour * 2 * np.pi / 24
    return (math.sin(week), math.cos(week)), (math.sin(hour), math.cos(hour))

def normalize_latlon(lat, lon):
    lat = lat * np.pi / 180
    lon = lon * np.pi / 180
    return (math.sin(lat), math.cos(lat)), (math.sin(lon), math.cos(lon))

class Phase6Pipeline:
    def __init__(self, 
                 tiles_dir="data/tiles", 
                 embeddings_dir="embeddings", 
                 model_ckpt="models/clay/v1.5/clay-v1.5.ckpt",
                 metadata_yaml="clay-repo/configs/metadata.yaml",
                 batch_size=32,
                 limit=None,
                 resume=True):
        self.tiles_dir = Path(tiles_dir)
        self.embeddings_dir = Path(embeddings_dir)
        self.model_ckpt = Path(model_ckpt)
        self.metadata_yaml = Path(metadata_yaml)
        self.batch_size = batch_size
        self.limit = limit
        self.resume = resume  # Skip already-computed embeddings
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embedder = None
        self.transform = None
        self.waves = None
        
        # 10 bands strictly as requested
        self.expected_bands = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
        self.band_to_clay_name = {
            "B02": "blue", "B03": "green", "B04": "red", "B05": "rededge1",
            "B06": "rededge2", "B07": "rededge3", "B08": "nir", "B8A": "nir08",
            "B11": "swir16", "B12": "swir22"
        }

    def setup(self):
        if not self.model_ckpt.exists():
            raise FileNotFoundError(f"Clay checkpoint missing at {self.model_ckpt}")
        
        print(f"Loading Clay model from {self.model_ckpt} to {self.device}...", flush=True)
        self.embedder = Embedder(ckpt_path=self.model_ckpt, device=self.device)
        
        # Load metadata configuration
        with open(self.metadata_yaml, "r") as f:
            metadata_content = yaml.safe_load(f)
        
        metadata = Box(metadata_content)
        mean_vals = []
        std_vals = []
        waves = []
        
        for b in self.expected_bands:
            cname = self.band_to_clay_name[b]
            mean_vals.append(metadata["sentinel-2-l2a"].bands.mean[cname])
            std_vals.append(metadata["sentinel-2-l2a"].bands.std[cname])
            waves.append(metadata["sentinel-2-l2a"].bands.wavelength[cname])
            
        self.transform = v2.Compose([
            v2.Normalize(mean=mean_vals, std=std_vals),
        ])
        self.waves = torch.tensor(waves, dtype=torch.float32)

    def process_tiles(self):
        stats = {
            "total_valid_tiles": 0,
            "processed": 0,
            "skipped_existing": 0,
            "failed": 0,
            "processing_time": 0.0,
            "device": self.device,
            "failures": []
        }
        
        years = ["2022", "2023", "2024"]
        valid_tiles = []
        
        for year in years:
            year_dir = self.tiles_dir / year
            if not year_dir.exists():
                print(f"Warning: Year directory {year_dir} does not exist")
                continue
            for tile_dir in year_dir.iterdir():
                if tile_dir.is_dir() and (tile_dir / "metadata.json").exists():
                    valid_tiles.append(tile_dir)
                    
        stats["total_valid_tiles"] = len(valid_tiles)
        print(f"Discovered {len(valid_tiles)} valid tiles across years {years}")
        
        if self.limit:
            print(f"Limiting to first {self.limit} tiles")
            valid_tiles = valid_tiles[:self.limit]
            
        # Create output dirs
        for year in years:
            (self.embeddings_dir / year).mkdir(parents=True, exist_ok=True)
            
        start_time = time.time()
        
        batch = []
        for tile_dir in valid_tiles:
            try:
                with open(tile_dir / "metadata.json", "r") as f:
                    meta = json.load(f)
                    
                year = tile_dir.parent.name
                tile_id = meta["tile_id"]
                out_path = self.embeddings_dir / year / f"{tile_id}.npy"
                
                # Skip if embedding already exists and resume is enabled
                if self.resume and out_path.exists():
                    stats["skipped_existing"] += 1
                    continue
                    
                # Read 10 bands
                pixels = []
                for b in self.expected_bands:
                    b_path = tile_dir / f"{b}.tif"
                    with rasterio.open(b_path) as src:
                        pixels.append(src.read(1))
                
                pixels = np.stack(pixels, axis=0) # [10, 256, 256]
                
                # Parse date
                date_str = meta["date"]
                # time usually 00:00:00 if not provided, check source_scene for hour?
                # e.g., S2A_MSIL2A_20221227T052231_N0510_R062_T43QFV_20240807T043638
                hour = 12
                if "source_scene" in meta and "T" in meta["source_scene"]:
                    time_part = meta["source_scene"].split("_")[2] # 20221227T052231
                    if "T" in time_part:
                        hour_str = time_part.split("T")[1][:2]
                        hour = int(hour_str)
                        
                date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(hour=hour)
                t_norm = normalize_timestamp(date_obj)
                week_norm, hour_norm = t_norm[0], t_norm[1]
                
                l_norm = normalize_latlon(meta["latitude"], meta["longitude"])
                lat_norm, lon_norm = l_norm[0], l_norm[1]
                
                item = {
                    "pixels": pixels,
                    "time": np.hstack((week_norm, hour_norm)),
                    "latlon": np.hstack((lat_norm, lon_norm)),
                    "gsd": [10.0],
                    "meta": meta,
                    "out_path": out_path,
                    "year": year
                }
                batch.append(item)
                
                if len(batch) >= self.batch_size:
                    self._process_batch(batch, stats)
                    batch = []
                    
            except Exception as e:
                print(f"Error processing {tile_dir}: {e}")
                stats["failed"] += 1
                stats["failures"].append({
                    "tile_id": tile_dir.name if hasattr(tile_dir, 'name') else str(tile_dir),
                    "error": str(e)
                })
                
        if len(batch) > 0:
            self._process_batch(batch, stats)
            
        stats["processing_time"] = time.time() - start_time
        if stats["processed"] > 0:
            stats["tiles_sec"] = stats["processed"] / stats["processing_time"]
            
        print("Phase 6 finished.")
        print(stats)
        
        with open(self.embeddings_dir / "embedding_summary.json", "w") as f:
            json.dump(stats, f, indent=2)
            
        return stats
        
    def _process_batch(self, batch, stats):
        # Prepare tensors
        b_pixels = torch.tensor(np.stack([item["pixels"] for item in batch]), dtype=torch.float32)
        b_time = torch.tensor(np.stack([item["time"] for item in batch]), dtype=torch.float32)
        b_latlon = torch.tensor(np.stack([item["latlon"] for item in batch]), dtype=torch.float32)
        b_gsd = torch.tensor([10.0], dtype=torch.float32)
        b_waves = self.waves
        
        # Normalize
        b_pixels = self.transform(b_pixels)
        
        datacube = {
            "pixels": b_pixels.to(self.device),
            "time": b_time.to(self.device),
            "latlon": b_latlon.to(self.device),
            "gsd": b_gsd.to(self.device),
            "waves": b_waves.to(self.device)
        }
        
        with torch.no_grad():
            embeddings = self.embedder(datacube).cpu().numpy()
            
        # Verify shape
        assert embeddings.shape[1] == 1024, f"Expected 1024-D, got {embeddings.shape[1]}"
        
        for i, item in enumerate(batch):
            emb = embeddings[i]
            np.save(item["out_path"], emb)
            
            # Save metadata/index
            meta = item["meta"]
            index_path = item["out_path"].with_suffix(".json")
            index_data = {
                "tile_id": meta["tile_id"],
                "year": item["year"],
                "date": meta["date"],
                "latitude": meta["latitude"],
                "longitude": meta["longitude"],
                "bbox": meta["bbox"],
                "sensor": meta["sensor"],
                "source_scene": meta.get("source_scene", ""),
                "embedding_path": str(item["out_path"]),
                "embedding_dimension": 1024,
                "model_name": "Clay Foundation Model",
                "model_version": "v1.5",
                "checkpoint_reference": str(self.model_ckpt),
                "processing_version": "1.0",
                "valid_percentage": meta.get("valid_percentage", 100.0)
            }
            with open(index_path, "w") as f:
                json.dump(index_data, f, indent=2)
                
            stats["processed"] += 1
            
        print("\n" + "=" * 60)
        print("PHASE 6: CLAY EMBEDDING GENERATION COMPLETE")
        print("=" * 60)
        print(f"Total valid tiles: {stats['total_valid_tiles']}")
        print(f"Processed: {stats['processed']}")
        print(f"Skipped (existing): {stats['skipped_existing']}")
        print(f"Failed: {stats['failed']}")
        print(f"Processing time: {stats['processing_time']:.2f}s")
        if stats['processed'] > 0:
            print(f"Throughput: {stats['tiles_sec']:.2f} tiles/sec")
        if stats['failures'] > 0:
            print(f"\nFailures:")
            for failure in stats['failures'][:10]:  # Show first 10 failures
                print(f"  - {failure['tile_id']}: {failure['error']}")
            if len(stats['failures']) > 10:
                print(f"  ... and {len(stats['failures']) - 10} more")
        print("=" * 60)
            
        return stats


def main():
    """Main entry point for Phase 6 pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 6: Clay Embedding Generation")
    parser.add_argument("--tiles-dir", type=str, default="data/tiles", help="Directory containing tiles")
    parser.add_argument("--embeddings-dir", type=str, default="embeddings", help="Output directory for embeddings")
    parser.add_argument("--model-ckpt", type=str, default="models/clay/v1.5/clay-v1.5.ckpt", help="Clay model checkpoint")
    parser.add_argument("--metadata-yaml", type=str, default="clay-repo/configs/metadata.yaml", help="Clay metadata config")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for processing")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tiles to process")
    parser.add_argument("--no-resume", action="store_true", help="Do not skip existing embeddings")
    
    args = parser.parse_args()
    
    pipeline = Phase6Pipeline(
        tiles_dir=args.tiles_dir,
        embeddings_dir=args.embeddings_dir,
        model_ckpt=args.model_ckpt,
        metadata_yaml=args.metadata_yaml,
        batch_size=args.batch_size,
        limit=args.limit,
        resume=not args.no_resume
    )
    
    pipeline.setup()
    stats = pipeline.process_tiles()
    
    return 0 if stats['failed'] == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
