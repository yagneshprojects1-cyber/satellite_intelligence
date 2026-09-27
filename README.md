# SIH Satellite Intelligence

Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery.

## Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: v16 or higher (v18+ recommended)

## Setup Instructions

Your teammates only need to run these commands to get the entire project running.

### 1. Backend Setup

First, navigate to the backend directory, create a virtual environment, and activate it:

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate it (Windows)
.venv\Scripts\activate
# (For Mac/Linux, use: source .venv/bin/activate)
```

Next, install the required Python dependencies:

```bash
pip install -r requirements.txt
```

Start the backend server:

```bash
python run_backend.py
```
*(Note: The backend orchestrator will automatically check your folders and start processing any missing pipelines in the background!)*

---

### 2. Frontend Setup

Open a **new terminal window** (leave the backend running), navigate to the frontend directory, and install the Node dependencies:

```bash
cd frontend
npm i
```

Start the frontend dashboard:

```bash
npm run dev
```

---

## 3. Data & ML Models Setup (Important for New Team Members)

Because satellite images (`data/`) and machine learning models (`models/`) are several gigabytes in size, **they are intentionally ignored by Git** and will not be downloaded when you `git pull`. 

If you are setting up this project for the first time, you must manually place these files in your backend folder:

**Option 1: The Quickest Way (Shared Drive)**
1. The project lead should zip their local `backend/data` and `backend/models` folders and upload them to a shared Google Drive or OneDrive.
2. Download the `.zip` files from the shared drive.
3. Extract them directly into your `backend/` folder so you have `backend/data/` and `backend/models/`.

**Option 2: Download Scripts**
If you don't have the zip files, ensure you run the model download scripts (if provided in the codebase) to fetch the required CLAY `.ckpt` AI models before running the backend.

---

## Git Workflow (What to Push vs. What to Ignore)

Your `.gitignore` file is already perfectly configured to handle this automatically, but here is a quick guide so your team knows what is happening.

### ✅ WHAT GETS PUSHED (Code & Configuration)
These are the files that represent your actual work and should be committed to GitHub:
- `backend/` Python scripts (`.py` files)
- `frontend/src/` React code (`.jsx`, `.css`)
- Configuration files (`package.json`, `requirements.txt`, `vite.config.js`)
- `README.md` and `.gitignore`

### ❌ WHAT STAYS LOCAL (Do Not Push)
These files should never be pushed to GitHub to save space and protect security. Your `.gitignore` is already blocking them:
- **Virtual Environments**: `backend/.venv/` and `frontend/node_modules/` (These are generated locally by `pip install` and `npm i`).
- **Secret Keys**: `.env` (Never push passwords or paths).
- **Databases**: `backend/qdrant_storage/` and `database.sqlite` (Every team member builds their own local database automatically when they run the code).
- **ML Models**: `backend/models/` containing the `clay-v1.5.ckpt` (These files are massive. Team members should download the model weights locally).
- **Raw Data**: `backend/data/` (Satellite imagery `.tif` files and `.json` outputs are gigabytes of data and stay on your local hard drive).
