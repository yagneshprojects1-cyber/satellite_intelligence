import { useState, useEffect } from 'react'
import { getEarliestChanges } from '../services/api'
import { MapPin, Clock, AlertTriangle } from 'lucide-react'

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

  if (loading) {
    return (
      <div className="card">
        <div className="spinner"></div>
        <p style={{ marginTop: '1rem' }}>Loading earliest changes...</p>
      </div>
    )
  }

  if (!earliestChanges || !earliestChanges.results || earliestChanges.results.length === 0) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <AlertTriangle size={48} color="#fbbf24" style={{ marginBottom: '1rem' }} />
          <p>No earliest change results available</p>
          <p style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
            Run earliest change analysis job to generate results
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="fade-in">
      <h1>Earliest Change Detection</h1>
      <p style={{ color: '#9ca3af', marginBottom: '2rem' }}>
        First detected changes across the temporal sequence
      </p>

      <div className="card">
        <h2 className="card-header">Summary</h2>
        <div className="grid grid-3">
          <div style={{ padding: '1rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '8px' }}>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: '#60a5fa' }}>
              {earliestChanges.total_locations || 0}
            </div>
            <div style={{ color: '#9ca3af' }}>Total Locations</div>
          </div>
          <div style={{ padding: '1rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '8px' }}>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: '#22c55e' }}>
              {earliestChanges.results?.filter(r => r.persistence === 'Persistent').length || 0}
            </div>
            <div style={{ color: '#9ca3af' }}>Persistent Changes</div>
          </div>
          <div style={{ padding: '1rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '8px' }}>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: '#fbbf24' }}>
              {earliestChanges.results?.filter(r => r.persistence === 'Transient').length || 0}
            </div>
            <div style={{ color: '#9ca3af' }}>Transient Changes</div>
          </div>
        </div>
      </div>

      <div className="search-results">
        {earliestChanges.results.map((result, index) => (
          <div key={index} className="result-card">
            <div className="result-content">
              <div className="result-title">
                <MapPin size={18} style={{ marginRight: '0.5rem' }} />
                {result.location_reference}
              </div>
              <div className="result-meta">
                <Clock size={14} style={{ marginRight: '0.25rem' }} />
                Earliest: {result.earliest_change_date}
              </div>
              <div className="result-meta">Before: {result.before_date}</div>
              <div className="result-meta">After: {result.after_date}</div>
              <div className="result-similarity">
                Confidence: {(result.confidence * 100).toFixed(1)}%
              </div>
              <div className="result-meta">
                Change: {result.change_percentage.toFixed(1)}%
              </div>
              <div className="result-meta" style={{ color: '#60a5fa' }}>
                Persistence: {result.persistence}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default EarliestChange
