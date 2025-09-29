#!/usr/bin/env python3
"""
Script to run the FastAPI backend server
"""
import uvicorn
import os
from pathlib import Path

if __name__ == "__main__":
    # Change to backend directory
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(backend_dir)]
    )
