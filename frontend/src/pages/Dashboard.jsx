import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Search, Activity, Layers, Eye, Radar,
  ArrowRight, Satellite, ShieldCheck, Sparkles,
  MapPin, CheckCircle2, TrendingUp, Clock, Compass
} from 'lucide-react'

const CAPABILITIES = [
  {
    icon: Search,
    color: '#3b82f6',
    bg: 'rgba(59, 130, 246, 0.12)',
    border: 'rgba(59, 130, 246, 0.25)',
    title: 'Semantic & Free-Text Search',
    badge: 'PS 2.2.1',
    desc: 'Query satellite archives using natural language phrases like "construction near river" or "urban expansion". Filter by AOI bounding box, sensor, date, and valid data %.',
    link: '/semantic-search',
    btnText: 'Open Semantic Search'
  },
  {
    icon: Activity,
    color: '#a855f7',
    bg: 'rgba(168, 85, 247, 0.12)',
    border: 'rgba(168, 85, 247, 0.25)',
    title: 'Multi-Temporal Change Analysis',
    badge: 'PS 2.2.2',
    desc: 'Select a target scene to auto-locate historical baseline imagery. Perform multi-spectral differencing with automatic multi-class change categorization.',
    link: '/change-analysis',
    btnText: 'Analyze Changes'
  },
  {
    icon: Layers,
    color: '#f59e0b',
    bg: 'rgba(245, 158, 11, 0.12)',
    border: 'rgba(245, 158, 11, 0.25)',
    title: 'Discovery & Cluster Search',
    badge: 'PS 2.2.4',
    desc: 'Upload any satellite tile image to find visually and semantically similar territories across multi-year observation archives without manual queries.',
    link: '/similar-locations',
    btnText: 'Find Similar Sites'
  },
  {
    icon: Eye,
    color: '#10b981',
    bg: 'rgba(16, 185, 129, 0.12)',
    border: 'rgba(16, 185, 129, 0.25)',
    title: 'Analyst Review Queue',
    badge: 'PS 2.2.5',
    desc: 'Inspect AI-detected change candidates with side-by-side evidence. Confirm or reject findings with full geospatial provenance preserved in audit history.',
    link: '/analyst-review',
    btnText: 'Launch Review Queue'
  },
  {
    icon: Radar,
    color: '#38bdf8',
    bg: 'rgba(56, 189, 248, 0.12)',
    border: 'rgba(56, 189, 248, 0.25)',
    title: 'Earliest Change Monitoring',
    badge: 'PS 2.2.2',
    desc: 'Track earliest observation dates crossing confidence thresholds and monitor long-term persistence (Persistent vs. Transient vs. Emerging) across all sectors.',
    link: '/earliest-change',
    btnText: 'View Temporal Sequence'
  }
]

function Dashboard() {
  return (
    <div className="fade-in">
      {/* Hero Welcome Banner */}
      <div className="hero-banner" style={{
        border: '1px solid var(--glass-border)',
        borderRadius: '16px',
        padding: '2rem 2.25rem',
        marginBottom: '2rem',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          position: 'absolute', top: '-40px', right: '-40px',
          width: 220, height: 220, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, rgba(0,0,0,0) 70%)',
          pointerEvents: 'none'
        }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: '#60a5fa', fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.5rem' }}>
          <Sparkles size={16} /> On-Premises Earth Observation Platform
        </div>

        <h1 style={{ fontSize: '1.85rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.5rem', lineHeight: 1.25 }}>
          Satellite Intelligence Hub
        </h1>

        <p style={{ color: '#94a3b8', fontSize: '0.95rem', maxWidth: '820px', margin: 0, lineHeight: 1.6 }}>
          Query satellite imagery archives by semantic content and multi-temporal change. Incorporates natural-language search, unsupervised site clustering, multi-class change categorization, and an analyst review queue with full geospatial provenance.
        </p>
      </div>

      {/* Metrics Header Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.1rem', marginBottom: '2rem' }}>
        <div className="card" style={{ padding: '1.15rem 1.25rem', marginBottom: 0, borderLeft: '3px solid #3b82f6' }}>
          <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em', marginBottom: '0.35rem' }}>
            Indexed Satellite Tiles
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#3b82f6' }}>
            983 Tiles
          </div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
            2022 • 2023 • 2024 Sentinel-2
          </div>
        </div>

        <div className="card" style={{ padding: '1.15rem 1.25rem', marginBottom: 0, borderLeft: '3px solid #a855f7' }}>
          <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em', marginBottom: '0.35rem' }}>
            Monitored Sectors
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#a855f7' }}>
            11 Sectors
          </div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
            Geospatial tracking zones
          </div>
        </div>

        <div className="card" style={{ padding: '1.15rem 1.25rem', marginBottom: 0, borderLeft: '3px solid #f59e0b' }}>
          <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em', marginBottom: '0.35rem' }}>
            Detected Change Events
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f59e0b' }}>
            10 Events
          </div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
            Construction, Clearance, Water
          </div>
        </div>

        <div className="card" style={{ padding: '1.15rem 1.25rem', marginBottom: 0, borderLeft: '3px solid #10b981' }}>
          <div style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em', marginBottom: '0.35rem' }}>
            AI Foundation Models
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#10b981' }}>
            CLIP + RS
          </div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
            Multi-spectral feature encoder
          </div>
        </div>
      </div>

      {/* Core Capabilities Section Header */}
      <div style={{ marginBottom: '1.25rem' }}>
        <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Compass size={20} style={{ color: '#38bdf8' }} />
          Core Platform Capabilities
        </h2>
        <p style={{ fontSize: '0.85rem', color: '#94a3b8', margin: '0.2rem 0 0' }}>
          Explore key tools designed for intelligence analyst discovery and multi-temporal verification
        </p>
      </div>

      {/* Capabilities Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
        {CAPABILITIES.map((cap) => {
          const Icon = cap.icon
          return (
            <div
              key={cap.title}
              className="card"
              style={{
                marginBottom: 0,
                display: 'flex',
                flexDirection: 'column',
                padding: '1.5rem',
                border: '1px solid var(--glass-border)',
                transition: 'transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease'
              }}
            >
              {/* Card Header: Icon & Badge */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <div style={{
                  width: 44, height: 44, borderRadius: '10px',
                  background: cap.bg, border: `1px solid ${cap.border}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: cap.color
                }}>
                  <Icon size={22} />
                </div>
                <span style={{
                  fontSize: '0.7rem', fontWeight: 700, padding: '0.2rem 0.55rem',
                  borderRadius: '999px', background: 'rgba(255,255,255,0.05)',
                  color: cap.color, border: `1px solid ${cap.border}`
                }}>
                  {cap.badge}
                </span>
              </div>

              {/* Title & Desc */}
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.5rem' }}>
                {cap.title}
              </h3>
              <p style={{ fontSize: '0.84rem', color: '#94a3b8', lineHeight: 1.55, flex: 1, marginBottom: '1.25rem' }}>
                {cap.desc}
              </p>

              {/* Action Button */}
              <Link
                to={cap.link}
                className="btn btn-secondary"
                style={{
                  justifyContent: 'space-between',
                  fontSize: '0.84rem',
                  padding: '0.65rem 1rem',
                  textDecoration: 'none',
                  borderColor: cap.border
                }}
              >
                <span>{cap.btnText}</span>
                <ArrowRight size={15} style={{ color: cap.color }} />
              </Link>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default Dashboard
