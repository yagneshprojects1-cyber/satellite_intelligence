import { useState, useEffect } from 'react'
import { getChangeAnalysis } from '../services/api'
import { Activity, AlertTriangle, Calendar, TrendingUp, Cpu } from 'lucide-react'

function ChangeAnalysis() {
  const [changes, setChanges] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadChanges() }, [])

  const loadChanges = async () => {
    try {
      const response = await getChangeAnalysis()
      setChanges(response.results || [])
    } catch (error) {
      console.error('Error loading changes:', error)
    } finally {
      setLoading(false)
    }
  }

  const getChangeColor = (pct) => {
    if (pct >= 40) return '#ef4444'
    if (pct >= 15) return '#f59e0b'
    return '#10b981'
  }

  if (loading) {
    return (
      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div className="spinner" />
        <p>Loading change analysis…</p>
      </div>
    )
  }

  return (
    <div className="fade-in">
      <h1>Change Analysis</h1>
      <p style={{ color: '#9ca3af', marginBottom: '1.75rem', fontSize: '0.9rem' }}>
        Detected changes between temporal image pairs
      </p>

      {changes.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <AlertTriangle size={36} color="#fbbf24" style={{ marginBottom: '0.85rem', opacity: 0.8 }} />
          <p style={{ fontWeight: 500, marginBottom: '0.35rem' }}>No change results available</p>
          <p style={{ fontSize: '0.83rem', color: '#9ca3af' }}>Run the change detection job to generate results</p>
        </div>
      ) : (
        <div className="search-results">
          {changes.map((change, index) => {
            const color = getChangeColor(change.change_percentage)
            const confPct = ((change.confidence || 0) * 100).toFixed(1)

            return (
              <div key={change.pair_id || index} className="result-card">
                <div className="result-content">
                  {/* Pair ID */}
                  <div style={{
                    fontFamily: 'monospace', fontSize: '0.82rem', fontWeight: 600,
                    color: '#f1f5f9', marginBottom: '0.9rem',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'
                  }}>
                    {change.pair_id}
                  </div>

                  {/* Change bar */}
                  <div style={{ marginBottom: '0.85rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b', marginBottom: '0.25rem' }}>
                      <span>Change</span>
                      <span style={{ color, fontWeight: 600 }}>{change.change_percentage.toFixed(1)}%</span>
                    </div>
                    <div style={{ height: 3, background: 'rgba(255,255,255,0.07)', borderRadius: 999, overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', width: `${Math.min(100, change.change_percentage)}%`,
                        background: color, borderRadius: 999, transition: 'width 0.5s ease'
                      }} />
                    </div>
                  </div>

                  {/* Meta */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.79rem', color: '#94a3b8' }}>
                      <Calendar size={11} style={{ color: '#475569', flexShrink: 0 }} />
                      {change.before_date} → {change.after_date}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.79rem', color: '#94a3b8' }}>
                      <TrendingUp size={11} style={{ color: '#475569', flexShrink: 0 }} />
                      Confidence: <strong style={{ color: '#60a5fa' }}>{confPct}%</strong>
                    </div>
                    {change.model_used && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.79rem', color: '#94a3b8' }}>
                        <Cpu size={11} style={{ color: '#475569', flexShrink: 0 }} />
                        {change.model_used}
                      </div>
                    )}
                    {change.change_type && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.79rem', color: '#60a5fa' }}>
                        <Activity size={11} style={{ color: '#475569', flexShrink: 0 }} />
                        {change.change_type}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default ChangeAnalysis
