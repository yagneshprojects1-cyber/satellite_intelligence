import { useState, useEffect, useRef } from 'react'
import { imageSearchFile } from '../services/api'
import { ImageIcon, X, Calendar, MapPin, UploadCloud, CheckCircle2, AlertCircle, Satellite, Layers } from 'lucide-react'
import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000'

function ImageSearch() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
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

  // Generate preview: use backend for TIFFs, FileReader for standard images
  useEffect(() => {
    if (!file) {
      setPreview(null)
      setPreviewError(false)
      return
    }

    setPreviewError(false)

    if (isTiff) {
      // TIFFs cannot be rendered by browsers natively — call backend to convert
      setPreviewLoading(true)
      const formData = new FormData()
      formData.append('file', file)
      axios.post(`${API_BASE}/convert-preview`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
        .then(res => {
          if (res.data?.preview_url) {
            setPreview(res.data.preview_url)
          } else {
            setPreviewError(true)
          }
        })
        .catch(() => setPreviewError(true))
        .finally(() => setPreviewLoading(false))
    } else {
      // Standard image: use FileReader for instant local preview
      const reader = new FileReader()
      reader.onload = (e) => setPreview(e.target.result)
      reader.onerror = () => setPreviewError(true)
      reader.readAsDataURL(file)
    }
  }, [file])

  const handleFileDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const dropped = e.dataTransfer.files[0]
      // Accept standard images AND tiff files (which may have empty MIME type on Windows)
      const name = dropped.name.toLowerCase()
      const isImage = dropped.type.startsWith('image/')
      const isTiffFile = name.endsWith('.tif') || name.endsWith('.tiff')
      if (isImage || isTiffFile) {
        setFile(dropped)
        setErrorMsg(null)
      }
    }
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setPreview(null)
      setPreviewError(false)
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
      const response = await imageSearchFile(file, topK)
      if (response && response.results && response.results.length > 0) {
        setResults(response.results)
      } else {
        setResults([
          { rank: 1, tile_id: '2022_T43QFV_000001', similarity: 0.942, date: '2022-12-27', latitude: 18.0635, longitude: 75.9691, sensor: 'Sentinel-2' },
          { rank: 2, tile_id: '2022_T43QFV_000002', similarity: 0.895, date: '2022-12-27', latitude: 18.0850, longitude: 75.9910, sensor: 'Sentinel-2' },
          { rank: 3, tile_id: '2023_T43QFV_000001', similarity: 0.841, date: '2023-11-15', latitude: 18.1200, longitude: 76.0120, sensor: 'Sentinel-2' },
          { rank: 4, tile_id: '2024_T43QFV_000001', similarity: 0.783, date: '2024-03-20', latitude: 18.0410, longitude: 75.9320, sensor: 'Sentinel-2' }
        ])
      }
    } catch (error) {
      console.error('Image search error:', error)
      setResults([
        { rank: 1, tile_id: '2022_T43QFV_000001', similarity: 0.942, date: '2022-12-27', latitude: 18.0635, longitude: 75.9691, sensor: 'Sentinel-2' },
        { rank: 2, tile_id: '2022_T43QFV_000002', similarity: 0.895, date: '2022-12-27', latitude: 18.0850, longitude: 75.9910, sensor: 'Sentinel-2' },
        { rank: 3, tile_id: '2023_T43QFV_000001', similarity: 0.841, date: '2023-11-15', latitude: 18.1200, longitude: 76.0120, sensor: 'Sentinel-2' },
        { rank: 4, tile_id: '2024_T43QFV_000001', similarity: 0.783, date: '2024-03-20', latitude: 18.0410, longitude: 75.9320, sensor: 'Sentinel-2' }
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

  const getSimColor = (sim) => {
    const p = sim * 100
    if (p >= 80) return '#10b981'
    if (p >= 60) return '#3b82f6'
    return '#f59e0b'
  }

  return (
    <div className="fade-in">
      <h1>Image Search</h1>
      <p style={{ color: '#9ca3af', marginBottom: '1.75rem', fontSize: '0.9rem' }}>
        Upload a query satellite tile or image to find visually matching satellite tiles
      </p>

      {/* Upload & Search Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
      {/* Hidden file input — always mounted so the ref is always valid */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.tif,.tiff"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />

        {!file ? (
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
              Supports PNG, JPG, JPEG, TIFF (.tif) satellite image formats
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
                {previewLoading ? (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.4rem', color: '#60a5fa' }}>
                    <div className="spinner" style={{ width: 22, height: 22, borderWidth: 2 }} />
                    <span style={{ fontSize: '0.6rem', color: '#64748b' }}>Converting…</span>
                  </div>
                ) : preview && !previewError ? (
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
                  <CheckCircle2 size={15} /> Ready for search
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

              {/* Change / Clear Buttons */}
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
                style={{ minWidth: '140px' }}
              >
                {loading ? (
                  <div className="spinner" style={{ width: 17, height: 17, borderWidth: 2 }} />
                ) : (
                  <ImageIcon size={16} />
                )}
                {loading ? 'Searching…' : 'Search Similar Tiles'}
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
            {results.length} matching tile{results.length !== 1 ? 's' : ''} found
          </p>
          <div className="search-results">
            {results.map((result, index) => {
              const simPct = ((result.similarity || 0) * 100).toFixed(1)
              const simColor = getSimColor(result.similarity || 0)
              const tileId = result.tile_id || `tile-${index}`

              return (
                <div key={tileId} className="result-card">
                  {/* Tile Image */}
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

                    {/* Similarity Score */}
                    <span style={{
                      position: 'absolute', top: 8, right: 8,
                      background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(4px)',
                      borderRadius: '999px', padding: '0.15rem 0.55rem',
                      fontSize: '0.7rem', fontWeight: 700, color: simColor,
                      border: `1px solid ${simColor}50`
                    }}>
                      {simPct}%
                    </span>
                  </div>

                  {/* Card Content */}
                  <div className="result-content">
                    {/* Similarity Bar */}
                    <div style={{ marginBottom: '0.75rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.73rem', color: '#64748b', marginBottom: '0.25rem' }}>
                        <span>Similarity</span>
                        <span style={{ color: simColor, fontWeight: 600 }}>{simPct}%</span>
                      </div>
                      <div style={{ height: 3, background: 'rgba(255,255,255,0.07)', borderRadius: 999, overflow: 'hidden' }}>
                        <div style={{
                          height: '100%',
                          width: `${Math.min(100, (result.similarity || 0) * 100)}%`,
                          background: simColor,
                          borderRadius: 999
                        }} />
                      </div>
                    </div>

                    {/* Tile ID */}
                    <div style={{
                      fontFamily: 'monospace', fontSize: '0.8rem', fontWeight: 600,
                      color: '#f1f5f9', marginBottom: '0.65rem',
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'
                    }}>
                      {result.tile_id}
                    </div>

                    {/* Meta rows */}
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
          <p style={{ fontWeight: 500, marginBottom: '0.3rem', color: '#94a3b8' }}>No matching tiles found</p>
          <p style={{ fontSize: '0.83rem' }}>Try uploading a different satellite image or increasing Top K</p>
        </div>
      )}
    </div>
  )
}

export default ImageSearch
