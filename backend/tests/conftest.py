"""Fixtures de pytest para los tests de OpenClinicIA."""

import uuid
from collections.abc import AsyncGenerator
from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database import Base, get_db
from core.security import get_password_hash
from main import app
from models.paciente import Paciente
from models.tenant import Tenant
from models.usuario import Usuario

# ─── Base de datos en memoria para tests ──────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Crea el engine SQLite en memoria para la sesión de tests."""
    from sqlalchemy.pool import StaticPool

    _engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Provee una sesión de DB que hace rollback al finalizar cada test."""
    TestingSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Crea un AsyncClient que inyecta la sesión de test en la aplicación."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    app.dependency_overrides.clear()


# ─── Fixtures de datos ────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def tenant_fixture(db_session: AsyncSession) -> Tenant:
    """Crea un tenant de prueba."""
    tenant = Tenant(
        id=uuid.uuid4(),
        nombre="Clínica Test",
        slug="clinica-test",
        plan="pro",
        activo=True,
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def usuario_fixture(db_session: AsyncSession, tenant_fixture: Tenant) -> Usuario:
    """Crea un usuario médico de prueba."""
    usuario = Usuario(
        id=uuid.uuid4(),
        tenant_id=tenant_fixture.id,
        email="medico@test.com",
        hashed_password=get_password_hash("Test1234!"),
        nombre="Carlos",
        apellido="García",
        rol="medico",
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()
    return usuario


@pytest_asyncio.fixture
async def recepcion_fixture(db_session: AsyncSession, tenant_fixture: Tenant) -> Usuario:
    """Crea un usuario de recepción de prueba."""
    usuario = Usuario(
        id=uuid.uuid4(),
        tenant_id=tenant_fixture.id,
        email="recepcion@test.com",
        hashed_password=get_password_hash("Test1234!"),
        nombre="Ana",
        apellido="López",
        rol="recepcion",
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()
    return usuario


@pytest_asyncio.fixture
async def paciente_fixture(db_session: AsyncSession, tenant_fixture: Tenant) -> Paciente:
    """Crea un paciente de prueba."""
    paciente = Paciente(
        id=uuid.uuid4(),
        tenant_id=tenant_fixture.id,
        numero_historia="HC-001",
        nombre="Juan",
        apellido="Pérez",
        fecha_nacimiento=date(1985, 6, 15),
        dni="12345678",
        telefono="1155551234",
        email=None,
        obra_social="OSDE",
        activo=True,
    )
    db_session.add(paciente)
    await db_session.flush()
    return paciente


@pytest_asyncio.fixture
async def auth_token(
    async_client: AsyncClient,
    usuario_fixture: Usuario,
) -> str:
    """Obtiene un token JWT válido para el usuario de prueba."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "medico@test.com", "password": "Test1234!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token: str) -> dict[str, str]:
    """Retorna el header de autorización con el token JWT."""
    return {"Authorization": f"Bearer {auth_token}"}
