import { useState, useEffect } from 'react'
import { getEarliestChanges } from '../services/api'
import {
  MapPin, Clock, TrendingUp, Activity, Calendar,
  AlertTriangle, CheckCircle2, Eye, RefreshCw, Radar,
  Satellite, Shield
} from 'lucide-react'
import { formatDateFriendly } from '../utils/locationFormatter'

// Convert bbox center → human-readable sector name
function bboxToSectorName(locationRef, index) {
  if (!locationRef) return `Monitoring Sector ${index + 1}`

  // Try to parse JSON bbox string
  let bbox = locationRef
  if (typeof locationRef === 'string') {
    try { bbox = JSON.parse(locationRef) } catch (_) { /* not JSON */ }
  }

  if (typeof bbox === 'object' && bbox !== null) {
    const lat = ((bbox.min_lat || 0) + (bbox.max_lat || 0)) / 2
    const lon = ((bbox.min_lon || 0) + (bbox.max_lon || 0)) / 2
    const latDir = lat >= 0 ? 'N' : 'S'
    const lonDir = lon >= 0 ? 'E' : 'W'
    return `${Math.abs(lat).toFixed(3)}°${latDir}, ${Math.abs(lon).toFixed(3)}°${lonDir}`
  }

  // Already a human string
  if (typeof bbox === 'string' && !bbox.startsWith('{')) {
    return bbox
  }

  return `Monitoring Sector ${index + 1}`
}

function bboxToCoordString(locationRef) {
  if (!locationRef) return null
  let bbox = locationRef
  if (typeof locationRef === 'string') {
    try { bbox = JSON.parse(locationRef) } catch (_) { return null }
  }
  if (typeof bbox === 'object' && bbox !== null && bbox.min_lat != null) {
    const span_lat = Math.abs((bbox.max_lat - bbox.min_lat) * 111).toFixed(1)
    const span_lon = Math.abs((bbox.max_lon - bbox.min_lon) * 111).toFixed(1)
    return `${span_lat} × ${span_lon} km coverage area`
  }
  return null
}

