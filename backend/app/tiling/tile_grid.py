import math
from typing import Dict, List, Tuple
from rasterio.transform import Affine

class TileGrid:
    """
    Manages the creation of a standard geospatial grid to ensure temporal consistency
    across different scenes/years.
    """

    def __init__(self, crs: str, transform: Affine, width: int, height: int, tile_size: int = 256):
        """
        Initialize the master grid based on a reference scene (e.g., 2022).
        
        Args:
            crs: Coordinate Reference System string (e.g., EPSG:32643)
            transform: Rasterio Affine transform from the reference scene
            width: Width of the reference scene in pixels
            height: Height of the reference scene in pixels
            tile_size: Desired tile dimension (width & height)
        """
        self.crs = crs
        self.transform = transform
        self.scene_width = width
        self.scene_height = height
        self.tile_size = tile_size

        self.tiles = self._generate_grid()

    def _generate_grid(self) -> List[Dict]:
        """
        Generate bounding boxes for all tiles in the reference grid.
        
        Returns:
            List of dictionaries containing tile metadata and bounds.
        """
        tiles = []
        cols = math.ceil(self.scene_width / self.tile_size)
        rows = math.ceil(self.scene_height / self.tile_size)
        
        tile_id_counter = 1

        for row in range(rows):
            for col in range(cols):
                # Calculate pixel windows
                col_off = col * self.tile_size
                row_off = row * self.tile_size
                
                # Get exact coordinates for the bounding box
                # top-left
                min_x, max_y = self.transform * (col_off, row_off)
                # bottom-right
                max_x, min_y = self.transform * (col_off + self.tile_size, row_off + self.tile_size)

                # Format deterministic tile ID e.g., 000001
                tile_str = f"{tile_id_counter:06d}"
                
                tiles.append({
                    "grid_id": tile_str,
                    "col_off": col_off,
                    "row_off": row_off,
                    "width": self.tile_size,
                    "height": self.tile_size,
                    "bounds": {
                        "left": min_x,
                        "bottom": min_y,
                        "right": max_x,
                        "top": max_y
                    }
                })
                
                tile_id_counter += 1

        return tiles
