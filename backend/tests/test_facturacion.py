"""Tests del módulo de Facturación (MOD_05)."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token, get_password_hash
from models.paciente import Paciente
from models.tenant import Tenant
from models.usuario import Usuario


# ─── Fixture adicional: admin ─────────────────────────────────────────────────


@pytest_asyncio.fixture
async def admin_fixture(db_session: AsyncSession, tenant_fixture: Tenant) -> Usuario:
    """Crea un usuario administrador de prueba."""
    usuario = Usuario(
        id=uuid.uuid4(),
        tenant_id=tenant_fixture.id,
        email="admin@test.com",
        hashed_password=get_password_hash("Test1234!"),
        nombre="Admin",
        apellido="Sistema",
        rol="admin",
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()
    return usuario


@pytest_asyncio.fixture
async def admin_headers(admin_fixture: Usuario) -> dict[str, str]:
    """Headers de autorización para el usuario admin."""
    token = create_access_token({"sub": str(admin_fixture.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def recepcion_headers(
    db_session: AsyncSession, tenant_fixture: Tenant
) -> dict[str, str]:
    """Headers de autorización para un usuario de recepción."""
    usuario = Usuario(
        id=uuid.uuid4(),
        tenant_id=tenant_fixture.id,
        email="recepcion_fact@test.com",
        hashed_password=get_password_hash("Test1234!"),
        nombre="Recep",
        apellido="Fact",
        rol="recepcion",
        activo=True,
    )
    db_session.add(usuario)
    await db_session.flush()
    token = create_access_token({"sub": str(usuario.id)})
    return {"Authorization": f"Bearer {token}"}


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_crear_obra_social(
    async_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Verifica que un admin puede crear una obra social."""
    payload = {
        "nombre": "OSDE",
        "codigo": "OSDE-210",
        "plan": "210",
        "porcentaje_cobertura": 70.0,
        "copago_consulta": 500.0,
        "notas": "Plan clásico 210",
    }
    response = await async_client.post(
        "/api/v1/facturacion/obras-sociales",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "OSDE"
    assert data["codigo"] == "OSDE-210"
    assert data["porcentaje_cobertura"] == 70.0
    assert data["copago_consulta"] == 500.0
    assert data["activa"] is True
    assert "id" in data
    assert "tenant_id" in data


@pytest.mark.asyncio
async def test_listar_obras_sociales(
    async_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Verifica que GET obras-sociales devuelve la lista con la OS creada."""
    # Crear una OS primero
    payload = {
        "nombre": "Swiss Medical",
        "codigo": "SM-GOLD",
        "porcentaje_cobertura": 80.0,
        "copago_consulta": 300.0,
    }
    create_resp = await async_client.post(
        "/api/v1/facturacion/obras-sociales",
        json=payload,
        headers=admin_headers,
    )
    assert create_resp.status_code == 201

    response = await async_client.get(
        "/api/v1/facturacion/obras-sociales",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(os["codigo"] == "SM-GOLD" for os in data)


@pytest.mark.asyncio
async def test_crear_comprobante_sin_os(
    async_client: AsyncClient,
    recepcion_headers: dict[str, str],
    paciente_fixture: Paciente,
) -> None:
    """Verifica que sin obra social monto_particular == monto_total y cobertura == 0."""
    payload = {
        "paciente_id": str(paciente_fixture.id),
        "tipo": "recibo",
        "concepto": "Consulta médica general",
        "items": [
            {
                "descripcion": "Consulta general",
                "cantidad": 1.0,
                "precio_unitario": 5000.0,
            }
        ],
    }
    response = await async_client.post(
        "/api/v1/facturacion/comprobantes",
        json=payload,
        headers=recepcion_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["monto_total"] == 5000.0
    assert data["monto_particular"] == 5000.0
    assert data["monto_cobertura"] == 0.0
    assert data["monto_copago"] == 0.0
    assert data["estado"] == "pendiente"
    assert data["numero_comprobante"].startswith("REC-")
    assert len(data["items"]) == 1
    assert data["items"][0]["subtotal"] == 5000.0


@pytest.mark.asyncio
async def test_crear_comprobante_con_os(
    async_client: AsyncClient,
    admin_headers: dict[str, str],
    recepcion_headers: dict[str, str],
    paciente_fixture: Paciente,
) -> None:
    """Verifica que con obra social el monto_cobertura se calcula correctamente."""
    # Crear OS con 60% de cobertura y copago de 400
    os_payload = {
        "nombre": "IOMA",
        "codigo": "IOMA-001",
        "plan": "Bronce",
        "porcentaje_cobertura": 60.0,
        "copago_consulta": 400.0,
    }
    os_resp = await async_client.post(
        "/api/v1/facturacion/obras-sociales",
        json=os_payload,
        headers=admin_headers,
    )
    assert os_resp.status_code == 201
    obra_social_id = os_resp.json()["id"]

    payload = {
        "paciente_id": str(paciente_fixture.id),
        "obra_social_id": obra_social_id,
        "tipo": "factura_b",
        "concepto": "Consulta especialista + estudios",
        "items": [
            {
                "descripcion": "Consulta especialista",
                "cantidad": 1.0,
                "precio_unitario": 8000.0,
            },
            {
                "descripcion": "Laboratorio",
                "cantidad": 1.0,
                "precio_unitario": 2000.0,
            },
        ],
    }
    response = await async_client.post(
        "/api/v1/facturacion/comprobantes",
        json=payload,
        headers=recepcion_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["monto_total"] == 10000.0
    assert data["monto_cobertura"] == pytest.approx(6000.0, rel=1e-3)
    assert data["monto_copago"] == 400.0
    assert data["monto_particular"] == 0.0
    assert data["numero_comprobante"].startswith("FCTB-")
    assert data["obra_social_id"] == obra_social_id


@pytest.mark.asyncio
async def test_pagar_comprobante(
    async_client: AsyncClient,
    recepcion_headers: dict[str, str],
    paciente_fixture: Paciente,
) -> None:
    """Verifica que marcar un comprobante como pagado cambia el estado a 'pagado'."""
    # Crear comprobante primero
    create_payload = {
        "paciente_id": str(paciente_fixture.id),
        "tipo": "recibo",
        "concepto": "Consulta de seguimiento",
        "items": [
            {
                "descripcion": "Seguimiento",
                "cantidad": 1.0,
                "precio_unitario": 3000.0,
            }
        ],
    }
    create_resp = await async_client.post(
        "/api/v1/facturacion/comprobantes",
        json=create_payload,
        headers=recepcion_headers,
    )
    assert create_resp.status_code == 201
    comprobante_id = create_resp.json()["id"]
    assert create_resp.json()["estado"] == "pendiente"

    # Marcar como pagado
    pagar_resp = await async_client.post(
        f"/api/v1/facturacion/comprobantes/{comprobante_id}/pagar",
        headers=recepcion_headers,
    )
    assert pagar_resp.status_code == 200
    assert pagar_resp.json()["estado"] == "pagado"
    assert pagar_resp.json()["id"] == comprobante_id


@pytest.mark.asyncio
async def test_resumen_facturacion(
    async_client: AsyncClient,
    recepcion_headers: dict[str, str],
    admin_headers: dict[str, str],
    paciente_fixture: Paciente,
) -> None:
    """Verifica que el endpoint de resumen devuelve totales correctos."""
    # Crear un comprobante y pagarlo
    create_payload = {
        "paciente_id": str(paciente_fixture.id),
        "tipo": "recibo",
        "concepto": "Consulta para resumen",
        "items": [
            {
                "descripcion": "Consulta",
                "cantidad": 1.0,
                "precio_unitario": 4000.0,
            }
        ],
    }
    create_resp = await async_client.post(
        "/api/v1/facturacion/comprobantes",
        json=create_payload,
        headers=recepcion_headers,
    )
    assert create_resp.status_code == 201
    comprobante_id = create_resp.json()["id"]

    await async_client.post(
        f"/api/v1/facturacion/comprobantes/{comprobante_id}/pagar",
        headers=recepcion_headers,
    )

    # Consultar resumen del día (sin parámetros de fecha)
    resumen_resp = await async_client.get(
        "/api/v1/facturacion/resumen",
        headers=admin_headers,
    )
    assert resumen_resp.status_code == 200
    data = resumen_resp.json()
    assert "total_comprobantes" in data
    assert "monto_total" in data
    assert "monto_cobrado" in data
    assert "monto_pendiente" in data
    assert "por_obra_social" in data
    assert isinstance(data["por_obra_social"], list)
    assert data["total_comprobantes"] >= 1
    assert data["monto_cobrado"] >= 4000.0
