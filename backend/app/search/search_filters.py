"""
Search Filters Module
Provides advanced filtering capabilities for satellite imagery search
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range


class SearchFilters:
    """
    Advanced search filters for satellite imagery.
    
    Supports filtering by:
    - Year
    - Date range
    - Latitude/longitude
    - Bounding box
    - Sensor
    - Minimum similarity
    - Valid percentage
    """
    
    @staticmethod
    def build_qdrant_filter(filters: Dict[str, Any]) -> Optional[Filter]:
        """
        Build Qdrant filter from filter dictionary.
        
        Args:
            filters: Dictionary of filter conditions
            
        Returns:
            Qdrant Filter object or None if no filters
        """
        if not filters:
            return None
        
        must_conditions = []
        
        # Year filter
        if 'year' in filters:
            must_conditions.append(
                FieldCondition(key='year', match=MatchValue(value=str(filters['year'])))
            )
        
        # Sensor filter
        if 'sensor' in filters:
            must_conditions.append(
                FieldCondition(key='sensor', match=MatchValue(value=filters['sensor']))
            )
        
        # Minimum valid percentage filter
        if 'min_valid_percentage' in filters:
            # Note: Qdrant local doesn't support numeric range filters on payload
            # This would require server mode. For now, we'll apply this post-search
            pass
        
        # Date range filter
        if 'date_start' in filters or 'date_end' in filters:
            # Date filtering would require server mode with payload indexes
            # For now, we'll apply this post-search
            pass
        
        # Bounding box filter
        if 'bbox' in filters:
            # Spatial filtering would require PostGIS or geospatial queries
            # For now, we'll apply this post-search
            pass
        
        # Latitude/longitude range filter
        if 'lat_min' in filters or 'lat_max' in filters or 'lon_min' in filters or 'lon_max' in filters:
            # Numeric range filtering requires server mode
            # For now, we'll apply this post-search
            pass
        
        if must_conditions:
            return Filter(must=must_conditions)
        
        return None
    
    @staticmethod
    def apply_post_search_filters(results: List[Dict[str, Any]], 
                                 filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply filters that cannot be expressed in Qdrant query (post-search filtering).
        
        Args:
            results: List of search results
            filters: Dictionary of filter conditions
            
        Returns:
            Filtered list of results
        """
        if not results or not filters:
            return results
        
        filtered_results = []
        
        for result in results:
            # Apply minimum similarity filter
            if 'min_similarity' in filters:
                if result.get('similarity', 0.0) < filters['min_similarity']:
                    continue
            
            # Apply minimum valid percentage filter
            if 'min_valid_percentage' in filters:
                if result.get('valid_percentage', 0.0) < filters['min_valid_percentage']:
                    continue
            
            # Apply date range filter
            if 'date_start' in filters or 'date_end' in filters:
                result_date = result.get('date', '')
                if result_date:
                    try:
                        result_dt = datetime.strptime(result_date, '%Y-%m-%d')
                        
                        if 'date_start' in filters:
                            start_dt = datetime.strptime(filters['date_start'], '%Y-%m-%d')
                            if result_dt < start_dt:
                                continue
                        
                        if 'date_end' in filters:
                            end_dt = datetime.strptime(filters['date_end'], '%Y-%m-%d')
                            if result_dt > end_dt:
                                continue
                    except ValueError:
                        # Skip if date parsing fails
                        continue
            
            # Apply latitude range filter
            if 'lat_min' in filters or 'lat_max' in filters:
                lat = result.get('latitude', 0.0)
                
                if 'lat_min' in filters and lat < filters['lat_min']:
                    continue
                if 'lat_max' in filters and lat > filters['lat_max']:
                    continue
            
            # Apply longitude range filter
            if 'lon_min' in filters or 'lon_max' in filters:
                lon = result.get('longitude', 0.0)
                
                if 'lon_min' in filters and lon < filters['lon_min']:
                    continue
                if 'lon_max' in filters and lon > filters['lon_max']:
                    continue
            
            # Apply bounding box filter
            if 'bbox' in filters:
                bbox = filters['bbox']
                result_bbox = result.get('bbox', {})
                
                # Check if result bbox intersects with filter bbox
                if not SearchFilters._bbox_intersects(result_bbox, bbox):
                    continue
            
            filtered_results.append(result)
        
        return filtered_results
    
    @staticmethod
    def _bbox_intersects(bbox1: Dict[str, float], bbox2: Dict[str, float]) -> bool:
        """
        Check if two bounding boxes intersect.
        
        Args:
            bbox1: First bounding box {min_lon, min_lat, max_lon, max_lat}
            bbox2: Second bounding box {min_lon, min_lat, max_lon, max_lat}
            
        Returns:
            True if boxes intersect
        """
        # Calculate intersection
        inter_min_lon = max(bbox1.get('min_lon', -180), bbox2.get('min_lon', -180))
        inter_min_lat = max(bbox1.get('min_lat', -90), bbox2.get('min_lat', -90))
        inter_max_lon = min(bbox1.get('max_lon', 180), bbox2.get('max_lon', 180))
        inter_max_lat = min(bbox1.get('max_lat', 90), bbox2.get('max_lat', 90))
        
        # Check if boxes overlap
        if inter_min_lon >= inter_max_lon or inter_min_lat >= inter_max_lat:
            return False
        
        return True
    
    @staticmethod
    def create_filter_examples() -> Dict[str, Dict[str, Any]]:
        """
        Create example filter configurations.
        
        Returns:
            Dictionary of example filters
        """
        return {
            "year_2022": {
                "year": 2022
            },
            "date_range_2023": {
                "date_start": "2023-01-01",
                "date_end": "2023-12-31"
            },
            "high_quality": {
                "min_valid_percentage": 80.0
            },
            "high_similarity": {
                "min_similarity": 0.8
            },
            "geographic_region": {
                "lat_min": 17.0,
                "lat_max": 19.0,
                "lon_min": 75.0,
                "lon_max": 77.0
            },
            "combined": {
                "year": 2024,
                "min_valid_percentage": 70.0,
                "min_similarity": 0.7,
                "lat_min": 17.5,
                "lat_max": 18.5,
                "lon_min": 75.5,
                "lon_max": 76.5
            }
        }
    
    @staticmethod
    def validate_filters(filters: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate filter configuration.
        
        Args:
            filters: Dictionary of filter conditions
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Validate year
        if 'year' in filters:
            year = filters['year']
            if not isinstance(year, int) or year < 2000 or year > 2100:
                errors.append(f"Invalid year: {year}")
        
        # Validate date range
        if 'date_start' in filters:
            try:
                datetime.strptime(filters['date_start'], '%Y-%m-%d')
            except ValueError:
                errors.append(f"Invalid date_start format: {filters['date_start']}")
        
        if 'date_end' in filters:
            try:
                datetime.strptime(filters['date_end'], '%Y-%m-%d')
            except ValueError:
                errors.append(f"Invalid date_end format: {filters['date_end']}")
        
        if 'date_start' in filters and 'date_end' in filters:
            start_dt = datetime.strptime(filters['date_start'], '%Y-%m-%d')
            end_dt = datetime.strptime(filters['date_end'], '%Y-%m-%d')
            if start_dt > end_dt:
                errors.append("date_start must be before date_end")
        
        # Validate valid percentage
        if 'min_valid_percentage' in filters:
            pct = filters['min_valid_percentage']
            if not isinstance(pct, (int, float)) or pct < 0 or pct > 100:
                errors.append(f"Invalid min_valid_percentage: {pct}")
        
        # Validate similarity
        if 'min_similarity' in filters:
            sim = filters['min_similarity']
            if not isinstance(sim, (int, float)) or sim < 0 or sim > 1:
                errors.append(f"Invalid min_similarity: {sim}")
        
        # Validate latitude range
        if 'lat_min' in filters:
            lat_min = filters['lat_min']
            if not isinstance(lat_min, (int, float)) or lat_min < -90 or lat_min > 90:
                errors.append(f"Invalid lat_min: {lat_min}")
        
        if 'lat_max' in filters:
            lat_max = filters['lat_max']
            if not isinstance(lat_max, (int, float)) or lat_max < -90 or lat_max > 90:
                errors.append(f"Invalid lat_max: {lat_max}")
        
        if 'lat_min' in filters and 'lat_max' in filters:
            if filters['lat_min'] > filters['lat_max']:
                errors.append("lat_min must be less than lat_max")
        
        # Validate longitude range
        if 'lon_min' in filters:
            lon_min = filters['lon_min']
            if not isinstance(lon_min, (int, float)) or lon_min < -180 or lon_min > 180:
                errors.append(f"Invalid lon_min: {lon_min}")
        
        if 'lon_max' in filters:
            lon_max = filters['lon_max']
            if not isinstance(lon_max, (int, float)) or lon_max < -180 or lon_max > 180:
                errors.append(f"Invalid lon_max: {lon_max}")
        
        if 'lon_min' in filters and 'lon_max' in filters:
            if filters['lon_min'] > filters['lon_max']:
                errors.append("lon_min must be less than lon_max")
        
        # Validate bounding box
        if 'bbox' in filters:
            bbox = filters['bbox']
            required_keys = ['min_lon', 'min_lat', 'max_lon', 'max_lat']
            for key in required_keys:
                if key not in bbox:
                    errors.append(f"Missing bbox key: {key}")
            
            if 'min_lon' in bbox and 'max_lon' in bbox:
                if bbox['min_lon'] >= bbox['max_lon']:
                    errors.append("bbox min_lon must be less than max_lon")
            
            if 'min_lat' in bbox and 'max_lat' in bbox:
                if bbox['min_lat'] >= bbox['max_lat']:
                    errors.append("bbox min_lat must be less than max_lat")
        
        return len(errors) == 0, errors
