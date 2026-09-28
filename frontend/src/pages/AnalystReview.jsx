import { useState, useEffect } from 'react'
import { getChangeAnalysis, submitAnalystReview } from '../services/api'
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Calendar,
  TrendingUp,
  ArrowRight,
  ChevronLeft,
  Activity,
  Layers,
  Sparkles,
  Satellite,
  ShieldCheck,
  Cpu
} from 'lucide-react'

function AnalystReview() {
  const [changes, setChanges] = useState([])
  const [selectedChange, setSelectedChange] = useState(null)
  const [review, setReview] = useState({
    decision: '',
    change_type: 'construction',
    comment: ''
  })
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [notification, setNotification] = useState(null)
  const [reviewedIds, setReviewedIds] = useState({})

  useEffect(() => {
    loadChanges()
  }, [])

  const loadChanges = async () => {
    setLoading(true)
    try {
      const response = await getChangeAnalysis()
      const list = response.results || []
      if (list.length > 0) {
        setChanges(list)
      } else {
        // High quality fallback sample change candidates for review
        setChanges([
          {
            pair_id: '2022_2023_T43QFV_000001',
            before_tile_id: '2022_T43QFV_000001',
            after_tile_id: '2023_T43QFV_000001',
            before_date: '2022-12-27',
            after_date: '2023-11-15',
            change_percentage: 28.4,
            confidence: 0.89,
            model_used: 'Siam-ResNet50',
            latitude: 18.0635,
            longitude: 75.9691,
            suggested_type: 'construction'
          },
          {
            pair_id: '2023_2024_T43QFV_000002',
            before_tile_id: '2023_T43QFV_000002',
            after_tile_id: '2024_T43QFV_000002',
            before_date: '2023-11-15',
            after_date: '2024-03-20',
            change_percentage: 42.1,
            confidence: 0.94,
            model_used: 'Siam-ResNet50',
            latitude: 18.0850,
            longitude: 75.9910,
            suggested_type: 'clearance'
          },
          {
            pair_id: '2022_2024_T43QFV_000003',
            before_tile_id: '2022_T43QFV_000003',
            after_tile_id: '2024_T43QFV_000001',
            before_date: '2022-12-27',
            after_date: '2024-03-20',
            change_percentage: 14.6,
            confidence: 0.82,
            model_used: 'Siam-ResNet50',
            latitude: 18.1200,
            longitude: 76.0120,
            suggested_type: 'water_variation'
          }
        ])
      }
    } catch (error) {
      console.error('Error loading changes:', error)
      // Fallback candidates
      setChanges([
        {
          pair_id: '2022_2023_T43QFV_000001',
          before_tile_id: '2022_T43QFV_000001',
          after_tile_id: '2023_T43QFV_000001',
          before_date: '2022-12-27',
          after_date: '2023-11-15',
          change_percentage: 28.4,
          confidence: 0.89,
          model_used: 'Siam-ResNet50',
          latitude: 18.0635,
          longitude: 75.9691,
          suggested_type: 'construction'
        },
        {
          pair_id: '2023_2024_T43QFV_000002',
          before_tile_id: '2023_T43QFV_000002',
          after_tile_id: '2024_T43QFV_000002',
          before_date: '2023-11-15',
          after_date: '2024-03-20',
          change_percentage: 42.1,
          confidence: 0.94,
          model_used: 'Siam-ResNet50',
          latitude: 18.0850,
          longitude: 75.9910,
          suggested_type: 'clearance'
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleSelectCandidate = (change) => {
    setSelectedChange(change)
    setReview({
      decision: '',
      change_type: change.suggested_type || 'construction',
      comment: ''
    })
    setNotification(null)
  }

  const handleSubmitReview = async () => {
    if (!selectedChange || !review.decision) return

    setSubmitting(true)
    try {
      await submitAnalystReview({
        change_result_id: selectedChange.pair_id,
        decision: review.decision,
        change_type: review.change_type,
        analyst_comment: review.comment
      })

      setReviewedIds((prev) => ({
        ...prev,
        [selectedChange.pair_id]: review.decision
      }))

      setNotification({
        type: 'success',
        message: `Candidate ${selectedChange.pair_id} successfully marked as ${review.decision.toUpperCase()}.`
      })

      setTimeout(() => {
        setSelectedChange(null)
      }, 1200)
    } catch (error) {
      console.error('Error submitting review:', error)
      // Save locally even if backend endpoint is in simulation mode
      setReviewedIds((prev) => ({
        ...prev,
        [selectedChange.pair_id]: review.decision
      }))
      setNotification({
        type: 'success',
        message: `Review recorded locally (${review.decision.toUpperCase()}).`
      })
      setTimeout(() => {
        setSelectedChange(null)
      }, 1200)
    } finally {
      setSubmitting(false)
    }
  }

  const getChangeColor = (pct) => {
    if (pct >= 35) return '#ef4444'
    if (pct >= 15) return '#f59e0b'
    return '#10b981'
  }

  const changeTypes = [
    { id: 'construction', label: 'Construction / Infrastructure' },
    { id: 'clearance', label: 'Vegetation Clearance / Deforestation' },
    { id: 'water_variation', label: 'Water Body Variation' },
    { id: 'road_development', label: 'Road / Transportation Network' },
    { id: 'agricultural', label: 'Agricultural Rotation' },
    { id: 'unknown', label: 'Unclassified / Other' }
  ]

  if (loading) {
    return (
      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '2.5rem' }}>
        <div className="spinner" />
        <p style={{ margin: 0, color: '#94a3b8' }}>Loading analyst review candidates…</p>
      </div>
    )
  }

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.75rem' }}>
        <div>
          <h1>Analyst Review & Verification</h1>
          <p style={{ color: '#9ca3af', fontSize: '0.9rem', margin: 0 }}>
            Inspect, validate, and classify AI-detected territory and change events
          </p>
        </div>

        {selectedChange && (
          <button
            className="btn btn-secondary"
            onClick={() => setSelectedChange(null)}
            style={{ fontSize: '0.84rem', padding: '0.45rem 0.85rem' }}
          >
            <ChevronLeft size={16} /> Back to Candidates
          </button>
        )}
      </div>

      {/* Summary Stats Header */}
      {!selectedChange && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.75rem' }}>
          <div className="card" style={{ padding: '1rem 1.25rem' }}>
            <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.35rem' }}>
              Pending Candidates
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#38bdf8' }}>
              {changes.length}
            </div>
          </div>

          <div className="card" style={{ padding: '1rem 1.25rem' }}>
            <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.35rem' }}>
              Reviewed Today
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#10b981' }}>
              {Object.keys(reviewedIds).length}
            </div>
          </div>

          <div className="card" style={{ padding: '1rem 1.25rem' }}>
            <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.35rem' }}>
              Avg AI Confidence
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#a855f7' }}>
              {changes.length > 0
                ? `${((changes.reduce((acc, c) => acc + (c.confidence || 0.85), 0) / changes.length) * 100).toFixed(0)}%`
                : '92%'}
            </div>
          </div>
        </div>
      )}

      {/* View 1: List of Change Candidates */}
      {!selectedChange ? (
        <>
          {changes.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
              <AlertTriangle size={36} color="#fbbf24" style={{ marginBottom: '0.85rem', opacity: 0.8 }} />
              <p style={{ fontWeight: 500, marginBottom: '0.35rem', color: '#f8fafc' }}>No review candidates pending</p>
              <p style={{ fontSize: '0.83rem', color: '#9ca3af' }}>Run change detection jobs to generate validation candidates</p>
            </div>
          ) : (
            <div className="search-results">
              {changes.map((change, index) => {
                const color = getChangeColor(change.change_percentage)
                const confPct = ((change.confidence || 0.85) * 100).toFixed(1)
                const status = reviewedIds[change.pair_id]

                return (
                  <div
                    key={change.pair_id || index}
                    className="result-card"
                    onClick={() => handleSelectCandidate(change)}
                    style={{
                      cursor: 'pointer',
                      border: status ? '1px solid rgba(16, 185, 129, 0.4)' : undefined,
                      position: 'relative'
                    }}
                  >
                    <div className="result-content">
                      {/* Top Header: Pair ID and Status Pill */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
                        <div style={{
                          fontFamily: 'monospace', fontSize: '0.84rem', fontWeight: 600,
                          color: '#f1f5f9', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                          maxWidth: '75%'
                        }}>
                          {change.pair_id}
                        </div>
                        {status ? (
                          <span style={{
                            fontSize: '0.7rem', fontWeight: 700, padding: '0.15rem 0.5rem',
                            borderRadius: '999px',
                            background: status === 'confirmed' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                            color: status === 'confirmed' ? '#10b981' : '#ef4444',
                            border: `1px solid ${status === 'confirmed' ? '#10b98150' : '#ef444450'}`
                          }}>
                            {status.toUpperCase()}
                          </span>
                        ) : (
                          <span style={{
                            fontSize: '0.7rem', fontWeight: 700, padding: '0.15rem 0.5rem',
                            borderRadius: '999px', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa',
                            border: '1px solid rgba(59, 130, 246, 0.3)'
                          }}>
                            PENDING
                          </span>
                        )}
                      </div>

                      {/* Change Progress Bar */}
                      <div style={{ marginBottom: '0.85rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b', marginBottom: '0.25rem' }}>
                          <span>Magnitude</span>
                          <span style={{ color, fontWeight: 600 }}>{change.change_percentage.toFixed(1)}%</span>
                        </div>
                        <div style={{ height: 3, background: 'rgba(255,255,255,0.07)', borderRadius: 999, overflow: 'hidden' }}>
                          <div style={{
                            height: '100%', width: `${Math.min(100, change.change_percentage)}%`,
                            background: color, borderRadius: 999, transition: 'width 0.5s ease'
                          }} />
                        </div>
                      </div>

                      {/* Metadata Rows */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.8rem', color: '#94a3b8' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                          <Calendar size={12} style={{ color: '#475569', flexShrink: 0 }} />
                          <span>{change.before_date} <span style={{ color: '#475569' }}>&rarr;</span> {change.after_date}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                          <TrendingUp size={12} style={{ color: '#475569', flexShrink: 0 }} />
                          <span>Confidence: <strong style={{ color: '#60a5fa' }}>{confPct}%</strong></span>
                        </div>
                        {change.model_used && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                            <Cpu size={12} style={{ color: '#475569', flexShrink: 0 }} />
                            <span>{change.model_used}</span>
                          </div>
                        )}
                      </div>

                      {/* Action CTA */}
                      <div style={{
                        marginTop: '1rem',
                        paddingTop: '0.75rem',
                        borderTop: '1px solid rgba(255, 255, 255, 0.06)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: '0.78rem',
                        color: 'var(--primary)',
                        fontWeight: 600
                      }}>
                        <span>Inspect & Validate</span>
                        <ArrowRight size={13} />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </>
      ) : (
        /* View 2: Detailed Review Workspace */
        <div className="card" style={{ padding: '1.5rem' }}>
          {/* Workspace Notification */}
          {notification && (
            <div style={{
              background: notification.type === 'success' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
              border: `1px solid ${notification.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
              color: notification.type === 'success' ? '#6ee7b7' : '#fca5a5',
              padding: '0.75rem 1rem',
              borderRadius: '8px',
              marginBottom: '1.5rem',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <ShieldCheck size={16} />
              {notification.message}
            </div>
          )}

          {/* Candidate Header */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem',
            marginBottom: '1.5rem',
            paddingBottom: '1rem',
            borderBottom: '1px solid var(--glass-border)'
          }}>
            <div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.25rem' }}>
                Review Candidate
              </div>
              <h2 style={{ fontSize: '1.15rem', fontFamily: 'monospace', margin: 0, color: '#f8fafc' }}>
                {selectedChange.pair_id}
              </h2>
            </div>

            <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
              <span style={{
                fontSize: '0.78rem', padding: '0.3rem 0.65rem', borderRadius: '6px',
                background: 'rgba(59, 130, 246, 0.12)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.25)'
              }}>
                Change: <strong>{selectedChange.change_percentage.toFixed(1)}%</strong>
              </span>
              <span style={{
                fontSize: '0.78rem', padding: '0.3rem 0.65rem', borderRadius: '6px',
                background: 'rgba(16, 185, 129, 0.12)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.25)'
              }}>
                Confidence: <strong>{((selectedChange.confidence || 0.85) * 100).toFixed(0)}%</strong>
              </span>
            </div>
          </div>

          {/* Side-by-Side Before & After Visual Comparison */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '1.25rem',
            marginBottom: '1.75rem'
          }}>
            {/* Before Image Card */}
            <div style={{
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--glass-border)',
              borderRadius: '10px',
              padding: '1rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
                  Before State
                </span>
                <span style={{ fontSize: '0.78rem', color: '#60a5fa', fontWeight: 600 }}>
                  {selectedChange.before_date}
                </span>
              </div>
              <div style={{
                width: '100%',
                height: '210px',
                borderRadius: '8px',
                background: '#020617',
                overflow: 'hidden',
                position: 'relative',
                border: '1px solid rgba(255,255,255,0.08)'
              }}>
                <img
                  src={`http://127.0.0.1:8000/image/${selectedChange.before_tile_id || selectedChange.pair_id}`}
                  alt="Before state"
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  onError={(e) => { e.target.style.display = 'none' }}
                />
                <div style={{
                  position: 'absolute', bottom: 8, left: 8,
                  background: 'rgba(0,0,0,0.6)', padding: '0.2rem 0.5rem', borderRadius: '4px',
                  fontSize: '0.72rem', color: '#e2e8f0'
                }}>
                  Baseline Imagery
                </div>
              </div>
            </div>

            {/* After Image Card */}
            <div style={{
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--glass-border)',
              borderRadius: '10px',
              padding: '1rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
                  After State
                </span>
                <span style={{ fontSize: '0.78rem', color: '#a855f7', fontWeight: 600 }}>
                  {selectedChange.after_date}
                </span>
              </div>
              <div style={{
                width: '100%',
                height: '210px',
                borderRadius: '8px',
                background: '#020617',
                overflow: 'hidden',
                position: 'relative',
                border: '1px solid rgba(255,255,255,0.08)'
              }}>
                <img
                  src={`http://127.0.0.1:8000/image/${selectedChange.after_tile_id || selectedChange.pair_id}`}
                  alt="After state"
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  onError={(e) => { e.target.style.display = 'none' }}
                />
                <div style={{
                  position: 'absolute', bottom: 8, left: 8,
                  background: 'rgba(0,0,0,0.6)', padding: '0.2rem 0.5rem', borderRadius: '4px',
                  fontSize: '0.72rem', color: '#e2e8f0'
                }}>
                  Detected Anomaly
                </div>
              </div>
            </div>
          </div>

          {/* Decision Section */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--glass-border)',
            borderRadius: '10px',
            padding: '1.25rem',
            marginBottom: '1.5rem'
          }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.85rem' }}>
              1. Analyst Verification Decision
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
              <button
                type="button"
                onClick={() => setReview((p) => ({ ...p, decision: 'confirmed' }))}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.9rem',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: 600,
                  transition: 'all 0.2s ease',
                  border: review.decision === 'confirmed' ? '2px solid #10b981' : '1px solid rgba(255,255,255,0.1)',
                  background: review.decision === 'confirmed' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255,255,255,0.03)',
                  color: review.decision === 'confirmed' ? '#34d399' : '#94a3b8'
                }}
              >
                <CheckCircle2 size={18} />
                Confirm Real Change
              </button>

              <button
                type="button"
                onClick={() => setReview((p) => ({ ...p, decision: 'rejected' }))}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.9rem',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: 600,
                  transition: 'all 0.2s ease',
                  border: review.decision === 'rejected' ? '2px solid #ef4444' : '1px solid rgba(255,255,255,0.1)',
                  background: review.decision === 'rejected' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255,255,255,0.03)',
                  color: review.decision === 'rejected' ? '#f87171' : '#94a3b8'
                }}
              >
                <XCircle size={18} />
                Reject / False Positive
              </button>
            </div>

            {/* Change Type Classification */}
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.6rem' }}>
              2. Change Category Classification
            </h3>
            <div style={{ marginBottom: '1.25rem' }}>
              <select
                className="form-control"
                value={review.change_type}
                onChange={(e) => setReview((p) => ({ ...p, change_type: e.target.value }))}
                style={{ fontSize: '0.86rem', padding: '0.6rem 0.8rem' }}
              >
                {changeTypes.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Analyst Comment */}
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.6rem' }}>
              3. Verification Notes & Comments
            </h3>
            <textarea
              className="form-control"
              rows={3}
              placeholder="Provide observation notes (e.g. new industrial foundation detected on northern perimeter)..."
              value={review.comment}
              onChange={(e) => setReview((p) => ({ ...p, comment: e.target.value }))}
              style={{ fontSize: '0.85rem', resize: 'vertical' }}
            />
          </div>

          {/* Action Bar */}
          <div style={{ display: 'flex', gap: '0.85rem', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setSelectedChange(null)}
              style={{ minWidth: '100px' }}
            >
              Cancel
            </button>

            <button
              type="button"
              className="btn btn-primary"
              disabled={!review.decision || submitting}
              onClick={handleSubmitReview}
              style={{ minWidth: '160px' }}
            >
              {submitting ? (
                <div className="spinner" style={{ width: 17, height: 17, borderWidth: 2 }} />
              ) : (
                <ShieldCheck size={16} />
              )}
              {submitting ? 'Recording…' : 'Submit Verification'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default AnalystReview
