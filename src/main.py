"""
AIRA — Application entry point.

Creates the FastAPI app, wires middleware, registers routers,
and manages the DB lifecycle via the lifespan event.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.settings import settings
from src.db.base import Base
from src.db.session import engine
from src.api.routes import router as api_router


logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Lifespan — startup / shutdown
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: dispose engine cleanly
    await engine.dispose()


# ------------------------------------------------------------------
# App
# ------------------------------------------------------------------
app = FastAPI(
    title="AIRA",
    description="AI-Powered Responsive Intelligence Assistant",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_dev else None,      # Swagger UI in dev only
    redoc_url="/redoc" if settings.is_dev else None,
)


# ------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,      # required for cookie-based JWT auth
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Exception handlers
# ------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Pydantic / request validation failures → clean 422."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
        },
    )

@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------
app.include_router(api_router, prefix="/api")
