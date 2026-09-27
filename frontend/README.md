# SIH Frontend

React-based frontend for the SIH Satellite Intelligence system.

## Tech Stack

- React 18
- Vite
- React Router
- Axios
- Leaflet (for maps)
- Lucide React (icons)

## Setup

```bash
cd frontend
npm install
```

## Development

```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Build

```bash
npm run build
```

## Preview

```bash
npm run preview
```

## Pages

- **Dashboard**: System health and pipeline status
- **Semantic Search**: Text-to-image search using CLIP
- **Image Search**: Image-to-image similarity search
- **Change Analysis**: View detected changes
- **Earliest Change**: First detected changes across timeline
- **Similar Locations**: Clay embedding-based clustering
- **Map**: Interactive map visualization
- **Analyst Review**: Review and validate changes

## API Communication

The frontend communicates with the backend API at `http://localhost:8000`. The Vite proxy configuration handles CORS.

## Features

- Real-time pipeline status updates
- Responsive design
- Dark theme
- Interactive visualizations
- Analyst workflow integration
