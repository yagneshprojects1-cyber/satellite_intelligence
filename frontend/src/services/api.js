import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Health & Status
export const getHealth = async () => {
  const response = await api.get('/health')
  return response.data
}

export const getPipelineStatus = async () => {
  const response = await api.get('/pipeline/status')
  return response.data
}

export const getJobs = async () => {
  const response = await api.get('/pipeline/jobs')
  return response.data
}

export const submitJob = async (phase, operation = 'process') => {
  const response = await api.post('/pipeline/run', { phase, operation })
  return response.data
}

// Search
export const semanticSearch = async (query, topK = 10, filters = null) => {
  const response = await api.post('/search', { query, top_k: topK, filters })
  return response.data
}

export const imageSearch = async (tileId, topK = 10, filters = null) => {
  const response = await api.post('/image-search', { tile_id: tileId, top_k: topK, filters })
  return response.data
}

// Change Analysis
export const getChangeAnalysis = async () => {
  const response = await api.get('/change-analysis')
  return response.data
}

// Earliest Change
export const getEarliestChanges = async () => {
  const response = await api.get('/earliest-change')
  return response.data
}

// Similar Locations
export const getSimilarLocations = async (tileId, topK = 10) => {
  const response = await api.get(`/similar-locations?tile_id=${tileId}&top_k=${topK}`)
  return response.data
}

// Tiles
export const getTile = async (tileId) => {
  const response = await api.get(`/tiles/${tileId}`)
  return response.data
}

// Analyst Review
export const submitAnalystReview = async (reviewData) => {
  const response = await api.post('/analyst-review', reviewData)
  return response.data
}

export default api
