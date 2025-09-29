# test_minimal_fastapi.py
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "FastAPI is working!"}

@app.get("/test")
def test_endpoint():
    return {"status": "ok", "test": "successful"}

if __name__ == "__main__":
    print("Starting minimal FastAPI test server...")
    print("Check: http://localhost:8001")
    print("Press Ctrl+C to stop")
    uvicorn.run(app, host="0.0.0.0", port=8001)
