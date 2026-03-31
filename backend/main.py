"""Punto de entrada principal de la aplicación FastAPI de OpenClinicIA."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.router import api_v1_router
from core.config import settings
from core.logging import configure_logging, get_logger

configure_logging(level="DEBUG" if settings.DEBUG else "INFO")
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestiona el ciclo de vida de la aplicación (startup y shutdown).

    Args:
        app: Instancia de la aplicación FastAPI.

    Yields:
        None durante la ejecución de la aplicación.
    """
    # Startup
    logger.info(
        "Iniciando OpenClinicIA",
        extra={"environment": settings.ENVIRONMENT, "debug": settings.DEBUG},
    )

    if settings.ENVIRONMENT == "development":
        from core.database import init_db

        await init_db()
        logger.info("Base de datos inicializada en modo desarrollo")

    logger.info("OpenClinicIA lista para recibir requests")
    yield

    # Shutdown
    logger.info("Cerrando OpenClinicIA")
    from core.database import engine

    await engine.dispose()
    logger.info("Conexiones de base de datos cerradas")


def create_application() -> FastAPI:
    """Fábrica que crea y configura la aplicación FastAPI.

    Returns:
        Instancia de FastAPI completamente configurada.
    """
    application = FastAPI(
        title="OpenClinicIA",
        description="Sistema de gestión clínica con inteligencia artificial",
        version="1.0.0",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_v1_router)

    return application


app = create_application()


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Endpoint de health check para balanceadores de carga y orchestration.

    Returns:
        Diccionario con status y versión de la aplicación.
    """
    return {"status": "ok", "version": "1.0.0", "environment": settings.ENVIRONMENT}
