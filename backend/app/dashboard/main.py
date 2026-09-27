"""
Phase 15 - Streamlit Analyst Dashboard
Main dashboard application
"""

import sys
import os
from pathlib import Path

# Add the backend directory to sys.path so it can find the 'app' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import streamlit as st
import json
import rasterio
from PIL import Image
import numpy as np
import folium
from streamlit_folium import st_folium

# Import dashboard services
from app.dashboard.services import (
    SemanticSearchService,
    ImageSearchService,
    ChangeAnalysisService,
    EarliestChangeService,
    SimilarLocationsService,
    AnalystReviewService,
    MapDataService
)

# Page configuration
st.set_page_config(
    page_title="Satellite Intelligence",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize services
@st.cache_resource
def get_services():
    """Initialize and cache dashboard services"""
    return {
        'semantic_search': SemanticSearchService(),
        'image_search': ImageSearchService(),
        'change_analysis': ChangeAnalysisService(),
        'earliest_change': EarliestChangeService(),
        'similar_locations': SimilarLocationsService(),
        'analyst_review': AnalystReviewService(),
        'map_data': MapDataService()
    }

try:
    services = get_services()
except Exception as e:
    st.error(f"Failed to initialize services: {e}")
    st.stop()

# Sidebar navigation
st.sidebar.title("Satellite Intelligence")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["Semantic Search", "Image Search", "Change Analysis", "Earliest Change", "Similar Locations", "Map", "Analyst Review"],
    index=0
)

# Main title
st.markdown('<h1 class="main-title">🛰️ Satellite Intelligence</h1>', unsafe_allow_html=True)
st.markdown("---")

# Helper function to load tile image
def load_tile_image(tile_path: str) -> Image.Image:
    """Load tile image from path"""
    try:
        # If tile_path is a directory, construct RGB from bands
        tile_dir = Path(tile_path)
        if tile_dir.is_dir():
            # Load individual bands and create RGB
            red_path = tile_dir / "B04.tif"
            green_path = tile_dir / "B03.tif"
            blue_path = tile_dir / "B02.tif"
            
            if not all(p.exists() for p in [red_path, green_path, blue_path]):
                print(f"Missing RGB bands in {tile_dir}")
                return None
            
            # Read bands with rasterio
            with rasterio.open(red_path) as src:
                red = src.read(1)
            
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
            return Image.fromarray(rgb)
        else:
            # It's a file path
            if tile_path.endswith('.tif') or tile_path.endswith('.tiff'):
                with rasterio.open(tile_path) as src:
                    # Check number of bands
                    if src.count == 1:
                        # Single-band image (e.g., change mask)
                        img_data = src.read(1)
                        # Normalize to 0-255
                        img_data = ((img_data - img_data.min()) / (img_data.max() - img_data.min()) * 255).astype(np.uint8)
                        # Convert to grayscale RGB
                        img_data = np.stack([img_data, img_data, img_data], axis=-1)
                        return Image.fromarray(img_data)
                    else:
                        # Multi-band image
                        img_data = src.read([1, 2, 3])
                        img_data = np.transpose(img_data, (1, 2, 0))
                        img_data = ((img_data - img_data.min()) / (img_data.max() - img_data.min()) * 255).astype(np.uint8)
                        return Image.fromarray(img_data)
            else:
                return Image.open(tile_path)
    except Exception as e:
        st.error(f"Error loading image: {e}")
        return None

# Page: Semantic Search
if page == "Semantic Search":
    st.markdown('<h2 class="section-header">🔍 Semantic Search</h2>', unsafe_allow_html=True)
    
    st.markdown("Search satellite imagery using natural language queries.")
    
    # Query input
    query = st.text_input("Enter your query:", placeholder="e.g., areas with water bodies")
    top_k = st.slider("Number of results:", min_value=1, max_value=20, value=10)
    
    if st.button("Search") and query:
        with st.spinner("Searching..."):
            try:
                results = services['semantic_search'].search(query, top_k=top_k)
                
                if results:
                    st.success(f"Found {len(results)} results")
                    
                    # Display results in a grid
                    cols = st.columns(3)
                    for i, result in enumerate(results):
                        with cols[i % 3]:
                            st.subheader(f"Rank {i+1}")
                            
                            # Load and display image
                            tile_path = result.get('tile_path', '')
                            if tile_path:
                                img = load_tile_image(tile_path)
                                if img:
                                    st.image(img, use_column_width=True)
                            
                            # Display metadata
                            st.json({
                                'Tile ID': result.get('tile_id', ''),
                                'Similarity': f"{result.get('similarity', 0):.4f}",
                                'Date': result.get('date', ''),
                                'Latitude': result.get('latitude', ''),
                                'Longitude': result.get('longitude', ''),
                                'Sensor': result.get('sensor', '')
                            })
                else:
                    st.warning("No results found")
                    
            except Exception as e:
                st.error(f"Search failed: {e}")
                st.info("Make sure Qdrant is running and CLIP embeddings are indexed.")

