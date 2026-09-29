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
        if 'year' in filters and filters['year']:
            must_conditions.append(
                FieldCondition(key='year', match=MatchValue(value=str(filters['year'])))
            )
        
        # Sensor filter
        if 'sensor' in filters and filters['sensor']:
            s_val = "Sentinel-2" if "sentinel" in str(filters['sensor']).lower() else str(filters['sensor'])
            must_conditions.append(
                FieldCondition(key='sensor', match=MatchValue(value=s_val))
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
            # Apply Year filter
            if 'year' in filters and filters['year']:
                y_str = str(filters['year']).strip()
                res_year = str(result.get('year') or result.get('date', '')[:4] or result.get('tile_id', '')[:4])
                if y_str not in res_year:
                    continue
                    
            # Apply Sensor filter
            if 'sensor' in filters and filters['sensor']:
                s_str = str(filters['sensor']).strip().lower()
                res_sensor = str(result.get('sensor', '')).strip().lower()
                if s_str not in res_sensor and res_sensor not in s_str:
                    continue

            # Apply minimum similarity filter
            if 'min_similarity' in filters and filters['min_similarity'] is not None:
                if result.get('similarity', 0.0) < float(filters['min_similarity']):
                    continue
            
            # Apply minimum valid percentage filter
            if 'min_valid_percentage' in filters and filters['min_valid_percentage'] is not None:
                if float(result.get('valid_percentage', 0.0)) < float(filters['min_valid_percentage']):
                    continue
            
            # Apply date range filter (supports date_start/date_end or date_range dict)
            d_start = filters.get('date_start') or (filters.get('date_range', {}).get('start') if isinstance(filters.get('date_range'), dict) else None)
            d_end = filters.get('date_end') or (filters.get('date_range', {}).get('end') if isinstance(filters.get('date_range'), dict) else None)
            
            if d_start or d_end:
                result_date = result.get('date', '')
                if result_date:
                    try:
                        result_dt = datetime.strptime(result_date, '%Y-%m-%d')
                        if d_start and d_start.strip():
                            start_dt = datetime.strptime(d_start.strip(), '%Y-%m-%d')
                            if result_dt < start_dt:
                                continue
                        if d_end and d_end.strip():
                            end_dt = datetime.strptime(d_end.strip(), '%Y-%m-%d')
                            if result_dt > end_dt:
                                continue
                    except Exception:
                        pass
            
            # Apply latitude/longitude & bounding box filters
            lat = float(result.get('latitude', 0.0))
            lon = float(result.get('longitude', 0.0))
            
            min_lat = filters.get('lat_min') or (filters.get('bbox', {}).get('min_lat') if isinstance(filters.get('bbox'), dict) else None)
            max_lat = filters.get('lat_max') or (filters.get('bbox', {}).get('max_lat') if isinstance(filters.get('bbox'), dict) else None)
            min_lon = filters.get('lon_min') or (filters.get('bbox', {}).get('min_lon') if isinstance(filters.get('bbox'), dict) else None)
            max_lon = filters.get('lon_max') or (filters.get('bbox', {}).get('max_lon') if isinstance(filters.get('bbox'), dict) else None)
            
            if min_lat is not None and lat < float(min_lat):
                continue
            if max_lat is not None and lat > float(max_lat):
                continue
            if min_lon is not None and lon < float(min_lon):
                continue
            if max_lon is not None and lon > float(max_lon):
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
        Validate filter configuration gracefully supporting string and float formats.
        
        Args:
            filters: Dictionary of filter conditions
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        if not filters:
            return True, []
            
        # Clean empty string filters
        cleaned_filters = {k: v for k, v in filters.items() if v is not None and v != ''}
        
        # Validate year
        if 'year' in cleaned_filters:
            year_val = cleaned_filters['year']
            try:
                year_int = int(year_val)
                if year_int < 2000 or year_int > 2100:
                    errors.append(f"Invalid year: {year_val}")
            except (ValueError, TypeError):
                errors.append(f"Invalid year format: {year_val}")
        
        # Validate date range
        d_start = cleaned_filters.get('date_start') or (cleaned_filters.get('date_range', {}).get('start') if isinstance(cleaned_filters.get('date_range'), dict) else None)
        d_end = cleaned_filters.get('date_end') or (cleaned_filters.get('date_range', {}).get('end') if isinstance(cleaned_filters.get('date_range'), dict) else None)
        
        if d_start and str(d_start).strip():
            try:
                datetime.strptime(str(d_start).strip(), '%Y-%m-%d')
            except ValueError:
                errors.append(f"Invalid date_start format: {d_start}")
        
        if d_end and str(d_end).strip():
            try:
                datetime.strptime(str(d_end).strip(), '%Y-%m-%d')
            except ValueError:
                errors.append(f"Invalid date_end format: {d_end}")
        
        # Validate valid percentage
        if 'min_valid_percentage' in cleaned_filters:
            try:
                pct = float(cleaned_filters['min_valid_percentage'])
                if pct < 0 or pct > 100:
                    errors.append(f"Invalid min_valid_percentage: {pct}")
            except (ValueError, TypeError):
                errors.append(f"Invalid min_valid_percentage format: {cleaned_filters['min_valid_percentage']}")
        
        return len(errors) == 0, errors
        
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