function EarliestChange() {
  const [earliestChanges, setEarliestChanges] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const [viewFilter, setViewFilter] = useState('all')

  useEffect(() => { loadEarliestChanges() }, [])

  const loadEarliestChanges = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    else setLoading(true)
    try {
      const response = await getEarliestChanges()
      setEarliestChanges(response)
    } catch (error) {
      console.error('Error loading earliest changes:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const getChangeColor = (pct) => {
    if (pct >= 30) return '#ef4444'
    if (pct >= 10) return '#f59e0b'
    if (pct > 0) return '#3b82f6'
    return '#10b981'
  }

  const getChangeLabel = (result) => {
    const persistence = result.persistence || 'No Change'
    if (persistence === 'Persistent') return { label: 'Persistent Change', color: '#ef4444', bg: 'rgba(239,68,68,0.12)' }
    if (persistence === 'Transient') return { label: 'Transient Activity', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' }
    if (persistence === 'Emerging') return { label: 'Emerging Change', color: '#3b82f6', bg: 'rgba(59,130,246,0.12)' }
    return { label: 'Stable — Below Threshold', color: '#10b981', bg: 'rgba(16,185,129,0.12)' }
  }

  const getPersistenceInfo = (type) => {
    if (type === 'Persistent') return { color: '#ef4444', icon: '🔴', label: 'Persistent Change' }
    if (type === 'Transient') return { color: '#f59e0b', icon: '🟡', label: 'Transient Activity' }
    if (type === 'Emerging') return { color: '#3b82f6', icon: '🔵', label: 'Emerging Change' }
    return { color: '#10b981', icon: '🟢', label: 'Stable Zone' }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '5rem 2rem', gap: '1rem' }}>
        <div className="spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
        <p style={{ color: '#64748b', margin: 0 }}>Loading temporal change records…</p>
      </div>
    )
  }

  const results = earliestChanges?.results || []
  const persistentCount = results.filter(r => r.persistence === 'Persistent').length
  const transientCount = results.filter(r => r.persistence === 'Transient' || r.persistence === 'Emerging').length
  const stableCount = results.filter(r => !r.persistence || r.persistence === 'No Change').length
  const changedResults = results.filter(r => r.persistence && r.persistence !== 'No Change')
  const avgChange = results.length > 0
    ? (results.reduce((acc, r) => acc + (r.change_percentage || 0), 0) / results.length).toFixed(1)
    : 0

  const persistenceRank = { Persistent: 0, Emerging: 1, Transient: 2, 'No Change': 3 }
  const visibleResults = [...results]
    .filter((r) => {
      if (viewFilter === 'changed') return r.persistence && r.persistence !== 'No Change'
      if (viewFilter === 'stable') return !r.persistence || r.persistence === 'No Change'
      return true
    })
    .sort((a, b) => {
      const ra = persistenceRank[a.persistence] ?? 4
      const rb = persistenceRank[b.persistence] ?? 4
      if (ra !== rb) return ra - rb
      return (b.change_percentage || 0) - (a.change_percentage || 0)
    })

  return (
    <div className="fade-in">
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.75rem' }}>
        <div>
          <h1 style={{ marginBottom: '0.35rem' }}>
            <Radar size={22} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '0.5rem', color: '#60a5fa' }} />
            Temporal Change Monitoring
          </h1>
          <p style={{ color: '#9ca3af', fontSize: '0.9rem', margin: 0 }}>
            First detected and persistent changes across all monitored geographic sectors
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={() => loadEarliestChanges(true)}
          disabled={refreshing}
          style={{ fontSize: '0.84rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
        >
          <RefreshCw size={14} className={refreshing ? 'spin' : ''} />
          {refreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {/* Summary Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '1.75rem' }}>
        <div className="card" style={{ padding: '1.1rem 1.25rem', borderLeft: '3px solid #60a5fa' }}>
          <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.35rem', letterSpacing: '0.04em' }}>
            Monitored Sectors
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#60a5fa' }}>
            {earliestChanges?.total_locations || results.length}
          </div>
        </div>
        <div className="card" style={{ padding: '1.1rem 1.25rem', borderLeft: '3px solid #ef4444' }}>
          <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.35rem', letterSpacing: '0.04em' }}>
            Persistent Changes
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#ef4444' }}>{persistentCount}</div>
        </div>
        <div className="card" style={{ padding: '1.1rem 1.25rem', borderLeft: '3px solid #f59e0b' }}>
          <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.35rem', letterSpacing: '0.04em' }}>
            Transient Events
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#f59e0b' }}>{transientCount}</div>
        </div>
        <div className="card" style={{ padding: '1.1rem 1.25rem', borderLeft: '3px solid #10b981' }}>
          <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.35rem', letterSpacing: '0.04em' }}>
            Stable Zones
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#10b981' }}>{stableCount}</div>
        </div>
      </div>

      {/* No Results */}
      {results.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
          <div style={{
            width: 64, height: 64, borderRadius: '50%',
            background: 'rgba(96, 165, 250, 0.1)', display: 'flex',
            alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.25rem'
          }}>
            <Radar size={30} color="#60a5fa" />
          </div>
          <p style={{ fontWeight: 600, color: '#f1f5f9', marginBottom: '0.5rem' }}>
            No Monitoring Records Available
          </p>
          <p style={{ fontSize: '0.85rem', color: '#64748b', maxWidth: 400, margin: '0 auto' }}>
            Earliest change analysis has not been run yet, or no significant events were detected across the monitored timeframe.
          </p>
        </div>
      )}

      {/* Results Grid */}
      {results.length > 0 && (
        <>
          <p style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: '0.85rem' }}>
            Showing {visibleResults.length} of {results.length} monitored location{results.length !== 1 ? 's' : ''} · Avg measured intensity: <strong style={{ color: '#f1f5f9' }}>{avgChange}%</strong>
            {changedResults.length === 0 ? ' · No pair crossed the change threshold' : ''}
          </p>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            {[
              ['all', `All (${results.length})`],
              ['changed', `Threshold crossings (${changedResults.length})`],
              ['stable', `Stable (${stableCount})`],
            ].map(([id, label]) => (
              <button
                key={id}
                className="btn btn-secondary"
                onClick={() => setViewFilter(id)}
                style={{
                  fontSize: '0.78rem',
                  borderColor: viewFilter === id ? '#60a5fa' : undefined,
                  color: viewFilter === id ? '#60a5fa' : undefined
                }}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="search-results">
            {visibleResults.map((result, index) => {
              const changePct = result.change_percentage || 0
              const changeColor = getChangeColor(changePct)
              const changeLabel = getChangeLabel(result)
              const confPct = ((result.confidence || 0) * 100).toFixed(0)
              const persistInfo = getPersistenceInfo(result.persistence)
              const isStable = !result.persistence || result.persistence === 'No Change'
              const sectorName = bboxToSectorName(result.location_reference, index)
              const coverageStr = bboxToCoordString(result.location_reference)

              // Date display
              const hasEarliestDate = result.earliest_change_date && result.earliest_change_date !== 'N/A'
              const hasBeforeAfter = (result.before_date && result.before_date !== 'N/A') ||
                                     (result.after_date && result.after_date !== 'N/A')

              const beforeYr = result.before_date ? result.before_date.slice(0, 4) : '2022'
              const afterYr = result.after_date ? result.after_date.slice(0, 4) : '2024'
              const monitoringLabel = (hasBeforeAfter && result.before_date !== result.after_date)
                ? `${beforeYr} → ${afterYr} Monitoring Period`
                : 'Multi-Year Monitoring Active'

              return (
                <div key={index} className="result-card" style={{ cursor: 'default' }}>
                  {/* Header: Sector Name */}
                  <div style={{ padding: '1rem 1rem 0' }}>
                    <div style={{
                      display: 'flex', alignItems: 'flex-start', gap: '0.6rem',
                      marginBottom: '0.65rem'
                    }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: '8px',
                        background: `${changeColor}18`, display: 'flex',
                        alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '0.1rem'
                      }}>
                        <MapPin size={14} color={changeColor} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          fontSize: '0.9rem', fontWeight: 700, color: '#f1f5f9',
                          marginBottom: '0.15rem', lineHeight: 1.3
                        }}>
                          {sectorName}
                        </div>
                        {coverageStr && (
                          <div style={{ fontSize: '0.72rem', color: '#64748b' }}>
                            {coverageStr}
                          </div>
                        )}
                      </div>
                      {/* Status Pill */}
                      <span style={{
                        fontSize: '0.7rem', fontWeight: 700, flexShrink: 0,
                        padding: '0.2rem 0.6rem', borderRadius: '999px',
                        background: changeLabel.bg, color: changeLabel.color,
                        border: `1px solid ${changeLabel.color}30`
                      }}>
                        {changeLabel.label}
                      </span>
                    </div>
                  </div>

                  <div className="result-content">
                    {/* Change Bar */}
                    <div style={{ marginBottom: '0.85rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b', marginBottom: '0.3rem' }}>
                        <span>Change Intensity</span>
                        <span style={{ color: changeColor, fontWeight: 700 }}>
                          {`${Number(changePct).toFixed(1)}% measured`}
                        </span>
                      </div>
                      <div style={{ height: 4, background: 'rgba(255,255,255,0.07)', borderRadius: 999, overflow: 'hidden' }}>
                        <div style={{
                          height: '100%',
                          width: changePct === 0 ? '2%' : `${Math.min(100, changePct)}%`,
                          background: changeColor, borderRadius: 999, transition: 'width 0.6s ease'
                        }} />
                      </div>
                    </div>

                    {/* Info Rows */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      {/* Monitoring period */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.8rem', color: '#94a3b8' }}>
                        <Calendar size={12} style={{ color: '#475569', flexShrink: 0 }} />
                        <span>{monitoringLabel}</span>
                      </div>

                      {/* Earliest change date */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.8rem', color: '#94a3b8' }}>
                        <Clock size={12} style={{ color: '#475569', flexShrink: 0 }} />
                        {hasEarliestDate
                          ? <span>Earliest supported observation: <strong style={{ color: '#f1f5f9' }}>{formatDateFriendly(result.earliest_change_date)}</strong></span>
                          : <span style={{ color: '#64748b' }}>No usable observation crossed the change threshold</span>
                        }
                      </div>

                      {/* Persistence badge */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.8rem' }}>
                        <Activity size={12} style={{ color: '#475569', flexShrink: 0 }} />
                        <span style={{
                          color: persistInfo.color, fontWeight: 600,
                          background: `${persistInfo.color}15`, padding: '0.15rem 0.55rem',
                          borderRadius: 999, fontSize: '0.75rem',
                          border: `1px solid ${persistInfo.color}30`
                        }}>
                          {persistInfo.icon} {result.persistence || 'Monitoring Active'}
                        </span>
                      </div>

                      {/* Confidence */}
                      {!isStable && result.confidence != null && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.8rem', color: '#94a3b8' }}>
                          <Shield size={12} style={{ color: '#475569', flexShrink: 0 }} />
                          <span>Model confidence: <strong style={{ color: '#a78bfa' }}>{confPct}%</strong></span>
                        </div>
                      )}
                      {isStable && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.8rem', color: '#94a3b8' }}>
                          <Shield size={12} style={{ color: '#475569', flexShrink: 0 }} />
                          <span>Reported as stable — intensity stayed under the detection threshold</span>
                        </div>
                      )}
                    </div>

                    {/* Footer: Stable Notice */}
                    {isStable && (
                      <div style={{
                        marginTop: '0.85rem', paddingTop: '0.75rem',
                        borderTop: '1px solid rgba(255,255,255,0.05)',
                        display: 'flex', alignItems: 'center', gap: '0.4rem',
                        fontSize: '0.75rem', color: '#10b981'
                      }}>
                        <CheckCircle2 size={12} />
                        <span>No earliest-change date — this site did not meet persistence/confidence criteria</span>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

export default EarliestChange
