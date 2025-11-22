"""
FastAPI Backend for AI Video Generator
"""

import logging
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.models import SecurityScheme
from fastapi.security import APIKeyHeader
from contextlib import asynccontextmanager
import time

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger()

# Import settings
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("application_startup", message="FastAPI application starting up")

    # Validate configuration
    try:
        from config import settings
        settings.validate_dynamodb_config()
        logger.info("config_validated", message="Configuration validated successfully")
    except ValueError as e:
        logger.error("config_validation_failed", error=str(e))
        raise

    # Initialize database
    try:
        from database import init_db
        init_db()
        logger.info("database_tables_created", message="Database initialized successfully")
    except Exception as e:
        logger.error("database_init_error", error=str(e))

    # Initialize DynamoDB tables
    try:
        from dynamodb_config import init_dynamodb_tables
        init_dynamodb_tables()
        logger.info("dynamodb_tables_created", message="DynamoDB tables initialized successfully")
    except Exception as e:
        logger.error("dynamodb_init_error", error=str(e))

    # Initialize MV (Music Video) config flavors system
    try:
        from mv.config_manager import initialize_config_flavors
        initialize_config_flavors()
        logger.info("mv_config_flavors_initialized", message="Music Video config flavors initialized successfully")
    except Exception as e:
        logger.error("mv_config_flavor_init_error", error=str(e))

    yield

    logger.info("application_shutdown", message="FastAPI application shutting down")


# Initialize FastAPI app
app = FastAPI(
    title="AI Video Generator API",
    description="Backend API for generating AI-powered video ads",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
    }
)

# Configure OpenAPI schema to include API key authentication
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication. Use the value from your .env file (API_KEY)"
        }
    }
    # Apply security globally to all endpoints
    openapi_schema["security"] = [{"ApiKeyAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# CORS middleware configuration
# Get allowed origins from environment variable
cors_origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://badapples.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Authentication middleware - applies to all /api/ routes
@app.middleware("http")
async def api_authentication_middleware(request: Request, call_next):
    """Authenticate all /api/ routes with API key"""
    # Skip authentication for non-API routes
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    # Skip authentication for health check and docs
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    # Skip authentication for CORS preflight requests
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # Import here to avoid circular imports
    # Import the verification function (not the FastAPI dependency)
    import auth
    
    # Get API key from header or query parameter
    api_key_header = request.headers.get("X-API-Key")
    api_key_query = request.query_params.get("api_key")
    api_key = api_key_header or api_key_query
    
    if not api_key:
        return JSONResponse(
            status_code=401,
            content={
                "error": "Unauthorized",
                "message": "API key missing. Provide X-API-Key header or ?api_key=YOUR_KEY",
                "detail": "Authentication required for /api/ endpoints"
            },
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # Verify API key using the auth module's verification function
    if not auth.check_api_key(api_key):
        return JSONResponse(
            status_code=401,
            content={
                "error": "Unauthorized",
                "message": "Invalid API key",
                "detail": "The provided API key is not valid"
            },
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # Continue to the endpoint
    return await call_next(request)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = time.time()

    # Log request
    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        client_host=request.client.host if request.client else None
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log response
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=f"{process_time:.3f}s"
        )

        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            "request_failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            process_time=f"{process_time:.3f}s"
        )
        raise


# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_type=type(exc).__name__
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "details": str(exc) if app.debug else None
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint

    Returns:
        dict: Health status of the API
    """
    return {
        "status": "healthy",
        "service": "ai-video-generator",
        "version": "1.0.0"
    }


# Include routers
from routers import projects
from routers import generate, jobs, websocket, models, mv
from routers import mv_projects
from routers import audio_converter

app.include_router(generate.router)
app.include_router(jobs.router)
app.include_router(websocket.router)
app.include_router(models.router)
app.include_router(mv.router)
app.include_router(audio_converter.router)
app.include_router(mv_projects.router)
logger.info("router_loaded", router="mv_projects")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI Video Generator API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "generate": "/api/generate",
            "job_status": "/api/jobs/{job_id}",
            "websocket": "/ws/jobs/{job_id}",
            "mv_create_scenes": "/api/mv/create_scenes",
            "mv_generate_character_reference": "/api/mv/generate_character_reference",
            "mv_generate_video": "/api/mv/generate_video",
            "mv_lipsync": "/api/mv/lipsync",
            "mv_get_video": "/api/mv/get_video/{video_id}",
            "audio_download": "/api/audio/download",
            "audio_get": "/api/audio/get/{audio_id}",
            "audio_info": "/api/audio/info/{audio_id}"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
