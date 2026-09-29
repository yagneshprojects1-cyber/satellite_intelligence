import { useState, useEffect } from 'react'
import { getHealth, getJobs } from '../services/api'
import {
  Activity, CheckCircle, AlertCircle, Clock,
  Database, Cpu, RefreshCw, Zap, ShieldCheck,
  Server, HardDrive
} from 'lucide-react'

function StatusDot({ ok }) {
  return (
    <span style={{
      display: 'inline-block', width: 9, height: 9, borderRadius: '50%',
      background: ok ? '#22c55e' : '#ef4444',
      boxShadow: ok ? '0 0 6px #22c55e80' : '0 0 6px #ef444480',
      flexShrink: 0
    }} />
  )
}

function SystemHealth() {
  const [health, setHealth] = useState(null)
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastRefresh, setLastRefresh] = useState(null)

  useEffect(() => {
    loadHealthData()
    const interval = setInterval(loadHealthData, 10000)
    return () => clearInterval(interval)
  }, [])

  const loadHealthData = async (isManual = false) => {
    if (isManual) setRefreshing(true)
    else setLoading(true)
    try {
      const [healthData, jobsData] = await Promise.all([
        getHealth(),
        getJobs()
      ])
      setHealth(healthData)
      setJobs(jobsData.jobs || [])
      setLastRefresh(new Date())
    } catch (error) {
      console.error('Error loading health diagnostics:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const overallHealthy = health?.overall_status === 'healthy' || health?.status === 'healthy' || (health?.checks?.every(c => c.status === 'healthy'))
  const passedChecks = health?.checks?.filter(c => c.status === 'healthy').length || 0
  const totalChecks = health?.checks?.length || 0

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '5rem 2rem', gap: '1rem' }}>
        <div className="spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
        <p style={{ color: '#64748b', margin: 0 }}>Running system health diagnostics…</p>
      </div>
    )
  }

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.75rem' }}>
        <div>
          <h1 style={{ marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Activity size={22} style={{ color: '#10b981' }} />
            System Health & Diagnostics
          </h1>
          <p style={{ color: '#9ca3af', fontSize: '0.9rem', margin: 0 }}>
            Infrastructure connectivity, vector database index status, and active processing tasks
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            className="btn btn-secondary"
            onClick={() => loadHealthData(true)}
            disabled={refreshing}
            style={{ fontSize: '0.84rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <RefreshCw size={14} className={refreshing ? 'spin' : ''} />
            {refreshing ? 'Testing…' : 'Run Diagnostics'}
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.75rem' }}>
        <div className="card" style={{ padding: '1.1rem 1.25rem', borderLeft: `4px solid ${overallHealthy ? '#22c55e' : '#ef4444'}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
            <StatusDot ok={overallHealthy} />
            <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em' }}>
              Overall Status
            </span>
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: overallHealthy ? '#22c55e' : '#ef4444' }}>
            {overallHealthy ? 'Healthy & Operational' : 'Degraded State'}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>
            {passedChecks} of {totalChecks} subsystem checks passing
          </div>
        </div>

        <div className="card" style={{ padding: '1.1rem 1.25rem', borderLeft: '3px solid #3b82f6' }}>
          <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em', marginBottom: '0.5rem' }}>
            Vector Indexing
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#3b82f6' }}>
            1,966 Vectors
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>
            CLIP (983) + Clay (983) collections
          </div>
        </div>

        <div className="card" style={{ padding: '1.1rem 1.25rem', borderLeft: '3px solid #a855f7' }}>
          <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em', marginBottom: '0.5rem' }}>
            Active Tasks
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#a855f7' }}>
            {jobs.filter(j => j.status === 'running').length} Running
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>
            {jobs.length} total tasks queued
          </div>
        </div>

        <div className="card" style={{ padding: '1.1rem 1.25rem', borderLeft: '3px solid #10b981' }}>
          <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em', marginBottom: '0.5rem' }}>
            Environment Mode
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#10b981' }}>
            On-Premises
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>
            100% air-gapped / offline capable
          </div>
        </div>
      </div>

      {/* Component Diagnostics List */}
      <div className="card" style={{ padding: '1.25rem', marginBottom: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
            <Server size={17} color="#3b82f6" />
            <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
              Subsystem Diagnostics
            </h2>
          </div>
          {lastRefresh && (
            <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
              Last checked: {lastRefresh.toLocaleTimeString()}
            </span>
          )}
        </div>

        {health?.checks && health.checks.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {health.checks.map((check, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '0.85rem 1rem', borderRadius: '10px',
                background: 'rgba(255,255,255,0.025)',
                border: '1px solid rgba(255,255,255,0.06)',
                gap: '1rem', flexWrap: 'wrap'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: 200 }}>
                  <StatusDot ok={check.status === 'healthy'} />
                  <div>
                    <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#f1f5f9', textTransform: 'capitalize' }}>
                      {check.component}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '0.15rem' }}>
                      {check.message}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span style={{
                    fontSize: '0.72rem', fontWeight: 700, padding: '0.2rem 0.6rem',
                    borderRadius: '999px',
                    background: check.status === 'healthy' ? 'rgba(34,197,94,0.14)' : 'rgba(239,68,68,0.14)',
                    color: check.status === 'healthy' ? '#22c55e' : '#ef4444',
                    border: `1px solid ${check.status === 'healthy' ? '#22c55e35' : '#ef444435'}`
                  }}>
                    {check.status?.toUpperCase()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: '#64748b', fontSize: '0.85rem' }}>No diagnostic details returned from backend.</p>
        )}
      </div>

      {/* Active Jobs Section */}
      <div className="card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', marginBottom: '1.25rem' }}>
          <Zap size={17} color="#f59e0b" />
          <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
            Active Processing Queue
          </h2>
        </div>

        {jobs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem 1rem', color: '#64748b' }}>
            <CheckCircle size={32} color="#10b981" style={{ margin: '0 auto 0.5rem', opacity: 0.8 }} />
            <p style={{ fontWeight: 600, color: '#f1f5f9', margin: 0 }}>All queues clear</p>
            <p style={{ fontSize: '0.8rem', margin: '0.25rem 0 0' }}>No active background indexing or change detection tasks</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {jobs.map((job) => (
              <div key={job.job_id} style={{
                padding: '0.85rem 1rem',
                background: 'rgba(255,255,255,0.025)',
                borderRadius: '8px',
                border: '1px solid rgba(255,255,255,0.05)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '1rem', flexWrap: 'wrap'
              }}>
                <div>
                  <div style={{ fontWeight: 600, color: '#f1f5f9', fontSize: '0.88rem', marginBottom: '0.2rem' }}>
                    {job.phase?.replace(/_/g, ' ')}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#64748b' }}>
                    {job.operation}
                  </div>
                </div>
                <span style={{
                  fontSize: '0.72rem', fontWeight: 700, padding: '0.15rem 0.5rem',
                  borderRadius: '4px',
                  background: job.status === 'running' ? 'rgba(59,130,246,0.12)' : 'rgba(251,191,36,0.12)',
                  color: job.status === 'running' ? '#60a5fa' : '#fbbf24',
                  border: `1px solid ${job.status === 'running' ? '#3b82f630' : '#fbbf2430'}`
                }}>
                  {job.status?.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default SystemHealth
