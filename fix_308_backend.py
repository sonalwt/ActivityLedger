# Fix 308 Redirect Issue - Backend Update for main.py

# Add this to your FastAPI main.py file to handle the sync endpoint properly:

from fastapi import FastAPI
from fastapi.routing import APIRoute

# After creating your FastAPI app, add this:
# This ensures the /api/sync endpoint works without redirects

# Method 1: Disable redirect_slashes for the entire app
app = FastAPI(
    title="Timesheet API",
    version="1.0.0",
    redirect_slashes=False  # This prevents 308 redirects
)

# Method 2: Define both endpoints (with and without slash)
@app.post("/api/sync", response_model=dict)
async def receive_sync_data(sync_data: dict, db: Session = Depends(get_db)):
    """Main sync endpoint - no trailing slash"""
    # Your existing sync code here
    pass

@app.post("/api/sync/", include_in_schema=False, response_model=dict)
async def receive_sync_data_slash(sync_data: dict, db: Session = Depends(get_db)):
    """Duplicate endpoint with trailing slash to avoid redirects"""
    return await receive_sync_data(sync_data, db)

# Method 3: Custom route class to handle trailing slashes
class NoRedirectRoute(APIRoute):
    def get_route_handler(self):
        original_route_handler = super().get_route_handler()
        async def route_handler(request):
            request.scope["path"] = request.scope["path"].rstrip("/")
            return await original_route_handler(request)
        return route_handler

# Then use it:
app.router.route_class = NoRedirectRoute