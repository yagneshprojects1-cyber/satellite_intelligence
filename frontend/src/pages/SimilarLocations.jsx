import { useState } from 'react'
import { getSimilarLocations } from '../services/api'
import { Layers, Sparkles, AlertTriangle } from 'lucide-react'

function SimilarLocations() {
  const [tileId, setTileId] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [topK, setTopK] = useState(10)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!tileId.trim()) return

    setLoading(true)
    try {
      const response = await getSimilarLocations(tileId, topK)
      setResults(response.similar_locations || [])
    } catch (error) {
      console.error('Similar locations error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fade-in">
      <h1>Similar Locations</h1>
      <p style={{ color: '#9ca3af', marginBottom: '2rem' }}>
        Find similar locations using Clay embedding clustering
      </p>

      <div className="card">
        <form onSubmit={handleSearch}>
          <div className="grid grid-2" style={{ marginBottom: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Tile ID</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g., 2022_..."
                value={tileId}
                onChange={(e) => setTileId(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Results Count</label>
              <input
                type="number"
                className="form-control"
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value))}
                min={1}
                max={50}
              />
            </div>
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? <div className="spinner" style={{ width: 20, height: 20 }} /> : <Layers size={20} />}
            Find Similar
          </button>
        </form>
      </div>

      {results.length === 0 && !loading && (
        <div className="card">
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <AlertTriangle size={48} color="#fbbf24" style={{ marginBottom: '1rem' }} />
            <p>No results available</p>
            <p style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
              Run clustering job to enable similar location search
            </p>
          </div>
        </div>
      )}

      {results.length > 0 && (
        <div className="search-results">
          {results.map((result, index) => (
            <div key={index} className="result-card">
              <div className="result-image" style={{ 
                background: `linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Sparkles size={48} color="#60a5fa" />
              </div>
              <div className="result-content">
                <div className="result-title">#{result.rank} - {result.tile_id}</div>
                <div className="result-meta">Cluster: {result.cluster_id}</div>
                <div className="result-similarity">
                  Probability: {(result.cluster_probability * 100).toFixed(1)}%
                </div>
                {result.metadata && (
                  <>
                    <div className="result-meta">Year: {result.metadata.year}</div>
                    <div className="result-meta">
                      Location: {result.metadata.latitude?.toFixed(4)}, {result.metadata.longitude?.toFixed(4)}
                    </div>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default SimilarLocations
