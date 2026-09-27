import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
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
        <nav className="navbar">
          <Link to="/" className="navbar-brand">
            SIH Satellite Intelligence
          </Link>
          <ul className="navbar-nav">
            <li><Link to="/"><LayoutDashboard size={20} /> Dashboard</Link></li>
            <li><Link to="/semantic-search"><Search size={20} /> Semantic Search</Link></li>
            <li><Link to="/image-search"><ImageIcon size={20} /> Image Search</Link></li>
            <li><Link to="/change-analysis"><Activity size={20} /> Change Analysis</Link></li>
            <li><Link to="/earliest-change"><MapPin size={20} /> Earliest Change</Link></li>
            <li><Link to="/similar-locations"><Layers size={20} /> Similar Locations</Link></li>
            <li><Link to="/map"><MapPin size={20} /> Map</Link></li>
            <li><Link to="/analyst-review"><CheckCircle size={20} /> Analyst Review</Link></li>
          </ul>
        </nav>

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
    </Router>
  )
}

export default App
