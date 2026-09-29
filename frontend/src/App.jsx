import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Search, Image as ImageIcon, Activity,
  Clock, Layers, CheckCircle, Sun, Moon, Server
} from 'lucide-react'
import Dashboard from './pages/Dashboard'
import SemanticSearch from './pages/SemanticSearch'
import ImageSearch from './pages/ImageSearch'
import ChangeAnalysis from './pages/ChangeAnalysis'
import EarliestChange from './pages/EarliestChange'
import SimilarLocations from './pages/SimilarLocations'
import AnalystReview from './pages/AnalystReview'
import SystemHealth from './pages/SystemHealth'

function App() {
  const [theme, setTheme] = useState('dark')

  useEffect(() => {
    const saved = localStorage.getItem('sih_theme') || 'dark'
    setTheme(saved)
    if (saved === 'light') {
      document.body.classList.add('light-theme')
    } else {
      document.body.classList.remove('light-theme')
    }
  }, [])

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    localStorage.setItem('sih_theme', next)
    if (next === 'light') {
      document.body.classList.add('light-theme')
    } else {
      document.body.classList.remove('light-theme')
    }
  }

  return (
    <Router>
      <div className="app">
        <aside className="sidebar">
          <NavLink to="/" className="sidebar-brand" style={{ padding: '0.75rem 1rem', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <img
              src="/logo.png"
              alt="SIH Satellite Intelligence"
              style={{ height: '78px', width: '100%', objectFit: 'contain' }}
            />
          </NavLink>

          <div className="sidebar-section-label">Capabilities</div>
          <nav aria-label="Main navigation" style={{ flex: 1 }}>
            <ul className="sidebar-nav">
              <li><NavLink to="/" end><LayoutDashboard size={19} /> Dashboard</NavLink></li>
              <li><NavLink to="/semantic-search"><Search size={19} /> Semantic Search</NavLink></li>
              <li><NavLink to="/image-search"><ImageIcon size={19} /> Image Search</NavLink></li>
              <li><NavLink to="/change-analysis"><Activity size={19} /> Change Analysis</NavLink></li>
              <li><NavLink to="/earliest-change"><Clock size={19} /> Earliest Change</NavLink></li>
              <li><NavLink to="/similar-locations"><Layers size={19} /> Similar Locations</NavLink></li>
              <li><NavLink to="/analyst-review"><CheckCircle size={19} /> Analyst Review</NavLink></li>
              <li style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                <NavLink to="/system-health"><Server size={19} /> System Health</NavLink>
              </li>
            </ul>
          </nav>

          {/* Theme Toggle Button */}
          <div className="sidebar-footer" style={{ borderTop: '1px solid var(--glass-border)', paddingTop: '0.85rem' }}>
            <button
              onClick={toggleTheme}
              className="btn btn-secondary"
              style={{
                width: '100%',
                fontSize: '0.8rem',
                padding: '0.55rem 0.75rem',
                justifyContent: 'center',
                gap: '0.5rem'
              }}
            >
              {theme === 'dark' ? <Sun size={15} color="#fbbf24" /> : <Moon size={15} color="#3b82f6" />}
              <span>{theme === 'dark' ? 'Light Theme' : 'Dark Theme'}</span>
            </button>
          </div>
        </aside>

        <div className="app-content">
          <main className="container">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/semantic-search" element={<SemanticSearch />} />
              <Route path="/image-search" element={<ImageSearch />} />
              <Route path="/change-analysis" element={<ChangeAnalysis />} />
              <Route path="/earliest-change" element={<EarliestChange />} />
              <Route path="/similar-locations" element={<SimilarLocations />} />
              <Route path="/analyst-review" element={<AnalystReview />} />
              <Route path="/system-health" element={<SystemHealth />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  )
}

export default App
