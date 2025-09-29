# minimal_main.py - A minimal FastAPI app for testing
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Timesheet API - Minimal", version="1.0.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Timesheet API is running (minimal mode)"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "mode": "minimal"}

if __name__ == "__main__":
    import uvicorn
    print("Starting minimal FastAPI server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
