import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet'
import { Map as MapIcon, Layers } from 'lucide-react'
import 'leaflet/dist/leaflet.css'

function MapView() {
  const [tiles, setTiles] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Load tiles from backend
    loadTiles()
  }, [])

  const loadTiles = async () => {
    try {
      // This would fetch tiles from the backend
      // For now, use placeholder data
      setTiles([
        { id: '1', lat: 18.0, lon: 76.0, year: '2022' },
        { id: '2', lat: 18.5, lon: 76.5, year: '2023' },
        { id: '3', lat: 19.0, lon: 77.0, year: '2024' },
      ])
    } catch (error) {
      console.error('Error loading tiles:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="card">
        <div className="spinner"></div>
        <p style={{ marginTop: '1rem' }}>Loading map...</p>
      </div>
    )
  }

  return (
    <div className="fade-in">
      <h1>Interactive Map</h1>
      <p style={{ color: '#9ca3af', marginBottom: '2rem' }}>
        Visualize tiles, search results, and change locations
      </p>

      <div className="card">
        <div className="map-container">
          <MapContainer center={[18.5, 76.5]} zoom={8} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />
            {tiles.map((tile) => (
              <Circle
                key={tile.id}
                center={[tile.lat, tile.lon]}
                radius={5000}
                pathOptions={{ color: '#60a5fa', fillColor: '#60a5fa', fillOpacity: 0.3 }}
              >
                <Popup>
                  <div>
                    <strong>Tile {tile.id}</strong><br />
                    Year: {tile.year}<br />
                    Lat: {tile.lat.toFixed(4)}<br />
                    Lon: {tile.lon.toFixed(4)}
                  </div>
                </Popup>
              </Circle>
            ))}
          </MapContainer>
        </div>
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <h2 className="card-header">Map Legend</h2>
        <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: 20, height: 20, background: '#60a5fa', borderRadius: '50%', opacity: 0.5 }} />
            <span>Tile Coverage</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Layers size={20} color="#22c55e" />
            <span>Detected Changes</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <MapIcon size={20} color="#fbbf24" />
            <span>Search Results</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MapView