# Page: Image Search
elif page == "Image Search":
    st.markdown('<h2 class="section-header">🖼️ Image Search</h2>', unsafe_allow_html=True)
    
    st.markdown("Find similar satellite tiles by image similarity.")
    
    # Tile selection
    tiles_dir = Path(os.getenv('TILES_DIR', 'data/tiles'))
    tiles = []
    
    try:
        for year_dir in tiles_dir.iterdir():
            if year_dir.is_dir() and year_dir.name in ["2022", "2023", "2024"]:
                for tile_dir in year_dir.iterdir():
                    if tile_dir.is_dir():
                        metadata_file = tile_dir / "metadata.json"
                        if metadata_file.exists():
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                            # Add tile_path to metadata
                            metadata['tile_path'] = str(tile_dir)
                            tiles.append(metadata)
    except Exception as e:
        st.error(f"Failed to load tiles: {e}")
        tiles = []
    
    if tiles:
        tile_options = [f"{t['tile_id']} ({t['date']})" for t in tiles]
        selected_option = st.selectbox("Select a reference tile:", tile_options)
        top_k = st.slider("Number of results:", min_value=1, max_value=20, value=10)
        
        if st.button("Find Similar Images") and selected_option:
            selected_idx = tile_options.index(selected_option)
            selected_tile = tiles[selected_idx]['tile_id']
            
            with st.spinner("Searching..."):
                try:
                    results = services['image_search'].search_by_image(selected_tile, top_k=top_k)
                    
                    if results:
                        st.success(f"Found {len(results)} similar tiles")
                        
                        # Display selected tile
                        st.subheader("Selected Tile")
                        selected_metadata = tiles[selected_idx]
                        if selected_metadata:
                            img = load_tile_image(selected_metadata['tile_path'])
                            if img:
                                st.image(img, use_column_width=True)
                        
                        # Display results
                        cols = st.columns(3)
                        for i, result in enumerate(results):
                            with cols[i % 3]:
                                st.subheader(f"Rank {i+1}")
                                
                                tile_path = result.get('tile_path', '')
                                if tile_path:
                                    img = load_tile_image(tile_path)
                                    if img:
                                        st.image(img, use_column_width=True)
                                
                                st.json({
                                    'Tile ID': result.get('tile_id', ''),
                                    'Similarity': f"{result.get('similarity', 0):.4f}",
                                    'Date': result.get('date', ''),
                                    'Location': f"{result.get('latitude', '')}, {result.get('longitude', '')}"
                                })
                    else:
                        st.warning("No similar tiles found")
                        
                except Exception as e:
                    st.error(f"Search failed: {e}")
                    st.info("Make sure Qdrant is running and CLIP embeddings are indexed.")
    else:
        st.warning("No tiles found. Please run Phase 5 tiling first.")

