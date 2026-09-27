import { useState } from 'react'
import { semanticSearch } from '../services/api'
import { Search, Sparkles } from 'lucide-react'

function SemanticSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [topK, setTopK] = useState(10)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    try {
      const response = await semanticSearch(query, topK)
      setResults(response.results || [])
    } catch (error) {
      console.error('Search error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fade-in">
      <h1>Semantic Search</h1>
      <p style={{ color: '#9ca3af', marginBottom: '2rem' }}>
        Search satellite imagery using natural language queries
      </p>

      <div className="card">
        <form onSubmit={handleSearch}>
          <div className="grid grid-2" style={{ marginBottom: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Search Query</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g., areas with water bodies"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
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
            {loading ? <div className="spinner" style={{ width: 20, height: 20 }} /> : <Search size={20} />}
            Search
          </button>
        </form>
      </div>

      {results.length > 0 && (
        <div className="search-results">
          {results.map((result, index) => (
            <div key={index} className="result-card">
              <div className="result-image" style={{ 
                background: `linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)`,
                display: 'flex',
                alignItems: 'center',
                overflow: 'hidden',
                position: 'relative'
              }}>
                <img 
                  src={`http://127.0.0.1:8000/image/${result.tile_id}`} 
                  alt={result.tile_id}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', position: 'absolute', top: 0, left: 0 }}
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
              </div>
              <div className="result-content">
                <div className="result-title">#{result.rank} - {result.tile_id}</div>
                <div className="result-meta">Date: {result.date}</div>
                <div className="result-meta">Sensor: {result.sensor}</div>
                <div className="result-meta">
                  Location: {result.latitude.toFixed(4)}, {result.longitude.toFixed(4)}
                </div>
                <div className="result-similarity">
                  Similarity: {(result.similarity * 100).toFixed(1)}%
                </div>
                <div className="result-meta">
                  Valid: {result.valid_percentage.toFixed(1)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default SemanticSearch
