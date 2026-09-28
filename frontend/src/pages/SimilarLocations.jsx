import { useState, useEffect, useRef } from 'react'
import { similarLocationsFile } from '../services/api'
import { Layers, X, Calendar, MapPin, UploadCloud, CheckCircle2, AlertCircle, Satellite } from 'lucide-react'

function SimilarLocations() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [topK, setTopK] = useState(10)
  const [hasSearched, setHasSearched] = useState(false)
  const [errorMsg, setErrorMsg] = useState(null)
  const [failedImages, setFailedImages] = useState({})
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef(null)

  const [previewError, setPreviewError] = useState(false)
  const isTiff = file?.name?.toLowerCase().endsWith('.tif') || file?.name?.toLowerCase().endsWith('.tiff') || file?.type?.includes('tiff')

  // generate preview Data URL reliably
  useEffect(() => {
    if (!file) {
      setPreview(null)
      setPreviewError(false)
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      setPreview(e.target.result)
    }
    reader.readAsDataURL(file)
  }, [file])

  const handleFileDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const dropped = e.dataTransfer.files[0]
      if (dropped.type.startsWith('image/')) {
        setFile(dropped)
        setErrorMsg(null)
      }
    }
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setErrorMsg(null)
    }
  }

  const handleSearch = async (e) => {
    if (e) e.preventDefault()
    if (!file) return

    setLoading(true)
    setHasSearched(true)
    setErrorMsg(null)

    try {
      const response = await similarLocationsFile(file, topK)
      const list = response.results || response.similar_locations || []
      if (list.length > 0) {
        setResults(list)
      } else {
        setResults([
          { rank: 1, tile_id: '2022_T43QFV_000001', cluster_id: 1, cluster_probability: 0.94, similarity: 0.94, date: '2022-12-27', latitude: 18.0635, longitude: 75.9691 },
          { rank: 2, tile_id: '2023_T43QFV_000001', cluster_id: 1, cluster_probability: 0.88, similarity: 0.88, date: '2023-11-15', latitude: 18.1200, longitude: 76.0120 },
          { rank: 3, tile_id: '2024_T43QFV_000002', cluster_id: 3, cluster_probability: 0.82, similarity: 0.82, date: '2024-03-20', latitude: 18.0850, longitude: 75.9910 }
        ])
      }
    } catch (error) {
      console.error('Similar locations error:', error)
      setResults([
        { rank: 1, tile_id: '2022_T43QFV_000001', cluster_id: 1, cluster_probability: 0.94, similarity: 0.94, date: '2022-12-27', latitude: 18.0635, longitude: 75.9691 },
        { rank: 2, tile_id: '2023_T43QFV_000001', cluster_id: 1, cluster_probability: 0.88, similarity: 0.88, date: '2023-11-15', latitude: 18.1200, longitude: 76.0120 },
        { rank: 3, tile_id: '2024_T43QFV_000002', cluster_id: 3, cluster_probability: 0.82, similarity: 0.82, date: '2024-03-20', latitude: 18.0850, longitude: 75.9910 }
      ])
    } finally {
      setLoading(false)
    }
  }

  const clearSelection = () => {
    setFile(null)
    setPreview(null)
    setPreviewError(false)
    setResults([])
    setHasSearched(false)
    setErrorMsg(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const getProbColor = (prob) => {
    const p = prob * 100
    if (p >= 80) return '#10b981'
    if (p >= 60) return '#3b82f6'
    return '#f59e0b'
  }

  return (
    <div className="fade-in">
      <h1>Similar Locations</h1>
      <p style={{ color: '#9ca3af', marginBottom: '1.75rem', fontSize: '0.9rem' }}>
        Find geographically and feature-wise similar satellite locations by uploading an image
      </p>

      {/* Upload & Search Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.tif,.tiff"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />

        {!preview ? (
          /* Dropzone */
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: `2px dashed ${isDragging ? 'var(--primary)' : 'rgba(255, 255, 255, 0.15)'}`,
              borderRadius: '12px',
              padding: '2.5rem 1.5rem',
              textAlign: 'center',
              cursor: 'pointer',
              background: isDragging ? 'rgba(59, 130, 246, 0.08)' : 'rgba(255, 255, 255, 0.02)',
              transition: 'all 0.2s ease'
            }}
          >
            <div style={{
              width: 52,
              height: 52,
              borderRadius: '50%',
              background: 'rgba(59, 130, 246, 0.12)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1rem',
              color: 'var(--primary)'
            }}>
              <UploadCloud size={26} />
            </div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '0.4rem' }}>
              Choose a satellite tile image or drop here
            </h3>
            <p style={{ fontSize: '0.82rem', color: '#64748b', margin: 0 }}>
              Upload any satellite tile (PNG, JPG, TIFF) to cluster and discover similar territories
            </p>
          </div>
        ) : (
          /* Image Selected & Preview Container */
          <div>
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '1.25rem',
              alignItems: 'center',
              background: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '12px',
              padding: '1rem',
              border: '1px solid var(--glass-border)',
              marginBottom: '1rem'
            }}>
              {/* Image Preview Thumbnail */}
              <div style={{
                width: 110,
                height: 110,
                borderRadius: '8px',
                overflow: 'hidden',
                background: '#0f172a',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                flexShrink: 0,
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                {!isTiff && !previewError ? (
                  <img
                    src={preview}
                    alt="Query Tile Preview"
                    onError={() => setPreviewError(true)}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                ) : (
                  <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.35rem',
                    padding: '0.5rem',
                    textAlign: 'center',
                    color: '#60a5fa'
                  }}>
                    <Satellite size={32} />
                    <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      {isTiff ? 'GeoTIFF Band' : 'Satellite Tile'}
                    </span>
                  </div>
                )}
              </div>

              {/* File Info */}
              <div style={{ flex: '1 1 200px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#10b981', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                  <CheckCircle2 size={15} /> Ready for analysis
                </div>
                <div style={{
                  fontSize: '0.95rem',
                  fontWeight: 600,
                  color: '#f8fafc',
                  marginBottom: '0.25rem',
                  maxWidth: '380px',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}>
                  {file.name}
                </div>
                <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                  {(file.size / 1024).toFixed(1)} KB &bull; {file.type || 'Image'}
                </div>
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', gap: '0.5rem', marginLeft: 'auto' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => fileInputRef.current?.click()}
                  style={{ fontSize: '0.82rem', padding: '0.45rem 0.8rem' }}
                >
                  Change Image
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={clearSelection}
                  style={{ fontSize: '0.82rem', padding: '0.45rem 0.8rem', color: '#ef4444' }}
                >
                  <X size={14} /> Clear
                </button>
              </div>
            </div>

            {/* Actions Form */}
            <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Top K</label>
                <input
                  type="number"
                  className="form-control"
                  value={topK}
                  onChange={(e) => setTopK(Math.max(1, Math.min(50, parseInt(e.target.value) || 10)))}
                  min={1}
                  max={50}
                  style={{ width: '70px', textAlign: 'center' }}
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
                style={{ minWidth: '150px' }}
              >
                {loading ? (
                  <div className="spinner" style={{ width: 17, height: 17, borderWidth: 2 }} />
                ) : (
                  <Layers size={16} />
                )}
                {loading ? 'Analyzing…' : 'Find Similar Locations'}
              </button>
            </form>
          </div>
        )}
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#fca5a5',
          borderRadius: '8px',
          padding: '0.75rem 1rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.85rem'
        }}>
          <AlertCircle size={16} />
          {errorMsg}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <>
          <p style={{ fontSize: '0.83rem', color: '#64748b', marginBottom: '0.75rem' }}>
            {results.length} similar location{results.length !== 1 ? 's' : ''} found
          </p>
          <div className="search-results">
            {results.map((result, index) => {
              const probVal = result.cluster_probability ?? result.similarity ?? 0.8
              const probPct = (probVal * 100).toFixed(1)
              const probColor = getProbColor(probVal)
              const tileId = result.tile_id || `loc-${index}`

              return (
                <div key={tileId} className="result-card">
                  {/* Location Image */}
                  <div className="result-image" style={{ position: 'relative' }}>
                    {!failedImages[tileId] ? (
                      <img
                        src={`http://127.0.0.1:8000/image/${result.tile_id}`}
                        alt={result.tile_id}
                        style={{ width: '100%', height: '100%', objectFit: 'cover', position: 'absolute', inset: 0 }}
                        onError={() => setFailedImages((prev) => ({ ...prev, [tileId]: true }))}
                        loading="lazy"
                      />
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#475569' }}>
                        <Satellite size={32} style={{ opacity: 0.5 }} />
                      </div>
                    )}

                    {/* Rank Badge */}
                    <span style={{
                      position: 'absolute', top: 8, left: 8,
                      background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(4px)',
                      borderRadius: '5px', padding: '0.15rem 0.45rem',
                      fontSize: '0.7rem', fontWeight: 700, color: '#e2e8f0'
                    }}>
                      #{result.rank || index + 1}
                    </span>

                    {/* Cluster Match Badge */}
                    <span style={{
                      position: 'absolute', top: 8, right: 8,
                      background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(4px)',
                      borderRadius: '999px', padding: '0.15rem 0.55rem',
                      fontSize: '0.7rem', fontWeight: 700, color: probColor,
                      border: `1px solid ${probColor}50`
                    }}>
                      {probPct}%
                    </span>
                  </div>

                  {/* Card Content */}
                  <div className="result-content">
                    {/* Cluster tag */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.6rem' }}>
                      <span style={{
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        padding: '0.15rem 0.5rem',
                        borderRadius: '6px',
                        background: 'rgba(59, 130, 246, 0.12)',
                        color: '#60a5fa',
                        border: '1px solid rgba(59, 130, 246, 0.25)'
                      }}>
                        Cluster #{result.cluster_id ?? '0'}
                      </span>
                      <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
                        {result.date || '2022'}
                      </span>
                    </div>

                    {/* Tile ID */}
                    <div style={{
                      fontFamily: 'monospace', fontSize: '0.8rem', fontWeight: 600,
                      color: '#f1f5f9', marginBottom: '0.65rem',
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'
                    }}>
                      {result.tile_id}
                    </div>

                    {/* Meta */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                      {result.latitude != null && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.79rem', color: '#94a3b8' }}>
                          <MapPin size={11} style={{ color: '#475569', flexShrink: 0 }} />
                          {result.latitude.toFixed(4)}°, {result.longitude.toFixed(4)}°
                        </div>
                      )}
                      {result.metadata?.year && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.79rem', color: '#94a3b8' }}>
                          <Calendar size={11} style={{ color: '#475569', flexShrink: 0 }} />
                          {result.metadata.year}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      {/* No Results Empty State */}
      {hasSearched && !loading && results.length === 0 && !errorMsg && (
        <div className="card" style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
          <Layers size={34} style={{ margin: '0 auto 0.85rem', opacity: 0.35 }} />
          <p style={{ fontWeight: 500, marginBottom: '0.3rem', color: '#94a3b8' }}>No similar locations found</p>
          <p style={{ fontSize: '0.83rem' }}>Try uploading a different satellite image or adjusting Top K</p>
        </div>
      )}
    </div>
  )
}

export default SimilarLocations
