"""Alembic environment — soporte async con asyncpg."""

import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# ---------------------------------------------------------------------------
# Asegurar que el directorio raíz del backend esté en el path de Python para
# que los imports relativos (core.config, models.*) funcionen correctamente.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings  # noqa: E402
from core.database import Base  # noqa: E402

# Importar todos los modelos para que Alembic los detecte en Base.metadata
from models import base as _base_models  # noqa: E402, F401
from models.tenant import Tenant  # noqa: E402, F401
from models.usuario import Usuario  # noqa: E402, F401

# Los modelos paciente, turno y episodio pueden no existir todavía en el
# árbol de archivos durante la primera migración, por eso se importan con
# try/except para no bloquear la ejecución de alembic.
try:
    from models.paciente import Paciente  # noqa: F401
except ImportError:
    pass

try:
    from models.turno import Turno  # noqa: F401
except ImportError:
    pass

try:
    from models.episodio import Episodio  # noqa: F401
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Configuración de Alembic
# ---------------------------------------------------------------------------
config = context.config

# Interpretar la sección [loggers] del alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Sobreescribir la URL con el valor real desde Settings (soporta .env)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Modo offline — genera SQL sin conectarse a la DB
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Ejecuta las migraciones en modo offline (genera SQL puro)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Necesario para RLS y otras operaciones DDL complejas
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Modo online — se conecta a la DB y ejecuta las migraciones
# ---------------------------------------------------------------------------
def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        # Comparar tipos de servidor para detectar cambios de tipo
        compare_type=True,
        # Comparar valores de default del servidor
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Crea el engine async, obtiene una conexión síncrona y ejecuta las migraciones."""
    connectable = create_async_engine(
        settings.DATABASE_URL,
        poolclass=None,  # Usar NullPool para Alembic (sin pooling)
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Ejecuta las migraciones en modo online (con conexión real a la DB)."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
