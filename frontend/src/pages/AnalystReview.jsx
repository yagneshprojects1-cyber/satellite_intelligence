import { useState, useEffect } from 'react'
import { getChangeAnalysis, submitAnalystReview } from '../services/api'
import { CheckCircle, XCircle, MessageSquare, AlertTriangle } from 'lucide-react'

function AnalystReview() {
  const [changes, setChanges] = useState([])
  const [selectedChange, setSelectedChange] = useState(null)
  const [review, setReview] = useState({
    decision: '',
    change_type: 'unknown',
    comment: ''
  })
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    loadChanges()
  }, [])

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
      alert('Review submitted successfully')
      setSelectedChange(null)
      setReview({ decision: '', change_type: 'unknown', comment: '' })
    } catch (error) {
      console.error('Error submitting review:', error)
      alert('Failed to submit review')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="card">
        <div className="spinner"></div>
        <p style={{ marginTop: '1rem' }}>Loading analyst review candidates...</p>
      </div>
    )
  }

  if (changes.length === 0) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <AlertTriangle size={48} color="#fbbf24" style={{ marginBottom: '1rem' }} />
          <p>No change results available for review</p>
          <p style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
            Run change detection job to generate candidates
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="fade-in">
      <h1>Analyst Review</h1>
      <p style={{ color: '#9ca3af', marginBottom: '2rem' }}>
        Review and validate detected changes
      </p>

      {!selectedChange ? (
        <div className="search-results">
          {changes.map((change, index) => (
            <div key={index} className="result-card" onClick={() => setSelectedChange(change)}>
              <div className="result-content">
                <div className="result-title">{change.pair_id}</div>
                <div className="result-meta">Before: {change.before_date}</div>
                <div className="result-meta">After: {change.after_date}</div>
                <div className="result-similarity">
                  Change: {change.change_percentage.toFixed(1)}%
                </div>
                <div className="result-meta">
                  Confidence: {(change.confidence * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card">
          <h2 className="card-header">Review: {selectedChange.pair_id}</h2>
          
          <div className="change-comparison" style={{ marginBottom: '1rem' }}>
            <div>
              <h3 style={{ marginBottom: '0.5rem' }}>Before Image</h3>
              <div className="change-image" style={{ 
                background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <span style={{ color: '#9ca3af' }}>{selectedChange.before_date}</span>
              </div>
            </div>
            <div>
              <h3 style={{ marginBottom: '0.5rem' }}>After Image</h3>
              <div className="change-image" style={{ 
                background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <span style={{ color: '#9ca3af' }}>{selectedChange.after_date}</span>
              </div>
            </div>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <h3 style={{ marginBottom: '0.5rem' }}>Change Mask</h3>
            <div className="change-mask" style={{ 
              background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <span style={{ color: '#9ca3af' }}>Change mask visualization</span>
            </div>
          </div>

          <div style={{ 
            padding: '1rem',
            background: 'rgba(255, 255, 255, 0.02)',
            borderRadius: '8px',
            marginBottom: '1rem'
          }}>
            <div className="result-meta">Change Percentage: {selectedChange.change_percentage.toFixed(1)}%</div>
            <div className="result-meta">Confidence: {(selectedChange.confidence * 100).toFixed(1)}%</div>
            <div className="result-meta">Model: {selectedChange.model_used}</div>
          </div>

          <div className="form-group">
            <label className="form-label">Decision</label>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <button
                className={`btn ${review.decision === 'confirmed' ? 'btn-success' : 'btn-secondary'}`}
                onClick={() => setReview({ ...review, decision: 'confirmed' })}
              >
                <CheckCircle size={18} style={{ marginRight: '0.5rem' }} />
                Confirm
              </button>
              <button
                className={`btn ${review.decision === 'rejected' ? 'btn-danger' : 'btn-secondary'}`}
                onClick={() => setReview({ ...review, decision: 'rejected' })}
              >
                <XCircle size={18} style={{ marginRight: '0.5rem' }} />
                Reject
              </button>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Change Type</label>
            <select
              className="form-control"
              value={review.change_type}
              onChange={(e) => setReview({ ...review, change_type: e.target.value })}
            >
              <option value="unknown">Unknown</option>
              <option value="construction">Construction</option>
              <option value="clearance">Clearance</option>
              <option value="water_variation">Water Variation</option>
              <option value="road_development">Road Development</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Comment (Optional)</label>
            <textarea
              className="form-control"
              rows={3}
              value={review.comment}
              onChange={(e) => setReview({ ...review, comment: e.target.value })}
              placeholder="Add any additional notes..."
            />
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              className="btn btn-primary"
              onClick={handleSubmitReview}
              disabled={!review.decision || submitting}
            >
              {submitting ? <div className="spinner" style={{ width: 20, height: 20 }} /> : 'Submit Review'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => {
                setSelectedChange(null)
                setReview({ decision: '', change_type: 'unknown', comment: '' })
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default AnalystReview
