import { useState, useEffect } from 'react'
import { getChangeAnalysis } from '../services/api'
import { Activity, AlertTriangle } from 'lucide-react'

function ChangeAnalysis() {
  const [changes, setChanges] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedChange, setSelectedChange] = useState(null)

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

  if (loading) {
    return (
      <div className="card">
        <div className="spinner"></div>
        <p style={{ marginTop: '1rem' }}>Loading change analysis...</p>
      </div>
    )
  }

  return (
    <div className="fade-in">
      <h1>Change Analysis</h1>
      <p style={{ color: '#9ca3af', marginBottom: '2rem' }}>
        Detected changes between temporal image pairs
      </p>

      {changes.length === 0 ? (
        <div className="card">
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <AlertTriangle size={48} color="#fbbf24" style={{ marginBottom: '1rem' }} />
            <p>No change results available</p>
            <p style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
              Run change detection job to generate results
            </p>
          </div>
        </div>
      ) : (
        <div className="search-results">
          {changes.map((change, index) => (
            <div key={index} className="result-card" onClick={() => setSelectedChange(change)}>
              <div className="result-content">
                <div className="result-title">
                  <Activity size={18} style={{ marginRight: '0.5rem' }} />
                  {change.pair_id}
                </div>
                <div className="result-meta">Before: {change.before_date}</div>
                <div className="result-meta">After: {change.after_date}</div>
                <div className="result-similarity">
                  Change: {change.change_percentage.toFixed(1)}%
                </div>
                <div className="result-meta">
                  Confidence: {(change.confidence * 100).toFixed(1)}%
                </div>
                <div className="result-meta">Model: {change.model_used}</div>
                {change.change_type && (
                  <div className="result-meta" style={{ color: '#60a5fa' }}>
                    Type: {change.change_type}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedChange && (
        <div className="card" style={{ marginTop: '2rem' }}>
          <h2 className="card-header">Change Details: {selectedChange.pair_id}</h2>
          <div className="change-comparison">
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
          <div>
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
          <div style={{ marginTop: '1rem' }}>
            <button className="btn btn-secondary" onClick={() => setSelectedChange(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default ChangeAnalysis
