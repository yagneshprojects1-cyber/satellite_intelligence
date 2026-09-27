"""
Export Manager Module
Provides CSV and JSON export functionality with provenance tracking
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class ExportResult:
    """Data class for export operation result"""
    export_type: str  # "search_results", "change_results", "tiles", "clusters"
    format: str  # "csv" or "json"
    file_path: str
    record_count: int
    export_time: str
    status: str  # "success" or "failed"
    error_message: Optional[str] = None


class ExportManager:
    """
    Export manager for satellite intelligence results.
    
    Supports export of:
    - Search results (CLIP/Clay similarity search)
    - Change detection results
    - Tile metadata
    - Cluster assignments
    
    All exports include provenance information:
    - tile_id
    - source_scene
    - date
    - location (latitude, longitude, bbox)
    - sensor
    - model/model_version
    - processing_time
    - confidence
    - result
    """
    
    def __init__(self, output_dir: Path = Path("data/exports")):
        """
        Initialize export manager.
        
        Args:
            output_dir: Directory for export files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_search_results(self, 
                             results: List[Dict[str, Any]],
                             format: str = "csv",
                             filename: Optional[str] = None) -> ExportResult:
        """
        Export search results with provenance.
        
        Args:
            results: List of search results
            format: Export format ("csv" or "json")
            filename: Optional custom filename
            
        Returns:
            ExportResult
        """
        export_time = datetime.utcnow().isoformat()
        
        if not results:
            return ExportResult(
                export_type="search_results",
                format=format,
                file_path="",
                record_count=0,
                export_time=export_time,
                status="failed",
                error_message="No results to export"
            )
        
        # Prepare data with provenance
        export_data = []
        for result in results:
            record = {
                "tile_id": result.get("tile_id", ""),
                "rank": result.get("rank", 0),
                "similarity": result.get("similarity", 0.0),
                "date": result.get("date", ""),
                "latitude": result.get("latitude", 0.0),
                "longitude": result.get("longitude", 0.0),
                "bbox_min_lon": result.get("bbox", {}).get("min_lon", 0.0),
                "bbox_min_lat": result.get("bbox", {}).get("min_lat", 0.0),
                "bbox_max_lon": result.get("bbox", {}).get("max_lon", 0.0),
                "bbox_max_lat": result.get("bbox", {}).get("max_lat", 0.0),
                "sensor": result.get("sensor", ""),
                "source_scene": result.get("source_scene", ""),
                "valid_percentage": result.get("valid_percentage", 0.0),
                "tile_path": result.get("tile_path", ""),
                "embedding_model": result.get("embedding_model", ""),
                "embedding_type": result.get("embedding_type", ""),
                "export_time": export_time
            }
            export_data.append(record)
        
        # Generate filename
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"search_results_{timestamp}.{format}"
        
        file_path = self.output_dir / filename
        
        try:
            if format == "csv":
                self._write_csv(export_data, file_path)
            elif format == "json":
                self._write_json(export_data, file_path)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            return ExportResult(
                export_type="search_results",
                format=format,
                file_path=str(file_path),
                record_count=len(export_data),
                export_time=export_time,
                status="success"
            )
        except Exception as e:
            return ExportResult(
                export_type="search_results",
                format=format,
                file_path="",
                record_count=0,
                export_time=export_time,
                status="failed",
                error_message=str(e)
            )
    
    def export_change_results(self,
                             results: List[Dict[str, Any]],
                             format: str = "csv",
                             filename: Optional[str] = None) -> ExportResult:
        """
        Export change detection results with provenance.
        
        Args:
            results: List of change detection results
            format: Export format ("csv" or "json")
            filename: Optional custom filename
            
        Returns:
            ExportResult
        """
        export_time = datetime.utcnow().isoformat()
        
        if not results:
            return ExportResult(
                export_type="change_results",
                format=format,
                file_path="",
                record_count=0,
                export_time=export_time,
                status="failed",
                error_message="No results to export"
            )
        
        # Prepare data with provenance
        export_data = []
        for result in results:
            record = {
                "pair_id": result.get("pair_id", ""),
                "before_date": result.get("before_date", ""),
                "after_date": result.get("after_date", ""),
                "bbox_min_lon": result.get("bbox", {}).get("min_lon", 0.0),
                "bbox_min_lat": result.get("bbox", {}).get("min_lat", 0.0),
                "bbox_max_lon": result.get("bbox", {}).get("max_lon", 0.0),
                "bbox_max_lat": result.get("bbox", {}).get("max_lat", 0.0),
                "change_mask_path": result.get("change_mask_path", ""),
                "change_percentage": result.get("change_percentage", 0.0),
                "confidence": result.get("confidence", 0.0),
                "model_used": result.get("model_used", ""),
                "processing_time": result.get("processing_time", 0.0),
                "change_type": result.get("change_type", ""),
                "before_path": result.get("before_path", ""),
                "after_path": result.get("after_path", ""),
                "crs": result.get("crs", ""),
                "resolution": result.get("resolution", 0.0),
                "width": result.get("width", 0),
                "height": result.get("height", 0),
                "export_time": export_time
            }
            export_data.append(record)
        
        # Generate filename
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"change_results_{timestamp}.{format}"
        
        file_path = self.output_dir / filename
        
        try:
            if format == "csv":
                self._write_csv(export_data, file_path)
            elif format == "json":
                self._write_json(export_data, file_path)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            return ExportResult(
                export_type="change_results",
                format=format,
                file_path=str(file_path),
                record_count=len(export_data),
                export_time=export_time,
                status="success"
            )
        except Exception as e:
            return ExportResult(
                export_type="change_results",
                format=format,
                file_path="",
                record_count=0,
                export_time=export_time,
                status="failed",
                error_message=str(e)
            )
    
    def export_earliest_changes(self,
                                results: List[Dict[str, Any]],
                                format: str = "csv",
                                filename: Optional[str] = None) -> ExportResult:
        """
        Export earliest change results with provenance.
        
        Args:
            results: List of earliest change results
            format: Export format ("csv" or "json")
            filename: Optional custom filename
            
        Returns:
            ExportResult
        """
        export_time = datetime.utcnow().isoformat()
        
        if not results:
            return ExportResult(
                export_type="earliest_changes",
                format=format,
                file_path="",
                record_count=0,
                export_time=export_time,
                status="failed",
                error_message="No results to export"
            )
        
        # Prepare data with provenance
        export_data = []
        for result in results:
            record = {
                "location_reference": result.get("location_reference", ""),
                "earliest_change_date": result.get("earliest_change_date", ""),
                "before_date": result.get("before_date", ""),
                "after_date": result.get("after_date", ""),
                "confidence": result.get("confidence", 0.0),
                "change_percentage": result.get("change_percentage", 0.0),
                "persistence": result.get("persistence", ""),
                "evidence_pairs": json.dumps(result.get("evidence_pairs", [])),
                "created_at": result.get("created_at", ""),
                "export_time": export_time
            }
            export_data.append(record)
        
        # Generate filename
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"earliest_changes_{timestamp}.{format}"
        
        file_path = self.output_dir / filename
        
        try:
            if format == "csv":
                self._write_csv(export_data, file_path)
            elif format == "json":
                self._write_json(export_data, file_path)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            return ExportResult(
                export_type="earliest_changes",
                format=format,
                file_path=str(file_path),
                record_count=len(export_data),
                export_time=export_time,
                status="success"
            )
        except Exception as e:
            return ExportResult(
                export_type="earliest_changes",
                format=format,
                file_path="",
                record_count=0,
                export_time=export_time,
                status="failed",
                error_message=str(e)
            )
    
    def export_tile_metadata(self,
                           tiles: List[Dict[str, Any]],
                           format: str = "csv",
                           filename: Optional[str] = None) -> ExportResult:
        """
        Export tile metadata with provenance.
        
        Args:
            tiles: List of tile metadata
            format: Export format ("csv" or "json")
            filename: Optional custom filename
            
        Returns:
            ExportResult
        """
        export_time = datetime.utcnow().isoformat()
        
        if not tiles:
            return ExportResult(
                export_type="tiles",
                format=format,
                file_path="",
                record_count=0,
                export_time=export_time,
                status="failed",
                error_message="No tiles to export"
            )
        
        # Prepare data with provenance
        export_data = []
        for tile in tiles:
            record = {
                "tile_id": tile.get("tile_id", ""),
                "year": tile.get("year", ""),
                "date": tile.get("date", ""),
                "latitude": tile.get("latitude", 0.0),
                "longitude": tile.get("longitude", 0.0),
                "bbox_min_lon": tile.get("bbox", {}).get("min_lon", 0.0),
                "bbox_min_lat": tile.get("bbox", {}).get("min_lat", 0.0),
                "bbox_max_lon": tile.get("bbox", {}).get("max_lon", 0.0),
                "bbox_max_lat": tile.get("bbox", {}).get("max_lat", 0.0),
                "sensor": tile.get("sensor", ""),
                "source_scene": tile.get("source_scene", ""),
                "valid_percentage": tile.get("valid_percentage", 0.0),
                "crs": tile.get("crs", ""),
                "resolution": tile.get("resolution", 0.0),
                "width": tile.get("width", 0),
                "height": tile.get("height", 0),
                "export_time": export_time
            }
            export_data.append(record)
        
        # Generate filename
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"tile_metadata_{timestamp}.{format}"
        
        file_path = self.output_dir / filename
        
        try:
            if format == "csv":
                self._write_csv(export_data, file_path)
            elif format == "json":
                self._write_json(export_data, file_path)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            return ExportResult(
                export_type="tiles",
                format=format,
                file_path=str(file_path),
                record_count=len(export_data),
                export_time=export_time,
                status="success"
            )
        except Exception as e:
            return ExportResult(
                export_type="tiles",
                format=format,
                file_path="",
                record_count=0,
                export_time=export_time,
                status="failed",
                error_message=str(e)
            )
    
    def _write_csv(self, data: List[Dict[str, Any]], file_path: Path):
        """
        Write data to CSV file.
        
        Args:
            data: List of dictionaries
            file_path: Output file path
        """
        if not data:
            raise ValueError("No data to write")
        
        fieldnames = list(data[0].keys())
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    
    def _write_json(self, data: List[Dict[str, Any]], file_path: Path):
        """
        Write data to JSON file.
        
        Args:
            data: List of dictionaries
            file_path: Output file path
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def get_export_history(self) -> List[Dict[str, Any]]:
        """
        Get list of all export files in the output directory.
        
        Returns:
            List of export file information
        """
        history = []
        
        for file_path in self.output_dir.glob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                history.append({
                    "filename": file_path.name,
                    "format": file_path.suffix[1:],  # Remove leading dot
                    "size_bytes": stat.st_size,
                    "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # Sort by modified time (newest first)
        history.sort(key=lambda x: x["modified_time"], reverse=True)
        
        return history
