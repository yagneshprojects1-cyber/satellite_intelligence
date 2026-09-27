"""
Phase 15 - Streamlit Dashboard Entry Point
"""

import subprocess
import sys
import os

def main():
    """Run Streamlit dashboard using Python 3.12 venv"""
    print("Starting Satellite Intelligence Dashboard...")
    print("Access the dashboard at: http://localhost:8501")
    
    # Ensure we're using the venv Python
    venv_python = os.path.join(os.path.dirname(__file__), 'venv', 'Scripts', 'python.exe')
    
    # Run streamlit with the venv Python
    subprocess.run([
        venv_python, "-m", "streamlit", "run",
        "app/dashboard/main.py"
    ])

if __name__ == "__main__":
    main()
