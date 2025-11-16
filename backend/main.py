"""
FastAPI Backend for AI Video Generator
"""

import logging
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("application_startup", message="FastAPI application starting up")

    # Initialize database
    try:
        from database import init_db
        init_db()
        logger.info("database_tables_created", message="Database initialized successfully")
    except Exception as e:
        logger.error("database_init_error", error=str(e))

    # Load MV (Music Video) module configs
    try:
        from mv.scene_generator import load_configs
        load_configs()
        logger.info("mv_configs_loaded", message="Music Video configs loaded successfully")
    except Exception as e:
        logger.error("mv_config_load_error", error=str(e))

    yield

    logger.info("application_shutdown", message="FastAPI application shutting down")


# Initialize FastAPI app
app = FastAPI(
    title="AI Video Generator API",
    description="Backend API for generating AI-powered video ads",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],  # Frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
from routers import generate, jobs, websocket, models, mv

app.include_router(generate.router)
app.include_router(jobs.router)
app.include_router(websocket.router)
app.include_router(models.router)
app.include_router(mv.router)


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
            "mv_create_scenes": "/api/mv/create_scenes"
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
