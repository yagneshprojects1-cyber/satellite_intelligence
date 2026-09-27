import { useState, useEffect } from 'react'
import { getHealth, getPipelineStatus, getJobs } from '../services/api'
import { Activity, CheckCircle, AlertCircle, Clock } from 'lucide-react'

function Dashboard() {
  const [health, setHealth] = useState(null)
  const [pipelineStatus, setPipelineStatus] = useState(null)
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()
    const interval = setInterval(loadDashboardData, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadDashboardData = async () => {
    try {
      const [healthData, statusData, jobsData] = await Promise.all([
        getHealth(),
        getPipelineStatus(),
        getJobs()
      ])
      setHealth(healthData)
      setPipelineStatus(statusData)
      setJobs(jobsData.jobs || [])
    } catch (error) {
      console.error('Error loading dashboard:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="card">
        <div className="spinner"></div>
        <p style={{ marginTop: '1rem' }}>Loading dashboard...</p>
      </div>
    )
  }

  return (
    <div className="fade-in">
      <h1>Dashboard</h1>
      <p style={{ color: '#9ca3af', marginBottom: '2rem' }}>
        System overview and pipeline status
      </p>

      {/* Health Status */}
      <div className="card">
        <h2 className="card-header">System Health</h2>
        <div className="grid grid-3">
          {health?.checks?.map((check, index) => (
            <div key={index} style={{ 
              padding: '1rem',
              background: 'rgba(255, 255, 255, 0.02)',
              borderRadius: '8px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                {check.status === 'healthy' ? (
                  <CheckCircle size={18} color="#22c55e" />
                ) : (
                  <AlertCircle size={18} color="#ef4444" />
                )}
                <span style={{ fontWeight: 600 }}>{check.component}</span>
              </div>
              <p style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
                {check.message}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Pipeline Status */}
      <div className="card">
        <h2 className="card-header">Pipeline Status</h2>
        <div className="grid grid-2">
          {pipelineStatus?.completeness && Object.entries(pipelineStatus.completeness).map(([phase, complete]) => (
            <div key={phase} style={{ 
              padding: '1rem',
              background: 'rgba(255, 255, 255, 0.02)',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem'
            }}>
              {complete ? (
                <CheckCircle size={20} color="#22c55e" />
              ) : (
                <Clock size={20} color="#fbbf24" />
              )}
              <span style={{ textTransform: 'capitalize' }}>{phase.replace('_', ' ')}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Active Jobs */}
      <div className="card">
        <h2 className="card-header">Active Jobs</h2>
        {jobs.length === 0 ? (
          <p style={{ color: '#9ca3af' }}>No active jobs</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {jobs.map((job) => (
              <div key={job.job_id} style={{
                padding: '1rem',
                background: 'rgba(255, 255, 255, 0.02)',
                borderRadius: '8px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
                    {job.phase.replace('_', ' ')}
                  </div>
                  <div style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
                    {job.operation}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span className={`status-indicator ${job.status}`}>
                    {job.status}
                  </span>
                  {job.progress > 0 && (
                    <div style={{ marginTop: '0.5rem' }}>
                      <div className="progress-bar">
                        <div 
                          className="progress-fill" 
                          style={{ width: `${job.progress * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard
