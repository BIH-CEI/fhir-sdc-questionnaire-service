"""FastAPI application for SDC Form Manager."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.config import get_settings
import json
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


# Errors as FHIR OperationOutcome: FHIR/SDC clients expect an OperationOutcome
# body on 4xx/5xx, not FastAPI's {"detail": ...}. Handlers cover HTTPException
# (incl. unknown routes, 405), request validation and unexpected exceptions.
FHIR_JSON = "application/fhir+json"
ISSUE_CODE_BY_STATUS = {
    400: "invalid",
    401: "login",
    403: "forbidden",
    404: "not-found",
    405: "not-supported",
    409: "conflict",
    410: "deleted",
    412: "conflict",
    422: "processing",
    429: "throttled",
}


def operation_outcome(status: int, issues: list, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"resourceType": "OperationOutcome", "issue": issues},
        media_type=FHIR_JSON,
        headers=headers,
    )


def issue_for(status: int, diagnostics: str) -> dict:
    code = ISSUE_CODE_BY_STATUS.get(status, "exception" if status >= 500 else "processing")
    return {"severity": "error", "code": code, "diagnostics": diagnostics}


@app.exception_handler(StarletteHTTPException)
async def http_exception_as_operation_outcome(request: Request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail)
    return operation_outcome(exc.status_code, [issue_for(exc.status_code, detail)], exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error_as_operation_outcome(request: Request, exc: RequestValidationError):
    issues = []
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", ())]
        issue = {
            "severity": "error",
            # a body that is not JSON at all is a structural problem
            "code": "structure" if err.get("type") == "json_invalid" else "invalid",
            "diagnostics": err.get("msg", "invalid request"),
        }
        if loc:
            issue["expression"] = [".".join(loc)]
        issues.append(issue)
    return operation_outcome(422, issues or [issue_for(422, "invalid request")])


@app.exception_handler(Exception)
async def unexpected_error_as_operation_outcome(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}")
    return operation_outcome(500, [issue_for(500, "Internal server error")])


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


# Include routers
from app.routers import questionnaires, proctcae
app.include_router(questionnaires.router)
app.include_router(proctcae.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
