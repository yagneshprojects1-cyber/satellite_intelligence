import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import {
  UploadCloud, FolderOpen, Activity, Layers,
  AlertTriangle, CheckCircle2, Eye, X,
  MapPin, Calendar, Cpu, RefreshCw, Download
} from 'lucide-react'
import { formatDateFriendly } from '../utils/locationFormatter'

const API = 'http://127.0.0.1:8000'

// Sample files the analyst can download and re-upload
const SAMPLE_FILES = [
  { name: 'construction_sector_2024.tif', label: 'Construction Sector', badge: 'Construction', color: '#ef4444' },
  { name: 'vegetation_clearance_2024.tif', label: 'Vegetation Clearance', badge: 'Clearance', color: '#f59e0b' },
  { name: 'water_expansion_2024.tif', label: 'Water Body Expansion', badge: 'Water Variation', color: '#06b6d4' },
  { name: 'road_development_2024.tif', label: 'Road Development', badge: 'Road Dev.', color: '#a855f7' },
  { name: 'stable_sector_2024.tif', label: 'Stable Sector (No Change)', badge: 'No Change', color: '#10b981' },
]

function badgeStyle(type) {
  const styles = {
    'Construction':     { bg: 'rgba(239,68,68,0.15)',   border: '#ef4444', text: '#fca5a5' },
    'Clearance':        { bg: 'rgba(245,158,11,0.15)',  border: '#f59e0b', text: '#fde68a' },
    'Water Variation':  { bg: 'rgba(6,182,212,0.15)',   border: '#06b6d4', text: '#67e8f9' },
    'Road Development': { bg: 'rgba(168,85,247,0.15)',  border: '#a855f7', text: '#e9d5ff' },
    'No Change':        { bg: 'rgba(16,185,129,0.15)',  border: '#10b981', text: '#6ee7b7' },
  }
  return styles[type] || { bg: 'rgba(100,116,139,0.15)', border: '#64748b', text: '#cbd5e1' }
}

