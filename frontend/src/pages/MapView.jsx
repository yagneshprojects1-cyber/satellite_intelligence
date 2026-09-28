import { useState, useEffect, useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle, Rectangle, useMap } from 'react-leaflet'
import { getMapData } from '../services/api'
import { MapPin, Layers, Activity, Calendar, Satellite, RefreshCw, Eye, Search, X } from 'lucide-react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix default Leaflet icon paths in Vite / React
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

// Custom DivIcons for different years / change types
const createCustomIcon = (color, label = '') => {
  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        background: ${color};
        width: 22px;
        height: 22px;
        border-radius: 50%;
        border: 2px solid #ffffff;
        box-shadow: 0 0 10px ${color}99, 0 4px 6px rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        font-size: 9px;
        font-weight: 700;
      ">
        ${label}
      </div>
    `,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
    popupAnchor: [0, -11]
  })
}

const icons = {
  '2022': createCustomIcon('#3b82f6', '22'),
  '2023': createCustomIcon('#10b981', '23'),
  '2024': createCustomIcon('#8b5cf6', '24'),
  'change': createCustomIcon('#ef4444', '!'),
  'default': createCustomIcon('#06b6d4')
}

// Helper to center map view smoothly
function MapCenterUpdater({ center, zoom }) {
  const map = useMap()
  useEffect(() => {
    if (center && center[0] && center[1]) {
      map.setView(center, zoom || map.getZoom(), { animate: true })
    }
  }, [center, zoom, map])
  return null
}

function MapView() {
  const [tiles, setTiles] = useState([])
  const [changes, setChanges] = useState([])
  const [loading, setLoading] = useState(true)
  const [yearFilter, setYearFilter] = useState('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedItem, setSelectedItem] = useState(null)
  const [baseLayer, setBaseLayer] = useState('satellite')
  const [showCircles, setShowCircles] = useState(true)
  const [showMarkers, setShowMarkers] = useState(true)
  const [showChanges, setShowChanges] = useState(true)
  const [mapCenter, setMapCenter] = useState([18.0635, 75.9691])

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await getMapData(null, 500)
      setTiles(data.tiles || [])
      setChanges(data.changes || [])
      if (data.center && data.center[0] && data.center[1]) {
        setMapCenter(data.center)
      }
    } catch (error) {
      console.error('Error loading map data:', error)
      // Fallback sample tiles if backend is offline
      setTiles([
        { tile_id: '2022_T43QFV_000001', year: '2022', date: '2022-12-27', latitude: 18.0635, longitude: 75.9691, valid_percentage: 96.5, sensor: 'Sentinel-2' },
        { tile_id: '2022_T43QFV_000002', year: '2022', date: '2022-12-27', latitude: 18.0850, longitude: 75.9910, valid_percentage: 98.1, sensor: 'Sentinel-2' },
        { tile_id: '2023_T43QFV_000001', year: '2023', date: '2023-11-15', latitude: 18.1200, longitude: 76.0120, valid_percentage: 94.2, sensor: 'Sentinel-2' },
        { tile_id: '2023_T43QFV_000002', year: '2023', date: '2023-11-15', latitude: 18.0950, longitude: 76.0350, valid_percentage: 95.8, sensor: 'Sentinel-2' },
        { tile_id: '2024_T43QFV_000001', year: '2024', date: '2024-03-20', latitude: 18.0410, longitude: 75.9320, valid_percentage: 99.0, sensor: 'Sentinel-2' },
        { tile_id: '2024_T43QFV_000002', year: '2024', date: '2024-03-20', latitude: 18.0710, longitude: 75.9550, valid_percentage: 97.4, sensor: 'Sentinel-2' }
      ])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // Filtered tiles based on Search Query (shows all years by default)
  const filteredTiles = useMemo(() => {
    if (!searchQuery.trim()) return tiles
    const q = searchQuery.toLowerCase().trim()
    return tiles.filter((t) => {
      const latStr = t.latitude != null ? t.latitude.toFixed(4) : ''
      const lonStr = t.longitude != null ? t.longitude.toFixed(4) : ''
      return (
        t.tile_id?.toLowerCase().includes(q) ||
        t.sensor?.toLowerCase().includes(q) ||
        t.date?.toLowerCase().includes(q) ||
        String(t.year || '').toLowerCase().includes(q) ||
        latStr.includes(q) ||
        lonStr.includes(q)
      )
    })
  }, [tiles, searchQuery])

  // Tile layer URL map
  const tileLayers = {
    'carto-dark': {
      url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      attribution: '&copy; <a href="https://carto.com/">CARTO</a>'
    },
    'satellite': {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    },
    'osm': {
      url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }
  }

  const handleTileSelect = (tile) => {
    setSelectedItem(tile)
    if (tile.latitude && tile.longitude) {
      setMapCenter([tile.latitude, tile.longitude])
    }
  }

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <h1>Geospatial Map Viewer</h1>
          <p style={{ color: '#9ca3af', fontSize: '0.9rem', margin: 0 }}>
            Interactive Leaflet satellite tile coverage, change locations, and territory intelligence
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            className="btn btn-secondary"
            onClick={() => loadData(yearFilter)}
            disabled={loading}
            style={{ fontSize: '0.82rem', padding: '0.5rem 0.85rem' }}
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="card" style={{ marginBottom: '1.25rem', padding: '0.85rem 1.25rem' }}>
        <div style={{ position: 'relative', width: '100%' }}>
          <Search
            size={16}
            style={{
              position: 'absolute',
              left: '0.9rem',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#64748b',
              pointerEvents: 'none'
            }}
          />
          <input
            type="text"
            className="form-control"
            placeholder="Search tile by ID, coordinates (lat, lon), acquisition date, or sensor..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              paddingLeft: '2.5rem',
              paddingRight: searchQuery ? '2.5rem' : '1rem',
              width: '100%',
              height: '42px',
              fontSize: '0.88rem'
            }}
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              style={{
                position: 'absolute',
                right: '0.85rem',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: '4px'
              }}
            >
              <X size={15} />
            </button>
          )}
        </div>
      </div>

      {/* Main Map + Side Drawer Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedItem ? '1fr 340px' : '1fr', gap: '1.25rem', alignItems: 'stretch' }}>
        {/* Leaflet Map Card */}
        <div className="card" style={{ padding: '0.5rem', position: 'relative', height: '100%' }}>
          {loading && (
            <div style={{
              position: 'absolute', inset: 0, background: 'rgba(15, 23, 42, 0.7)',
              zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center',
              borderRadius: '12px', backdropFilter: 'blur(3px)'
            }}>
              <div className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
            </div>
          )}

          <div className="map-container" style={{ height: '580px', width: '100%' }}>
            <MapContainer
              center={mapCenter}
              zoom={10}
              scrollWheelZoom={true}
              style={{ height: '100%', width: '100%' }}
            >
              <MapCenterUpdater center={mapCenter} />

              <TileLayer
                url={tileLayers[baseLayer].url}
                attribution={tileLayers[baseLayer].attribution}
                maxZoom={19}
              />

              {/* Tile Coverage Circles & Markers */}
              {filteredTiles.map((tile) => {
                const color = tile.year === '2022' ? '#3b82f6' : tile.year === '2023' ? '#10b981' : '#8b5cf6'
                const icon = icons[tile.year] || icons.default
                const isSelected = selectedItem?.tile_id === tile.tile_id

                return (
                  <div key={tile.tile_id}>
                    {/* Footprint Coverage Circle */}
                    {showCircles && (
                      <Circle
                        center={[tile.latitude, tile.longitude]}
                        radius={2500}
                        pathOptions={{
                          color: color,
                          fillColor: color,
                          fillOpacity: isSelected ? 0.45 : 0.18,
                          weight: isSelected ? 2.5 : 1
                        }}
                        eventHandlers={{
                          click: () => handleTileSelect(tile)
                        }}
                      />
                    )}

                    {/* Tile Bounding Box if available */}
                    {tile.bbox && tile.bbox.min_lat && (
                      <Rectangle
                        bounds={[
                          [tile.bbox.min_lat, tile.bbox.min_lon],
                          [tile.bbox.max_lat, tile.bbox.max_lon]
                        ]}
                        pathOptions={{
                          color: color,
                          weight: 1,
                          fillOpacity: 0.05
                        }}
                      />
                    )}

                    {/* Point Marker (Click directly selects tile in the Right Inspector) */}
                    {showMarkers && (
                      <Marker
                        position={[tile.latitude, tile.longitude]}
                        icon={icon}
                        eventHandlers={{
                          click: () => handleTileSelect(tile)
                        }}
                      />
                    )}
                  </div>
                )
              })}

              {/* Change Detection Markers */}
              {showChanges && changes.map((change, idx) => {
                const lat = change.latitude || 18.06 + (idx * 0.02)
                const lon = change.longitude || 75.96 + (idx * 0.02)
                return (
                  <Marker
                    key={`change-${change.id || idx}`}
                    position={[lat, lon]}
                    icon={icons.change}
                    eventHandlers={{
                      click: () => setSelectedItem({
                        tile_id: `Change Hotspot #${idx + 1}`,
                        year: 'Change',
                        date: change.date || 'Detected Change',
                        latitude: lat,
                        longitude: lon,
                        sensor: change.change_type || 'Change Alert',
                        valid_percentage: (change.confidence || 0.9) * 100
                      })
                    }}
                  />
                )
              })}
            </MapContainer>
          </div>
        </div>

        {/* Selected Tile Inspector Sidebar - Exact Matching Height */}
        {selectedItem && (
          <div className="card" style={{
            padding: '1.25rem',
            position: 'relative',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            boxSizing: 'border-box'
          }}>
            <div>
              {/* Header */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#38bdf8', fontSize: '0.82rem', fontWeight: 600 }}>
                  <Eye size={14} /> Tile Inspector
                </div>
                <button
                  onClick={() => setSelectedItem(null)}
                  style={{
                    background: 'rgba(255,255,255,0.06)',
                    border: 'none',
                    color: '#94a3b8',
                    cursor: 'pointer',
                    fontSize: '1rem',
                    borderRadius: '6px',
                    width: 24,
                    height: 24,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  &times;
                </button>
              </div>

              {/* Tile Image Preview */}
              <div style={{
                width: '100%',
                height: 175,
                background: '#020617',
                borderRadius: '8px',
                overflow: 'hidden',
                marginBottom: '1rem',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                position: 'relative'
              }}>
                <img
                  src={`http://127.0.0.1:8000/image/${selectedItem.tile_id}`}
                  alt={selectedItem.tile_id}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  onError={(e) => { e.target.style.display = 'none' }}
                />
                <span style={{
                  position: 'absolute', top: 6, left: 6,
                  background: 'rgba(0,0,0,0.7)', padding: '0.15rem 0.5rem',
                  borderRadius: '4px', fontSize: '0.72rem', fontWeight: 700, color: '#f8fafc',
                  border: '1px solid rgba(255,255,255,0.15)'
                }}>
                  {selectedItem.year}
                </span>
              </div>

              {/* Tile ID */}
              <h3 style={{
                fontSize: '0.9rem',
                fontFamily: 'monospace',
                color: '#f8fafc',
                marginBottom: '1rem',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {selectedItem.tile_id}
              </h3>

              {/* Metadata List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', fontSize: '0.83rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#94a3b8' }}>
                  <Calendar size={14} style={{ color: '#475569', flexShrink: 0 }} />
                  <span>Date: <strong style={{ color: '#e2e8f0' }}>{selectedItem.date}</strong></span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#94a3b8' }}>
                  <MapPin size={14} style={{ color: '#475569', flexShrink: 0 }} />
                  <span>Coords: <strong style={{ color: '#e2e8f0' }}>{selectedItem.latitude.toFixed(4)}°, {selectedItem.longitude.toFixed(4)}°</strong></span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#94a3b8' }}>
                  <Satellite size={14} style={{ color: '#475569', flexShrink: 0 }} />
                  <span>Sensor: <strong style={{ color: '#e2e8f0' }}>{selectedItem.sensor || 'Sentinel-2'}</strong></span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#94a3b8' }}>
                  <Layers size={14} style={{ color: '#475569', flexShrink: 0 }} />
                  <span>Valid Pixels: <strong style={{ color: '#10b981' }}>{selectedItem.valid_percentage ? `${selectedItem.valid_percentage.toFixed(1)}%` : '100%'}</strong></span>
                </div>
              </div>
            </div>

            {/* Bottom Button */}
            <div style={{ marginTop: '1.25rem' }}>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setMapCenter([selectedItem.latitude, selectedItem.longitude])
                }}
                style={{ width: '100%', fontSize: '0.84rem', padding: '0.55rem' }}
              >
                Center on Map
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Map Legend & Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem', marginTop: '1.25rem' }}>
        <div className="card" style={{ padding: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.35rem' }}>
            Active Tiles Displayed
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#38bdf8' }}>
            {filteredTiles.length} <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 400 }}>of {tiles.length}</span>
          </div>
        </div>

        <div className="card" style={{ padding: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.35rem' }}>
            Year Distribution
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginTop: '0.2rem' }}>
            <span style={{ fontSize: '0.82rem', color: '#3b82f6', fontWeight: 600 }}>2022: {tiles.filter(t => t.year === '2022').length}</span>
            <span style={{ fontSize: '0.82rem', color: '#10b981', fontWeight: 600 }}>2023: {tiles.filter(t => t.year === '2023').length}</span>
            <span style={{ fontSize: '0.82rem', color: '#8b5cf6', fontWeight: 600 }}>2024: {tiles.filter(t => t.year === '2024').length}</span>
          </div>
        </div>

        <div className="card" style={{ padding: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.35rem' }}>
            Legend
          </div>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center', marginTop: '0.2rem', fontSize: '0.8rem', color: '#94a3b8' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#3b82f6' }} /> 2022 Tiles
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#10b981' }} /> 2023 Tiles
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#8b5cf6' }} /> 2024 Tiles
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#ef4444' }} /> Change Hotspots
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MapView