# Page: Change Analysis
elif page == "Change Analysis":
    st.markdown('<h2 class="section-header">📊 Change Analysis</h2>', unsafe_allow_html=True)
    
    st.markdown("Analyze changes between temporal pairs.")
    
    # Year combination selection
    year_comb = st.selectbox("Select year combination:", ["2022_2023", "2023_2024", "2022_2024"])
    
    # Load change results
    with st.spinner("Loading change results..."):
        try:
            results = services['change_analysis'].list_change_results(year_comb)
            
            if results:
                st.success(f"Found {len(results)} change results")
                
                # Select a result
                result_options = [f"{r['pair_id']} ({r['before_date']} → {r['after_date']})" for r in results]
                selected_result = st.selectbox("Select a change result:", result_options)
                
                if selected_result:
                    result_idx = result_options.index(selected_result)
                    result = results[result_idx]
                    
                    # Display change information
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Before Image")
                        # Load before image from tile path
                        before_path = result.get('before_path', '')
                        if before_path:
                            img = load_tile_image(before_path)
                            if img:
                                st.image(img, use_column_width=True)
                    
                    with col2:
                        st.subheader("After Image")
                        after_path = result.get('after_path', '')
                        if after_path:
                            img = load_tile_image(after_path)
                            if img:
                                st.image(img, use_column_width=True)
                    
                    # Display change mask
                    st.subheader("Change Mask")
                    change_mask_path = result.get('change_mask_path', '')
                    if change_mask_path:
                        img = load_tile_image(change_mask_path)
                        if img:
                            st.image(img, use_column_width=True)
                    
                    # Display metadata
                    st.subheader("Change Statistics")
                    st.json({
                        'Pair ID': result['pair_id'],
                        'Change Percentage': f"{result['change_percentage']:.2f}%",
                        'Confidence': f"{result['confidence']:.4f}",
                        'Method': result['model_used'],
                        'Processing Time': f"{result['processing_time']:.2f}s",
                        'Before Date': result['before_date'],
                        'After Date': result['after_date']
                    })
            else:
                st.warning(f"No change results found for {year_comb}")
                
        except Exception as e:
            st.error(f"Failed to load change results: {e}")

# Page: Earliest Change
elif page == "Earliest Change":
    st.markdown('<h2 class="section-header">⏱️ Earliest Change</h2>', unsafe_allow_html=True)
    
    st.markdown("Identify the earliest detected changes across years.")
    
    # Tile selection
    tiles_dir = Path(os.getenv('TILES_DIR', 'data/tiles'))
    tiles = []
    
    try:
        for year_dir in tiles_dir.iterdir():
            if year_dir.is_dir() and year_dir.name in ["2022", "2023", "2024"]:
                for tile_dir in year_dir.iterdir():
                    if tile_dir.is_dir():
                        metadata_file = tile_dir / "metadata.json"
                        if metadata_file.exists():
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                            # Add tile_path to metadata
                            metadata['tile_path'] = str(tile_dir)
                            tiles.append(metadata)
    except Exception as e:
        st.error(f"Failed to load tiles: {e}")
        tiles = []
    
    if tiles:
        tile_options = [f"{t['tile_id']} ({t['date']})" for t in tiles]
        selected_option = st.selectbox("Select a tile to check for earliest change:", tile_options)
        
        if st.button("Find Earliest Change") and selected_option:
            selected_idx = tile_options.index(selected_option)
            selected_tile = tiles[selected_idx]['tile_id']
            
            with st.spinner("Analyzing changes..."):
                try:
                    earliest_change = services['earliest_change'].get_earliest_change(selected_tile)
                    
                    if earliest_change:
                        st.success(f"Earliest change detected: {earliest_change['year_comb']}")
                        
                        # Display change information
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Before Image")
                            before_path = earliest_change.get('before_path', '')
                            if before_path:
                                img = load_tile_image(before_path)
                                if img:
                                    st.image(img, use_column_width=True)
                        
                        with col2:
                            st.subheader("After Image")
                            after_path = earliest_change.get('after_path', '')
                            if after_path:
                                img = load_tile_image(after_path)
                                if img:
                                    st.image(img, use_column_width=True)
                        
                        # Display change mask
                        st.subheader("Change Mask")
                        change_mask_path = earliest_change.get('change_mask_path', '')
                        if change_mask_path:
                            img = load_tile_image(change_mask_path)
                            if img:
                                st.image(img, use_column_width=True)
                        
                        # Display metadata
                        st.subheader("Change Statistics")
                        st.json({
                            'Tile ID': selected_tile,
                            'Earliest Change Period': earliest_change['year_comb'],
                            'Before Date': earliest_change['before_date'],
                            'After Date': earliest_change['after_date'],
                            'Change Percentage': f"{earliest_change['change_percentage']:.2f}%",
                            'Confidence': f"{earliest_change['confidence']:.4f}",
                            'Method': earliest_change['method']
                        })
                    else:
                        st.info(f"No change detected for tile {selected_tile} across all temporal pairs.")
                        
                except Exception as e:
                    st.error(f"Failed to find earliest change: {e}")
                    st.info("Make sure Phase 10 temporal pairs and Phase 11 change results exist.")
    else:
        st.warning("No tiles found. Please run Phase 5 tiling first.")

