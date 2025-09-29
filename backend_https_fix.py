# Add this to your backend/main.py after the app creation

from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api-timesheet.firsteconomy.com", "*.firsteconomy.com"]
)

# Add middleware to handle X-Forwarded headers
@app.middleware("http")
async def handle_forwarded_proto(request: Request, call_next):
    # Check if request is coming through a proxy
    forwarded_proto = request.headers.get("X-Forwarded-Proto")
    if forwarded_proto == "https":
        # Update the URL scheme to prevent redirects
        request.scope["scheme"] = "https"
    
    response = await call_next(request)
    return response
