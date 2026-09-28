import { useState } from 'react'
import { semanticSearch } from '../services/api'
import { Search, MapPin, Calendar, Satellite, ChevronRight, BarChart3 } from 'lucide-react'

function SemanticSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [topK, setTopK] = useState(10)
  const [hasSearched, setHasSearched] = useState(false)
  const [selectedTile, setSelectedTile] = useState(null)
  const [failedImages, setFailedImages] = useState({})

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setHasSearched(true)
    setSelectedTile(null)

    try {
      const response = await semanticSearch(query, topK)
      setResults(response.results || [])
    } catch (error) {
      console.error('Search error:', error)
    } finally {
      setLoading(false)
    }
  }

  const getSimColor = (sim) => {
    const p = sim * 100
    if (p >= 80) return '#10b981'
    if (p >= 60) return '#3b82f6'
    return '#f59e0b'
  }

  return (
    <div className="fade-in">
      <h1>Semantic Search</h1>
      <p style={{ color: '#9ca3af', marginBottom: '1.75rem', fontSize: '0.9rem' }}>
        Search satellite imagery using natural language
      </p>

      {/* Search Form */}
      <div className="card">
        <form onSubmit={handleSearch}>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <div style={{ flex: '1 1 300px', position: 'relative' }}>
              <Search size={16} style={{
                position: 'absolute', left: '0.9rem', top: '50%',
                transform: 'translateY(-50%)', color: '#64748b', pointerEvents: 'none'
              }} />
              <input
                type="text"
                className="form-control"
                placeholder="e.g. water bodies, agricultural land, dense forest..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                style={{ paddingLeft: '2.5rem' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.85rem', color: '#94a3b8', whiteSpace: 'nowrap' }}>Top K</label>
              <input
                type="number"
                className="form-control"
                value={topK}
                onChange={(e) => setTopK(Math.max(1, Math.min(50, parseInt(e.target.value) || 10)))}
                min={1} max={50}
                style={{ width: '70px', textAlign: 'center' }}
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !query.trim()}
              style={{ minWidth: '110px' }}
            >
              {loading
                ? <div className="spinner" style={{ width: 17, height: 17, borderWidth: 2 }} />
                : <Search size={16} />
              }
              {loading ? 'Searching…' : 'Search'}
            </button>
          </div>
        </form>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <>
          <p style={{ fontSize: '0.83rem', color: '#64748b', marginBottom: '0.25rem' }}>
            {results.length} result{results.length !== 1 ? 's' : ''} found
          </p>
          <div className="search-results">
            {results.map((result, index) => {
              const simPct = ((result.similarity || 0) * 100).toFixed(1)
              const simColor = getSimColor(result.similarity || 0)
              const expanded = selectedTile?.tile_id === result.tile_id

              return (
                <div
                  key={result.tile_id || index}
                  className="result-card"
                  onClick={() => setSelectedTile(expanded ? null : result)}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Image */}
                  <div className="result-image" style={{ position: 'relative' }}>
                    {!failedImages[result.tile_id] ? (
                      <img
                        src={`http://127.0.0.1:8000/image/${result.tile_id}`}
                        alt={result.tile_id}
                        style={{ width: '100%', height: '100%', objectFit: 'cover', position: 'absolute', inset: 0 }}
                        onError={() => setFailedImages(p => ({ ...p, [result.tile_id]: true }))}
                        loading="lazy"
                      />
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                        <Satellite size={32} style={{ color: '#334155', opacity: 0.5 }} />
                      </div>
                    )}

                    {/* Rank */}
                    <span style={{
                      position: 'absolute', top: 8, left: 8,
                      background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
                      borderRadius: '5px', padding: '0.15rem 0.45rem',
                      fontSize: '0.7rem', fontWeight: 700, color: '#e2e8f0'
                    }}>
                      #{result.rank}
                    </span>

                    {/* Similarity */}
                    <span style={{
                      position: 'absolute', top: 8, right: 8,
                      background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
                      borderRadius: '999px', padding: '0.15rem 0.55rem',
                      fontSize: '0.7rem', fontWeight: 700, color: simColor,
                      border: `1px solid ${simColor}50`
                    }}>
                      {simPct}%
                    </span>
                  </div>

                  {/* Body */}
                  <div className="result-content">
                    {/* Similarity Bar */}
                    <div style={{ marginBottom: '0.8rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.73rem', color: '#64748b', marginBottom: '0.25rem' }}>
                        <span>Similarity</span>
                        <span style={{ color: simColor, fontWeight: 600 }}>{simPct}%</span>
                      </div>
                      <div style={{ height: 3, background: 'rgba(255,255,255,0.07)', borderRadius: 999, overflow: 'hidden' }}>
                        <div style={{
                          height: '100%',
                          width: `${Math.min(100, (result.similarity || 0) * 100)}%`,
                          background: simColor,
                          borderRadius: 999,
                          transition: 'width 0.5s ease'
                        }} />
                      </div>
                    </div>

                    {/* Tile ID */}
                    <div style={{
                      fontFamily: 'monospace', fontSize: '0.8rem', fontWeight: 600,
                      color: '#f1f5f9', marginBottom: '0.7rem',
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'
                    }}>
                      {result.tile_id}
                    </div>

                    {/* Meta */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                      {result.date && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.79rem', color: '#94a3b8' }}>
                          <Calendar size={11} style={{ color: '#475569', flexShrink: 0 }} />
                          {result.date}
                        </div>
                      )}
                      {result.sensor && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.79rem', color: '#94a3b8' }}>
                          <Satellite size={11} style={{ color: '#475569', flexShrink: 0 }} />
                          {result.sensor}
                        </div>
                      )}
                      {result.latitude != null && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.79rem', color: '#94a3b8' }}>
                          <MapPin size={11} style={{ color: '#475569', flexShrink: 0 }} />
                          {result.latitude.toFixed(4)}°, {result.longitude.toFixed(4)}°
                        </div>
                      )}
                    </div>

                    {/* Expanded Details */}
                    {expanded && (
                      <div style={{
                        marginTop: '0.85rem',
                        paddingTop: '0.85rem',
                        borderTop: '1px solid rgba(255,255,255,0.06)',
                        animation: 'fadeIn 0.2s ease'
                      }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                          {result.valid_percentage != null && (
                            <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 8, padding: '0.55rem 0.7rem' }}>
                              <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.2rem' }}>Valid Pixels</div>
                              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#10b981' }}>{result.valid_percentage.toFixed(1)}%</div>
                            </div>
                          )}
                          {result.sensor && (
                            <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 8, padding: '0.55rem 0.7rem' }}>
                              <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.2rem' }}>Sensor</div>
                              <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#e2e8f0' }}>{result.sensor}</div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Expand hint */}
                    <div style={{
                      marginTop: '0.75rem',
                      display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.25rem',
                      fontSize: '0.72rem', color: '#475569'
                    }}>
                      <ChevronRight size={12} style={{
                        transform: expanded ? 'rotate(90deg)' : 'none',
                        transition: 'transform 0.2s ease'
                      }} />
                      {expanded ? 'Collapse' : 'Details'}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      {/* No results */}
      {hasSearched && !loading && results.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
          <BarChart3 size={34} style={{ margin: '0 auto 0.85rem', opacity: 0.35 }} />
          <p style={{ fontWeight: 500, marginBottom: '0.3rem' }}>No results found</p>
          <p style={{ fontSize: '0.83rem' }}>Try rephrasing your query</p>
        </div>
      )}
    </div>
  )
}

export default SemanticSearch
