from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models as _models  # noqa: F401
from app.config import settings
from app.core.database import Base, close_db, engine
from app.core.logging import logger, setup_logging
from app.core.middleware import RequestIDMiddleware
from app.core.redis import close_redis
from app.routes.complaints import router as complaints_router
from app.routes.meta import router as meta_router
from app.routes.metrics import router as metrics_router
from app.routes.probes import router as probes_router
from app.routes.stats import router as stats_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager handling startup initialization
    and SIGTERM graceful shutdown connection draining.
    """
    setup_logging(settings.LOG_LEVEL)
    logger.info(f"Starting {settings.APP_NAME} in environment '{settings.ENVIRONMENT}'...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning(f"Database schema auto-creation skipped or failed on startup: {e}")
    yield
    logger.info("Received SIGTERM/SIGINT signal. Initiating graceful shutdown sequence...")
    await close_db()
    await close_redis()
    logger.info("Graceful shutdown complete. All database and cache connections closed.")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="CivicPulse Backend API for Citizen Complaint Management & AI Triage",
    lifespan=lifespan,
)

# Configure CORS Middleware for Local Frontend Origins & Expose Headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Cache", "X-Request-ID"],
)

# Attach Request ID middleware
app.add_middleware(RequestIDMiddleware)

# Custom Validation Exception Handler for Field-Level 400 Errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(item) for item in err.get("loc", []))
        errors.append({"field": loc, "message": err.get("msg")})
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": "Field-level request payload validation failed.",
            "errors": errors
        }
    )

# Register route modules
app.include_router(probes_router)
app.include_router(complaints_router)
app.include_router(stats_router)
app.include_router(meta_router)
app.include_router(metrics_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