export default function ChangeAnalysis() {
  const [file, setFile]             = useState(null)
  const [preview, setPreview]       = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [analyzing, setAnalyzing]   = useState(false)
  const [result, setResult]         = useState(null)
  const [error, setError]           = useState(null)
  const [sliderPos, setSliderPos]   = useState(50)
  const [modalOpen, setModalOpen]   = useState(false)

  const fileInputRef = useRef(null)
  const compareRef   = useRef(null)

  // Generate upload preview via /convert-preview for TIFFs
  useEffect(() => {
    if (!file) { setPreview(null); return }
    const isTiff = file.name?.toLowerCase().endsWith('.tif') || file.name?.toLowerCase().endsWith('.tiff')
    if (isTiff) {
      const fd = new FormData()
      fd.append('file', file)
      axios.post(`${API}/convert-preview`, fd)
        .then(r => setPreview(r.data?.preview_url || null))
        .catch(() => setPreview(null))
    } else {
      const reader = new FileReader()
      reader.onload = e => setPreview(e.target.result)
      reader.readAsDataURL(file)
    }
  }, [file])

  // Reset slider when modal opens
  useEffect(() => { if (modalOpen) setSliderPos(50) }, [modalOpen])

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f) acceptFile(f)
  }

  const handleFileChange = (e) => {
    const f = e.target.files?.[0]
    if (f) acceptFile(f)
  }

  const acceptFile = (f) => {
    const name = f.name.toLowerCase()
    const ok = f.type.startsWith('image/') || name.endsWith('.tif') || name.endsWith('.tiff')
    if (!ok) { setError('Please upload a GeoTIFF or image file.'); return }
    setFile(f)
    setResult(null)
    setError(null)
  }

  const loadSample = async (filename) => {
    try {
      const res = await fetch(`${API}/static-sample/${filename}`)
      if (!res.ok) throw new Error('Not found')
      const blob = await res.blob()
      const f = new File([blob], filename, { type: 'image/tiff' })
      acceptFile(f)
    } catch {
      setError(`Sample file "${filename}" not available from server. Download and upload manually.`)
    }
  }

  const downloadSample = (filename) => {
    const a = document.createElement('a')
    a.href = `${API}/static-sample/${filename}`
    a.download = filename
    a.click()
  }

  const runAnalysis = async () => {
    if (!file) return
    setAnalyzing(true)
    setError(null)
    setResult(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const r = await axios.post(`${API}/change-analysis-upload`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setResult(r.data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Analysis failed. Check backend.')
    } finally {
      setAnalyzing(false)
    }
  }

  const updateSlider = (clientX) => {
    const el = compareRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    setSliderPos(Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100)))
  }

  const bd = result ? badgeStyle(result.change_type) : {}

  return (
    <div className="fade-in">
      {/* Page Header */}
      <div style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.35rem' }}>
          <Activity size={22} style={{ color: '#a855f7' }} />
          Multi-Temporal Change Analysis
        </h1>
        <p style={{ color: 'var(--text-muted, #94a3b8)', fontSize: '0.9rem', margin: 0 }}>
          Upload a GeoTIFF satellite tile. The system automatically locates the matching historical baseline,
          computes spectral change and classifies the change type.
        </p>
      </div>

      <div>

        {/* Upload + Result — full width */}
        <div>
          {/* Drop Zone */}
          <div
            className="card"
            style={{ padding: '1.5rem', marginBottom: '1.25rem' }}
            onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
          >
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <UploadCloud size={16} style={{ color: '#a855f7' }} /> Upload Target Satellite Tile
            </h3>

            {!file ? (
              <div
                onClick={() => fileInputRef.current?.click()}
                className="dropzone-area"
                style={{
                  border: `2px dashed ${isDragging ? '#a855f7' : 'rgba(168,85,247,0.4)'}`,
                  borderRadius: '12px',
                  padding: '2.5rem 1.5rem',
                  textAlign: 'center',
                  cursor: 'pointer',
                  background: isDragging ? 'rgba(168,85,247,0.06)' : 'transparent',
                  transition: 'all 0.2s ease'
                }}
              >
                <UploadCloud size={40} style={{ color: '#a855f7', marginBottom: '0.75rem', opacity: 0.7 }} />
                <p style={{ fontWeight: 600, marginBottom: '0.3rem' }}>
                  Drag & drop a GeoTIFF here, or click to browse
                </p>
                <p style={{ fontSize: '0.82rem', color: '#64748b', margin: 0 }}>
                  Accepts .tif / .tiff satellite imagery bands (Sentinel-2, etc.)
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".tif,.tiff,image/*"
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                />
              </div>
            ) : (
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                {/* Thumbnail */}
                <div style={{ flex: '0 0 160px', height: 160, borderRadius: 8, overflow: 'hidden', background: '#0f172a', border: '1px solid #334155', position: 'relative' }}>
                  {preview
                    ? <img src={preview} alt="preview" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    : <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', flexDirection: 'column', gap: '0.5rem', color: '#64748b', fontSize: '0.78rem' }}>
                        <RefreshCw size={22} className="spin" />Loading preview…
                      </div>
                  }
                </div>

                {/* File info + actions */}
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontWeight: 700, marginBottom: '0.25rem', wordBreak: 'break-all' }}>{file.name}</div>
                  <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '1rem' }}>
                    {(file.size / 1024).toFixed(0)} KB — satellite imagery tile
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <button
                      className="btn btn-primary"
                      onClick={runAnalysis}
                      disabled={analyzing}
                      style={{ padding: '0.55rem 1.1rem', fontSize: '0.87rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                    >
                      {analyzing
                        ? <><RefreshCw size={14} className="spin" /> Analyzing…</>
                        : <><Activity size={14} /> Run Change Analysis</>}
                    </button>
                    <button
                      className="btn btn-secondary"
                      onClick={() => { setFile(null); setPreview(null); setResult(null); setError(null) }}
                      style={{ padding: '0.55rem 0.85rem', fontSize: '0.87rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                    >
                      <X size={14} /> Clear
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Error message */}
          {error && (
            <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid #ef4444', color: '#fca5a5', padding: '0.75rem 1rem', borderRadius: '10px', marginBottom: '1.25rem', fontSize: '0.85rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <AlertTriangle size={16} /> {error}
            </div>
          )}

          {/* Analyzing spinner */}
          {analyzing && (
            <div className="card" style={{ padding: '2rem', textAlign: 'center', marginBottom: '1.25rem' }}>
              <RefreshCw size={32} className="spin" style={{ color: '#a855f7', marginBottom: '0.75rem' }} />
              <p style={{ fontWeight: 600, marginBottom: '0.3rem' }}>Locating historical baseline…</p>
              <p style={{ fontSize: '0.82rem', color: '#64748b', margin: 0 }}>
                Finding nearest archived tile at the same location &amp; running multi-spectral change classifier
              </p>
            </div>
          )}

          {/* Result Panel */}
          {result && !analyzing && (
            <div className="card" style={{ padding: '1.5rem', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <CheckCircle2 size={18} style={{ color: '#10b981' }} /> Analysis Complete
                </h3>
                <span style={{
                  ...bd,
                  background: bd.bg, borderColor: bd.border, color: bd.text,
                  fontSize: '0.8rem', fontWeight: 700, padding: '0.25rem 0.75rem',
                  borderRadius: '999px', border: `1px solid ${bd.border}`,
                  display: 'inline-flex', alignItems: 'center', gap: '0.35rem'
                }}>
                  <Activity size={13} /> {result.change_type || 'No Change'}
                </span>
              </div>

              {/* Before / After images */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <div style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid #334155', background: '#0f172a', position: 'relative' }}>
                  {result.before_preview
                    ? <img src={result.before_preview} alt="before" style={{ width: '100%', height: 200, objectFit: 'cover', display: 'block' }} />
                    : <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: '0.8rem' }}>No baseline image</div>}
                  <span style={{ position: 'absolute', bottom: 8, left: 8, background: 'rgba(0,0,0,0.75)', color: '#94a3b8', fontSize: '0.7rem', padding: '0.15rem 0.4rem', borderRadius: 4, fontWeight: 700 }}>
                    BEFORE · {formatDateFriendly(result.before_date)}
                  </span>
                </div>

                <div style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid #334155', background: '#0f172a', position: 'relative' }}>
                  {result.after_preview
                    ? <img src={result.after_preview} alt="after" style={{ width: '100%', height: 200, objectFit: 'cover', display: 'block' }} />
                    : <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: '0.8rem' }}>No upload preview</div>}
                  <span style={{ position: 'absolute', bottom: 8, right: 8, background: 'rgba(0,0,0,0.75)', color: '#06b6d4', fontSize: '0.7rem', padding: '0.15rem 0.4rem', borderRadius: 4, fontWeight: 700 }}>
                    AFTER · Uploaded
                  </span>
                </div>
              </div>

              {/* Inspect Slider Button */}
              <button
                className="btn btn-secondary"
                onClick={() => setModalOpen(true)}
                style={{ width: '100%', justifyContent: 'center', marginBottom: '1.25rem', gap: '0.5rem', padding: '0.65rem' }}
              >
                <Eye size={15} /> Open Interactive Comparison Slider
              </button>

              {/* Metrics */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.75rem', background: 'rgba(0,0,0,0.15)', borderRadius: 10, padding: '1rem', border: '1px solid rgba(255,255,255,0.06)' }}>
                <div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.2rem' }}>Change Magnitude</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: result.change_percentage > 15 ? '#ef4444' : result.change_percentage > 5 ? '#f59e0b' : '#10b981' }}>
                    {result.change_percentage?.toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.2rem' }}>AI Confidence</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#38bdf8' }}>{((result.confidence || 0) * 100).toFixed(0)}%</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.2rem' }}>Baseline Tile</div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#f1f5f9', wordBreak: 'break-all' }}>{result.before_tile_id || '—'}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.2rem' }}>Detection Method</div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#f1f5f9' }}>{result.method || 'ChangeFormer'}</div>
                </div>
                {result.upload_lat && (
                  <div>
                    <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.2rem' }}>Upload Coordinates</div>
                    <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#f1f5f9' }}>
                      {result.upload_lat?.toFixed(4)}°N, {result.upload_lon?.toFixed(4)}°E
                    </div>
                  </div>
                )}
                <div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.2rem' }}>Sensor</div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#f1f5f9' }}>{result.sensor || 'Sentinel-2'}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Comparison Slider Modal */}
      {modalOpen && result && (
        <div
          style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem' }}
          onClick={() => setModalOpen(false)}
        >
          <div
            style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '14px', maxWidth: '780px', width: '100%', overflow: 'hidden', boxShadow: '0 25px 50px rgba(0,0,0,0.6)' }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem 1.25rem', borderBottom: '1px solid #334155' }}>
              <h3 style={{ fontSize: '1rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Layers size={18} style={{ color: '#06b6d4' }} /> Before / After Comparison — {result.change_type}
              </h3>
              <button className="btn btn-secondary" onClick={() => setModalOpen(false)} style={{ padding: '0.2rem 0.6rem' }}>✕</button>
            </div>

            <div style={{ padding: '1.25rem' }}>
              {/* Slider compare area */}
              <div
                ref={compareRef}
                onMouseDown={e => updateSlider(e.clientX)}
                onMouseMove={e => { if (e.buttons === 1) updateSlider(e.clientX) }}
                onTouchMove={e => { if (e.touches[0]) updateSlider(e.touches[0].clientX) }}
                style={{ position: 'relative', width: '100%', height: 360, borderRadius: 10, overflow: 'hidden', border: '1px solid #334155', background: '#0f172a', cursor: 'ew-resize', userSelect: 'none' }}
              >
                {/* BEFORE (baseline) — full background */}
                {result.before_preview
                  ? <img src={result.before_preview} alt="before" draggable={false} style={{ width: '100%', height: '100%', objectFit: 'cover', position: 'absolute', inset: 0 }} />
                  : <div style={{ position: 'absolute', inset: 0, background: '#111827', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>No baseline</div>}

                {/* AFTER (uploaded) — clipped by slider */}
                {result.after_preview && (
                  <img
                    src={result.after_preview}
                    alt="after"
                    draggable={false}
                    style={{ width: '100%', height: '100%', objectFit: 'cover', position: 'absolute', inset: 0, clipPath: `inset(0 ${100 - sliderPos}% 0 0)` }}
                  />
                )}

                {/* Divider handle */}
                <div style={{ position: 'absolute', top: 0, bottom: 0, left: `${sliderPos}%`, width: 2, background: '#06b6d4', transform: 'translateX(-50%)', pointerEvents: 'none', zIndex: 10 }}>
                  <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: 26, height: 26, borderRadius: '50%', background: '#06b6d4', border: '2px solid #fff', boxShadow: '0 0 10px rgba(6,182,212,0.9)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '12px', fontWeight: 'bold' }}>↔</div>
                </div>

                <div style={{ position: 'absolute', top: 10, left: 10, background: 'rgba(15,23,42,0.85)', padding: '0.25rem 0.65rem', borderRadius: 4, fontSize: '0.75rem', color: '#94a3b8', fontWeight: 700, zIndex: 10, border: '1px solid rgba(255,255,255,0.1)' }}>
                  BEFORE · {formatDateFriendly(result.before_date)}
                </div>
                <div style={{ position: 'absolute', top: 10, right: 10, background: 'rgba(15,23,42,0.85)', padding: '0.25rem 0.65rem', borderRadius: 4, fontSize: '0.75rem', color: '#06b6d4', fontWeight: 700, zIndex: 10, border: '1px solid rgba(6,182,212,0.3)' }}>
                  AFTER · Uploaded
                </div>
              </div>

              <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Baseline</span>
                <input type="range" min="0" max="100" value={sliderPos} onChange={e => setSliderPos(Number(e.target.value))} style={{ flex: 1, accentColor: '#06b6d4' }} />
                <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Uploaded</span>
              </div>

              <div style={{ marginTop: '1.25rem', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', background: '#0f172a', padding: '0.85rem', borderRadius: 8, border: '1px solid #334155', fontSize: '0.82rem' }}>
                <div><span style={{ color: '#94a3b8' }}>Change Type: </span><strong style={{ color: '#38bdf8' }}>{result.change_type}</strong></div>
                <div><span style={{ color: '#94a3b8' }}>Magnitude: </span><strong style={{ color: '#f59e0b' }}>{result.change_percentage?.toFixed(2)}%</strong></div>
                <div><span style={{ color: '#94a3b8' }}>Confidence: </span><strong style={{ color: '#10b981' }}>{((result.confidence || 0) * 100).toFixed(0)}%</strong></div>
              </div>
            </div>

            <div style={{ padding: '1rem 1.25rem', background: '#0f172a', borderTop: '1px solid #334155', display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setModalOpen(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
