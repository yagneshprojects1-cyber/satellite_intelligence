import { useState } from 'react'
import { semanticSearch, exportData } from '../services/api'
import { formatLocationTitle, formatDateFriendly } from '../utils/locationFormatter'
import { Search, MapPin, Calendar, Satellite, Download, ChevronDown, ChevronUp, Sparkles, SlidersHorizontal, CheckCircle2 } from 'lucide-react'

function SemanticSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [topK, setTopK] = useState(12)
  const [hasSearched, setHasSearched] = useState(false)
  const [selectedTile, setSelectedTile] = useState(null)
  const [failedImages, setFailedImages] = useState({})
  const [showFilters, setShowFilters] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [exportMsg, setExportMsg] = useState('')

  // Qdrant Metadata & AOI Filters state
  const [filters, setFilters] = useState({
    year: '',
    sensor: '',
    min_valid_percentage: 75,
    date_from: '',
    date_to: '',
    min_lat: '',
    max_lat: '',
    min_lon: '',
    max_lon: ''
  })

  const presetQueries = [
    "newly built structures near a river",
    "large vehicle concentrations on open ground",
    "water bodies and reservoirs",
    "agricultural land and crop clearing",
    "dense forest and canopy coverage"
  ]

  const handleSearch = async (e, queryOverride = null) => {
    if (e) e.preventDefault()
    const searchQuery = queryOverride !== null ? queryOverride : query
    if (!searchQuery.trim()) return

    setLoading(true)
    setHasSearched(true)
    setSelectedTile(null)
    setExportMsg('')

    const activeFilters = {}
    if (filters.year) activeFilters.year = filters.year
    if (filters.sensor) activeFilters.sensor = filters.sensor
    if (filters.min_valid_percentage) activeFilters.min_valid_percentage = parseFloat(filters.min_valid_percentage)
    if (filters.date_from || filters.date_to) {
      activeFilters.date_range = {
        start: filters.date_from || null,
        end: filters.date_to || null
      }
    }
    if (filters.min_lat && filters.max_lat && filters.min_lon && filters.max_lon) {
      activeFilters.bbox = {
        min_lat: parseFloat(filters.min_lat),
        max_lat: parseFloat(filters.max_lat),
        min_lon: parseFloat(filters.min_lon),
        max_lon: parseFloat(filters.max_lon)
      }
    }

    try {
      const response = await semanticSearch(searchQuery, topK, Object.keys(activeFilters).length > 0 ? activeFilters : null)
      setResults(response.results || [])
    } catch (error) {
      console.error('Search error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async (format) => {
    if (results.length === 0) return
    setExporting(true)
    try {
      const res = await exportData('search_results', format, results)
      setExportMsg(`Exported ${res.record_count} records to ${res.file_path || format.toUpperCase()}`)
    } catch (err) {
      setExportMsg('Export failed: ' + err.message)
    } finally {
      setExporting(false)
    }
  }

  const getSimColor = (sim) => {
    const p = sim * 100
    if (p >= 80) return '#10b981'
    if (p >= 60) return '#06b6d4'
    return '#f59e0b'
  }

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Sparkles size={24} style={{ color: '#06b6d4' }} />
            Semantic & Multimodal Retrieval
          </h1>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.2rem' }}>
            Natural language text search powered by CLIP & Qdrant vector indexing with metadata & AOI filtering
          </p>
        </div>

        {results.length > 0 && (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }} onClick={() => handleExport('csv')} disabled={exporting}>
              <Download size={14} /> Export CSV
            </button>
            <button className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }} onClick={() => handleExport('json')} disabled={exporting}>
              <Download size={14} /> Export JSON
            </button>
          </div>
        )}
      </div>

      {exportMsg && (
        <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', color: '#10b981', padding: '0.6rem 1rem', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <CheckCircle2 size={16} /> {exportMsg}
        </div>
      )}

      {/* Search Bar & Main Controls */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <form onSubmit={handleSearch}>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <div style={{ flex: '1 1 340px', position: 'relative' }}>
              <Search size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: '#06b6d4', pointerEvents: 'none' }} />
              <input
                type="text"
                className="form-control"
                placeholder='e.g. "newly built structures near a river" or "vehicle concentrations"...'
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                style={{ paddingLeft: '2.75rem', fontSize: '0.95rem' }}
              />
            </div>

            <button
              type="button"
              className={`btn ${showFilters ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setShowFilters(!showFilters)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <SlidersHorizontal size={16} />
              Filters {Object.values(filters).some(v => v !== '' && v !== 75) && <span style={{ background: '#06b6d4', color: '#0f172a', borderRadius: '50%', width: 16, height: 16, fontSize: '0.65rem', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700 }}>!</span>}
              {showFilters ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <label style={{ fontSize: '0.82rem', color: '#94a3b8', whiteSpace: 'nowrap' }}>Limit</label>
              <input
                type="number"
                className="form-control"
                value={topK}
                onChange={(e) => setTopK(Math.max(1, Math.min(50, parseInt(e.target.value) || 10)))}
                min={1} max={50}
                style={{ width: '65px', textAlign: 'center' }}
              />
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading || !query.trim()} style={{ minWidth: '120px' }}>
              {loading ? <div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> : <Search size={16} />}
              {loading ? 'Searching…' : 'Execute Search'}
            </button>
          </div>
        </form>

        {/* Preset Query Chips */}
        <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Examples:</span>
          {presetQueries.map((preset, idx) => (
            <button
              key={idx} type="button"
              onClick={(e) => { setQuery(preset); handleSearch(e, preset) }}
              style={{
                background: 'rgba(30, 41, 59, 0.7)', border: '1px solid rgba(51, 65, 85, 0.8)', color: '#cbd5e1',
                padding: '0.25rem 0.65rem', borderRadius: '999px', fontSize: '0.78rem', cursor: 'pointer', transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => { e.target.style.borderColor = '#06b6d4'; e.target.style.color = '#38bdf8' }}
              onMouseLeave={(e) => { e.target.style.borderColor = 'rgba(51, 65, 85, 0.8)'; e.target.style.color = '#cbd5e1' }}
            >
              "{preset}"
            </button>
          ))}
        </div>

        {/* Filter Drawer */}
        {showFilters && (
          <div style={{ marginTop: '1.25rem', paddingTop: '1.25rem', borderTop: '1px solid #334155', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div>
              <label style={{ fontSize: '0.78rem', color: '#94a3b8', display: 'block', marginBottom: '0.3rem' }}>Acquisition Year</label>
              <select className="form-control" value={filters.year} onChange={(e) => setFilters({ ...filters, year: e.target.value })}>
                <option value="">All Years</option>
                <option value="2022">2022 Baseline</option>
                <option value="2023">2023 Intermediate</option>
                <option value="2024">2024 Latest</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', color: '#94a3b8', display: 'block', marginBottom: '0.3rem' }}>Sensor Platform</label>
              <select className="form-control" value={filters.sensor} onChange={(e) => setFilters({ ...filters, sensor: e.target.value })}>
                <option value="">All Sensors</option>
                <option value="Sentinel-2">Sentinel-2 MSI</option>
                <option value="Landsat-8">Landsat-8 OLI</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', color: '#94a3b8', display: 'block', marginBottom: '0.3rem' }}>
                Min Valid Data Quality: <span style={{ color: '#06b6d4', fontWeight: 700 }}>{filters.min_valid_percentage}%</span>
              </label>
              <input type="range" min="30" max="100" step="5" value={filters.min_valid_percentage} onChange={(e) => setFilters({ ...filters, min_valid_percentage: e.target.value })} style={{ width: '100%', accentColor: '#06b6d4' }} />
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', color: '#94a3b8', display: 'block', marginBottom: '0.3rem' }}>Date Range (Start - End)</label>
              <div style={{ display: 'flex', gap: '0.4rem' }}>
                <input type="date" className="form-control" style={{ fontSize: '0.75rem', padding: '0.35rem' }} value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} />
                <input type="date" className="form-control" style={{ fontSize: '0.75rem', padding: '0.35rem' }} value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Results Grid */}
      {results.length > 0 && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
              Retrieved <span style={{ color: '#06b6d4', fontWeight: 700 }}>{results.length}</span> ranked satellite tile matches for query <span style={{ color: '#f8fafc', fontStyle: 'italic' }}>"{query}"</span>
            </p>
          </div>

          <div className="search-results">
            {results.map((result, index) => {
              const simPct = ((result.similarity || 0) * 100).toFixed(1)
              const simColor = getSimColor(result.similarity || 0)
              const friendlyTitle = formatLocationTitle(result.tile_id, result.latitude, result.longitude, result.date)
              const friendlyDate = formatDateFriendly(result.date)

              return (
                <div
                  key={result.tile_id || index}
                  className="result-card"
                  onClick={() => setSelectedTile(result)}
                  style={{ cursor: 'pointer', position: 'relative' }}
                >
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
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', background: '#0f172a' }}>
                        <Satellite size={32} style={{ color: '#334155', opacity: 0.5 }} />
                      </div>
                    )}

                    <span style={{ position: 'absolute', top: 8, left: 8, background: 'rgba(15, 23, 42, 0.85)', backdropFilter: 'blur(4px)', borderRadius: '5px', padding: '0.2rem 0.5rem', fontSize: '0.72rem', fontWeight: 700, color: '#e2e8f0', border: '1px solid #334155' }}>
                      #{result.rank || index + 1}
                    </span>

                    <span style={{ position: 'absolute', top: 8, right: 8, background: 'rgba(15, 23, 42, 0.85)', backdropFilter: 'blur(4px)', borderRadius: '999px', padding: '0.2rem 0.6rem', fontSize: '0.72rem', fontWeight: 700, color: simColor, border: `1px solid ${simColor}60` }}>
                      {simPct}% Match
                    </span>
                  </div>

                  <div className="result-body">
                    {/* User Friendly Sector Title */}
                    <div className="result-title" style={{ fontSize: '0.92rem', fontWeight: 700, color: '#f8fafc' }}>
                      {friendlyTitle}
                    </div>

                    <div className="result-meta">
                      <span><Calendar size={12} /> {friendlyDate}</span>
                      <span><Satellite size={12} /> {result.sensor || 'Sentinel-2'}</span>
                    </div>

                    {result.latitude && result.longitude && (
                      <div className="result-meta" style={{ marginTop: '0.25rem' }}>
                        <span><MapPin size={12} /> {Number(result.latitude).toFixed(4)}°N, {Number(result.longitude).toFixed(4)}°E</span>
                        {result.valid_percentage && <span>QA: {Number(result.valid_percentage).toFixed(0)}%</span>}
                      </div>
                    )}

                    {/* Subtle Technical ID Badge for Audit Lineage */}
                    <div style={{ marginTop: '0.5rem', paddingTop: '0.4rem', borderTop: '1px dashed #334155', fontSize: '0.68rem', color: '#64748b', fontFamily: 'monospace' }}>
                      ID: {result.tile_id}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      {hasSearched && !loading && results.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: '3rem 1.5rem', color: '#64748b' }}>
          <Search size={40} style={{ opacity: 0.3, marginBottom: '0.75rem' }} />
          <p style={{ color: '#e2e8f0', fontWeight: 600 }}>No imagery tiles matched your semantic query and filters</p>
        </div>
      )}

      {/* Tile Detail Preview Modal */}
      {selectedTile && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(6px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem' }} onClick={() => setSelectedTile(null)}>
          <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '14px', maxWidth: '650px', width: '100%', overflow: 'hidden', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem 1.25rem', borderBottom: '1px solid #334155' }}>
              <h3 style={{ fontSize: '1.05rem', margin: 0, color: '#f8fafc' }}>
                {formatLocationTitle(selectedTile.tile_id, selectedTile.latitude, selectedTile.longitude, selectedTile.date)}
              </h3>
              <button onClick={() => setSelectedTile(null)} className="btn btn-secondary" style={{ padding: '0.2rem 0.6rem' }}>✕</button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem', padding: '1.25rem' }}>
              <div style={{ height: 260, borderRadius: 8, overflow: 'hidden', background: '#0f172a', border: '1px solid #334155' }}>
                <img src={`http://127.0.0.1:8000/image/${selectedTile.tile_id}`} alt="tile" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </div>

              <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                <div><span style={{ color: '#94a3b8' }}>Similarity Score:</span> <strong style={{ color: getSimColor(selectedTile.similarity || 0) }}>{((selectedTile.similarity || 0) * 100).toFixed(2)}%</strong></div>
                <div><span style={{ color: '#94a3b8' }}>Acquisition Date:</span> <strong>{formatDateFriendly(selectedTile.date)}</strong></div>
                <div><span style={{ color: '#94a3b8' }}>Sensor Platform:</span> <strong>{selectedTile.sensor || 'Sentinel-2 MSI'}</strong></div>
                <div><span style={{ color: '#94a3b8' }}>Geographic Bounds:</span> <strong>{selectedTile.latitude?.toFixed(4)}°N, {selectedTile.longitude?.toFixed(4)}°E</strong></div>
                <div><span style={{ color: '#94a3b8' }}>Data Quality Index:</span> <strong>{selectedTile.valid_percentage || 100}%</strong></div>
                <div style={{ fontFamily: 'monospace', fontSize: '0.72rem', color: '#64748b' }}><span style={{ color: '#94a3b8' }}>System Tile ID:</span> {selectedTile.tile_id}</div>
              </div>
            </div>

            <div style={{ padding: '1rem 1.25rem', background: '#0f172a', borderTop: '1px solid #334155', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button className="btn btn-secondary" onClick={() => setSelectedTile(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SemanticSearch
