import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import { LayoutDashboard, Search, Image as ImageIcon, Activity, MapPin, Layers, CheckCircle } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import SemanticSearch from './pages/SemanticSearch'
import ImageSearch from './pages/ImageSearch'
import ChangeAnalysis from './pages/ChangeAnalysis'
import EarliestChange from './pages/EarliestChange'
import SimilarLocations from './pages/SimilarLocations'
import MapView from './pages/MapView'
import AnalystReview from './pages/AnalystReview'

function App() {
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
          <div className="sidebar-section-label">Workspace</div>
          <nav aria-label="Main navigation">
            <ul className="sidebar-nav">
              <li><NavLink to="/" end><LayoutDashboard size={19} /> Dashboard</NavLink></li>
              <li><NavLink to="/semantic-search"><Search size={19} /> Semantic Search</NavLink></li>
              <li><NavLink to="/image-search"><ImageIcon size={19} /> Image Search</NavLink></li>
              <li><NavLink to="/change-analysis"><Activity size={19} /> Change Analysis</NavLink></li>
              <li><NavLink to="/earliest-change"><MapPin size={19} /> Earliest Change</NavLink></li>
              <li><NavLink to="/similar-locations"><Layers size={19} /> Similar Locations</NavLink></li>
              <li><NavLink to="/map"><MapPin size={19} /> Map</NavLink></li>
              <li><NavLink to="/analyst-review"><CheckCircle size={19} /> Analyst Review</NavLink></li>
            </ul>
          </nav>
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
              <Route path="/map" element={<MapView />} />
              <Route path="/analyst-review" element={<AnalystReview />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  )
}

export default App
