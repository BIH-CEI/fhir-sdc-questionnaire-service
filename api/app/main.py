"""FastAPI application for SDC Form Manager."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import get_settings
import logging

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=settings.log_level.upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FHIR SDC Form Manager API",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# IP logging middleware (5 lines!)
@app.middleware("http")
async def log_ip_access(request: Request, call_next):
    ip = request.client.host
    logger.info(f"IP: {ip} | {request.method} {request.url.path}")
    response = await call_next(request)
    return response


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "fhir_base_url": settings.fhir_base_url
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "FHIR SDC Form Manager API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


# Include routers (to be implemented)
# from app.routers import questionnaires, valuesets, terminology
# app.include_router(questionnaires.router)
# app.include_router(valuesets.router)
# app.include_router(terminology.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
