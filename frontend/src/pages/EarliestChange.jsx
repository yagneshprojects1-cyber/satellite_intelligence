import { useState, useEffect } from 'react'
import { getEarliestChanges } from '../services/api'
import { MapPin, Clock, AlertTriangle, TrendingUp, Activity, Calendar } from 'lucide-react'

function EarliestChange() {
  const [earliestChanges, setEarliestChanges] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadEarliestChanges()
  }, [])

  const loadEarliestChanges = async () => {
    try {
      const response = await getEarliestChanges()
      setEarliestChanges(response)
    } catch (error) {
      console.error('Error loading earliest changes:', error)
    } finally {
      setLoading(false)
    }
  }

  const getChangeColor = (pct) => {
    if (pct >= 40) return '#ef4444'
    if (pct >= 15) return '#f59e0b'
    return '#10b981'
  }

  const getPersistenceColor = (type) => {
    if (type === 'Persistent') return '#10b981'
    if (type === 'Transient') return '#f59e0b'
    return '#94a3b8'
  }

  if (loading) {
    return (
      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div className="spinner" />
        <p>Loading earliest changes…</p>
      </div>
    )
  }

  if (!earliestChanges || !earliestChanges.results || earliestChanges.results.length === 0) {
    return (
      <div className="fade-in">
        <h1>Earliest Change Detection</h1>
        <p style={{ color: '#9ca3af', marginBottom: '1.75rem', fontSize: '0.9rem' }}>
          First detected changes across the temporal sequence
        </p>
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <AlertTriangle size={36} color="#fbbf24" style={{ marginBottom: '0.85rem', opacity: 0.8 }} />
          <p style={{ fontWeight: 500, marginBottom: '0.35rem' }}>No earliest change results available</p>
          <p style={{ fontSize: '0.83rem', color: '#9ca3af' }}>Run earliest change analysis job to generate results</p>
        </div>
      </div>
    )
  }

  const results = earliestChanges.results
  const persistentCount = results.filter(r => r.persistence === 'Persistent').length
  const transientCount = results.filter(r => r.persistence === 'Transient').length

  return (
    <div className="fade-in">
      <h1>Earliest Change Detection</h1>
      <p style={{ color: '#9ca3af', marginBottom: '1.75rem', fontSize: '0.9rem' }}>
        First detected changes across the temporal sequence
      </p>

      {/* Summary stats */}
      <div className="grid grid-3" style={{ marginBottom: '1.5rem' }}>
        <div className="card" style={{ textAlign: 'center', padding: '1.25rem' }}>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#60a5fa' }}>
            {earliestChanges.total_locations || results.length}
          </div>
          <div style={{ color: '#94a3b8', fontSize: '0.83rem', marginTop: '0.25rem' }}>Total Locations</div>
        </div>
        <div className="card" style={{ textAlign: 'center', padding: '1.25rem' }}>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#10b981' }}>
            {persistentCount}
          </div>
          <div style={{ color: '#94a3b8', fontSize: '0.83rem', marginTop: '0.25rem' }}>Persistent</div>
        </div>
        <div className="card" style={{ textAlign: 'center', padding: '1.25rem' }}>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#fbbf24' }}>
            {transientCount}
          </div>
          <div style={{ color: '#94a3b8', fontSize: '0.83rem', marginTop: '0.25rem' }}>Transient</div>
        </div>
      </div>

      {/* Result cards */}
      <div className="search-results">
        {results.map((result, index) => {
          const changePct = result.change_percentage || 0
          const changeColor = getChangeColor(changePct)
          const confPct = ((result.confidence || 0) * 100).toFixed(1)
          const persistColor = getPersistenceColor(result.persistence)

          return (
            <div key={index} className="result-card">
              <div className="result-content">
                {/* Location */}
                <div style={{
                  fontFamily: 'monospace', fontSize: '0.82rem', fontWeight: 600,
                  color: '#f1f5f9', marginBottom: '0.9rem',
                  display: 'flex', alignItems: 'center', gap: '0.4rem'
                }}>
                  <MapPin size={13} style={{ color: '#60a5fa', flexShrink: 0 }} />
                  <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {result.location_reference}
                  </span>
                </div>

                {/* Change bar */}
                <div style={{ marginBottom: '0.85rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b', marginBottom: '0.25rem' }}>
                    <span>Change</span>
                    <span style={{ color: changeColor, fontWeight: 600 }}>{changePct.toFixed(1)}%</span>
                  </div>
                  <div style={{ height: 3, background: 'rgba(255,255,255,0.07)', borderRadius: 999, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%', width: `${Math.min(100, changePct)}%`,
                      background: changeColor, borderRadius: 999, transition: 'width 0.5s ease'
                    }} />
                  </div>
                </div>

                {/* Meta rows */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.79rem', color: '#94a3b8' }}>
                    <Clock size={11} style={{ color: '#475569', flexShrink: 0 }} />
                    Earliest: <strong style={{ color: '#f1f5f9' }}>{result.earliest_change_date}</strong>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.79rem', color: '#94a3b8' }}>
                    <Calendar size={11} style={{ color: '#475569', flexShrink: 0 }} />
                    {result.before_date} → {result.after_date}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.79rem', color: '#94a3b8' }}>
                    <TrendingUp size={11} style={{ color: '#475569', flexShrink: 0 }} />
                    Confidence: <strong style={{ color: '#60a5fa' }}>{confPct}%</strong>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.79rem' }}>
                    <Activity size={11} style={{ color: '#475569', flexShrink: 0 }} />
                    <span style={{
                      color: persistColor, fontWeight: 600,
                      background: `${persistColor}15`, padding: '0.1rem 0.5rem',
                      borderRadius: 999, fontSize: '0.75rem'
                    }}>
                      {result.persistence}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default EarliestChange
