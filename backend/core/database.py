"""Configuración de la base de datos async con SQLAlchemy."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos ORM."""

    pass


def get_engine():
    """Retorna el engine async de SQLAlchemy (singleton por módulo).

    Usa una variable de módulo para cachear el engine entre llamadas.

    Returns:
        AsyncEngine configurado con la URL de la base de datos.
    """
    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


# Instancia de engine — creada al importar el módulo
# En tests, get_db se sobreescribe vía dependency_overrides por lo que
# este engine no se usa durante la ejecución de tests.
try:
    engine = get_engine()
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
except Exception:
    # Entorno donde asyncpg no está disponible (ej: generación de documentación)
    engine = None  # type: ignore[assignment]
    AsyncSessionLocal = None  # type: ignore[assignment]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI que provee una sesión de base de datos.

    La sesión se cierra automáticamente al finalizar el request.
    En caso de excepción, se realiza rollback automático.

    Yields:
        AsyncSession: Sesión de base de datos lista para usar.
    """
    async with AsyncSessionLocal() as session:  # type: ignore[misc]
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Crea todas las tablas definidas en los modelos.

    Usar solo en entorno de desarrollo. En producción usar Alembic.
    """
    from models import episodio  # noqa: F401
    from models import paciente  # noqa: F401
    from models import tenant  # noqa: F401
    from models import turno  # noqa: F401
    from models import usuario  # noqa: F401

    async with engine.begin() as conn:  # type: ignore[union-attr]
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Base de datos inicializada")