# Page: Similar Locations
elif page == "Similar Locations":
    st.markdown('<h2 class="section-header">🗺️ Similar Locations</h2>', unsafe_allow_html=True)
    
    st.markdown("Discover locations with similar Earth-observation characteristics.")
    
    # Tile selection
    tiles_dir = Path(os.getenv('TILES_DIR', 'data/tiles'))
    embeddings_dir = Path(os.getenv('EMBEDDINGS_DIR', 'embeddings'))
    tiles = []
    
    try:
        for year_dir in tiles_dir.iterdir():
            if year_dir.is_dir() and year_dir.name in ["2022", "2023", "2024"]:
                for tile_dir in year_dir.iterdir():
                    if tile_dir.is_dir():
                        metadata_file = tile_dir / "metadata.json"
                        if metadata_file.exists():
                            # Check if tile has embedding (only show tiles with embeddings)
                            embedding_file = embeddings_dir / year_dir.name / f"{tile_dir.name}.npy"
                            if embedding_file.exists():
                                with open(metadata_file, 'r') as f:
                                    metadata = json.load(f)
                                # Add tile_path to metadata
                                metadata['tile_path'] = str(tile_dir)
                                tiles.append(metadata)
    except Exception as e:
        st.error(f"Failed to load tiles: {e}")
        tiles = []
    
    if tiles:
        tile_options = [f"{t['tile_id']} ({t['date']})" for t in tiles]
        selected_option = st.selectbox("Select an interesting tile:", tile_options)
        top_k = st.slider("Number of similar locations:", min_value=1, max_value=20, value=10)
        
        if st.button("Find Similar Locations") and selected_option:
            selected_idx = tile_options.index(selected_option)
            selected_tile = tiles[selected_idx]['tile_id']
            
            with st.spinner("Finding similar locations..."):
                try:
                    # Get cluster info
                    cluster_info = services['similar_locations'].get_cluster_info(selected_tile)
                    
                    if cluster_info:
                        st.info(f"Tile belongs to Cluster {cluster_info['cluster_id']}")
                        
                        # Find similar locations
                        results = services['similar_locations'].find_similar_locations(selected_tile, top_k=top_k)
                        
                        if results:
                            st.success(f"Found {len(results)} similar locations")
                            
                            # Display results
                            cols = st.columns(3)
                            for i, result in enumerate(results):
                                with cols[i % 3]:
                                    st.subheader(f"Rank {i+1}")
                                    
                                    tile_path = result.tile_path
                                    if tile_path:
                                        img = load_tile_image(tile_path)
                                        if img:
                                            st.image(img, use_column_width=True)
                                    
                                    st.json({
                                        'Tile ID': result.tile_id,
                                        'Similarity': f"{result.similarity:.4f}",
                                        'Date': result.date,
                                        'Location': f"{result.latitude}, {result.longitude}",
                                        'Sensor': result.sensor
                                    })
                        else:
                            st.warning("No similar locations found")
                    else:
                        st.warning("Tile not found in cluster assignments")
                        
                except Exception as e:
                    st.error(f"Failed to find similar locations: {e}")
                    st.info("Make sure Phase 13 clustering is completed.")
    else:
        st.warning("No tiles with embeddings found. Please run Phase 6 Clay embeddings first.")

# Page: Map
elif page == "Map":
    st.markdown('<h2 class="section-header">🗺️ Map Visualization</h2>', unsafe_allow_html=True)
    
    st.markdown("Geographic visualization of tiles and changes.")
    
    # Load map data
    with st.spinner("Loading map data..."):
        try:
            tiles = services['map_data'].get_all_tiles()
            changes = services['map_data'].get_change_locations()
            
            st.success(f"Loaded {len(tiles)} tiles and {len(changes)} change locations")
            
            # Display statistics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Tiles", len(tiles))
            with col2:
                st.metric("Change Locations", len(changes))
            
            # Create folium map centered on average coordinates
            if tiles:
                avg_lat = sum(t['latitude'] for t in tiles) / len(tiles)
                avg_lon = sum(t['longitude'] for t in tiles) / len(tiles)
                
                m = folium.Map(location=[avg_lat, avg_lon], zoom_start=10)
                
                # Add tile markers
                for tile in tiles:
                    folium.Marker(
                        location=[tile['latitude'], tile['longitude']],
                        popup=f"""
                        <b>Tile ID:</b> {tile['tile_id']}<br>
                        <b>Date:</b> {tile['date']}<br>
                        <b>Year:</b> {tile['year']}
                        """,
                        icon=folium.Icon(color='blue', icon='cloud')
                    ).add_to(m)
                
                # Add change markers
                for change in changes:
                    # Get bbox center if available
                    bbox = change.get('bbox', {})
                    if bbox:
                        center_lat = (bbox.get('min_lat', 0) + bbox.get('max_lat', 0)) / 2
                        center_lon = (bbox.get('min_lon', 0) + bbox.get('max_lon', 0)) / 2
                    else:
                        center_lat = avg_lat
                        center_lon = avg_lon
                    
                    folium.CircleMarker(
                        location=[center_lat, center_lon],
                        radius=5000,
                        popup=f"""
                        <b>Pair ID:</b> {change['pair_id']}<br>
                        <b>Change %:</b> {change['change_percentage']:.2f}%<br>
                        <b>Confidence:</b> {change['confidence']:.4f}
                        """,
                        color='red',
                        fill=True,
                        fill_color='red'
                    ).add_to(m)
                
                # Display map
                st_folium(m, width=1200, height=600)
                
                st.info("Blue markers: Tile locations | Red circles: Change locations")
            else:
                st.warning("No tiles found to display on map.")
                
        except Exception as e:
            st.error(f"Failed to load map data: {e}")
            st.info("Make sure Phase 5 tiles exist.")
            st.info("Make sure Phase 5 tiles exist.")

# Page: Analyst Review
elif page == "Analyst Review":
    st.markdown('<h2 class="section-header">✍️ Analyst Review</h2>', unsafe_allow_html=True)
    
    st.markdown("Review and validate change detection results.")
    
    # Select change result
    year_comb = st.selectbox("Select year combination:", ["2022_2023", "2023_2024", "2022_2024"])
    
    with st.spinner("Loading change results..."):
        try:
            results = services['change_analysis'].list_change_results(year_comb)
            
            if results:
                result_options = [f"{r['pair_id']} ({r['before_date']} → {r['after_date']})" for r in results]
                selected_result = st.selectbox("Select a change result to review:", result_options)
                
                if selected_result:
                    result_idx = result_options.index(selected_result)
                    result = results[result_idx]
                    
                    # Display before/after images
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Before Image")
                        before_path = result.get('before_path', '')
                        if before_path:
                            img = load_tile_image(before_path)
                            if img:
                                st.image(img, use_column_width=True)
                    
                    with col2:
                        st.subheader("After Image")
                        after_path = result.get('after_path', '')
                        if after_path:
                            img = load_tile_image(after_path)
                            if img:
                                st.image(img, use_column_width=True)
                    
                    # Display change mask
                    st.subheader("Change Mask")
                    change_mask_path = result.get('change_mask_path', '')
                    if change_mask_path:
                        img = load_tile_image(change_mask_path)
                        if img:
                            st.image(img, use_column_width=True)
                    
                    # Review form
                    st.subheader("Analyst Review")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        decision = st.radio("Decision:", ["confirmed", "rejected"])
                    
                    with col2:
                        change_type = st.selectbox(
                            "Change Type:",
                            ["construction", "clearance", "water_variation", "road_development", "unknown"]
                        )
                    
                    comment = st.text_area("Analyst Comment (optional):")
                    
                    if st.button("Submit Review"):
                        try:
                            review = services['analyst_review'].save_review(
                                change_result_id=result['pair_id'],
                                decision=decision,
                                change_type=change_type,
                                comment=comment if comment else None
                            )
                            st.success(f"Review submitted successfully: {decision}")
                            st.json(review)
                        except Exception as e:
                            st.error(f"Failed to submit review: {e}")
                            st.info("Make sure PostgreSQL is running and Phase 14 database is set up.")
            else:
                st.warning(f"No change results found for {year_comb}")
                
        except Exception as e:
            st.error(f"Failed to load change results: {e}")
            st.info("Make sure Phase 11 change results exist.")

# Footer
st.markdown("---")
st.markdown("""
**Satellite Intelligence Dashboard**  
Phase 14-15: PostgreSQL/PostGIS Database and Streamlit Analyst Dashboard  
""")
