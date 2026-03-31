"""Tests del módulo de agenda de turnos."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.paciente import Paciente
from models.tenant import Tenant
from models.usuario import Usuario


def _turno_payload(
    paciente_id: uuid.UUID,
    medico_id: uuid.UUID,
    fecha_hora: datetime | None = None,
    duracion: int = 30,
) -> dict:
    """Construye el payload para crear un turno."""
    if fecha_hora is None:
        fecha_hora = datetime.now(timezone.utc) + timedelta(days=1)
    return {
        "paciente_id": str(paciente_id),
        "medico_id": str(medico_id),
        "fecha_hora": fecha_hora.isoformat(),
        "duracion_minutos": duracion,
        "motivo": "Control rutinario",
    }


@pytest.mark.asyncio
async def test_crear_turno(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    paciente_fixture: Paciente,
    usuario_fixture: Usuario,
) -> None:
    """Verifica que se puede crear un turno correctamente."""
    payload = _turno_payload(paciente_fixture.id, usuario_fixture.id)
    response = await async_client.post(
        "/api/v1/agenda/turnos",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["estado"] == "programado"
    assert data["motivo"] == "Control rutinario"
    assert str(paciente_fixture.id) == data["paciente_id"]
    assert "id" in data


@pytest.mark.asyncio
async def test_solapamiento_turnos(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    paciente_fixture: Paciente,
    usuario_fixture: Usuario,
) -> None:
    """Verifica que crear dos turnos en el mismo horario retorna 409."""
    fecha_hora = datetime.now(timezone.utc) + timedelta(days=2, hours=1)

    payload = _turno_payload(paciente_fixture.id, usuario_fixture.id, fecha_hora, 30)

    # Crear primer turno
    r1 = await async_client.post(
        "/api/v1/agenda/turnos", json=payload, headers=auth_headers
    )
    assert r1.status_code == 201

    # Segundo turno en el mismo horario — debe fallar
    r2 = await async_client.post(
        "/api/v1/agenda/turnos", json=payload, headers=auth_headers
    )
    assert r2.status_code == 409
    assert "solapamiento" in r2.json()["detail"].lower() or "horario" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_obtener_sala_espera_vacia(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verifica que la sala de espera vacía retorna una lista vacía."""
    response = await async_client.get(
        "/api/v1/agenda/sala-espera",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_ingresar_sala(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    paciente_fixture: Paciente,
    usuario_fixture: Usuario,
) -> None:
    """Verifica que un turno pasa a estado en_sala al ingresar."""
    fecha_hora = datetime.now(timezone.utc) + timedelta(days=3, hours=2)
    payload = _turno_payload(paciente_fixture.id, usuario_fixture.id, fecha_hora)

    # Crear turno
    create_resp = await async_client.post(
        "/api/v1/agenda/turnos", json=payload, headers=auth_headers
    )
    assert create_resp.status_code == 201
    turno_id = create_resp.json()["id"]

    # Ingresar a sala
    ingreso_resp = await async_client.post(
        f"/api/v1/agenda/turnos/{turno_id}/ingresar-sala",
        headers=auth_headers,
    )
    assert ingreso_resp.status_code == 200
    data = ingreso_resp.json()
    assert data["estado"] == "en_sala"
    assert data["sala_espera_ingreso"] is not None


@pytest.mark.asyncio
async def test_obtener_sala_espera(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    paciente_fixture: Paciente,
    usuario_fixture: Usuario,
) -> None:
    """Verifica que la sala de espera muestra turnos en estado en_sala."""
    fecha_hora = datetime.now(timezone.utc) + timedelta(days=4, hours=3)
    payload = _turno_payload(paciente_fixture.id, usuario_fixture.id, fecha_hora)

    create_resp = await async_client.post(
        "/api/v1/agenda/turnos", json=payload, headers=auth_headers
    )
    assert create_resp.status_code == 201
    turno_id = create_resp.json()["id"]

    await async_client.post(
        f"/api/v1/agenda/turnos/{turno_id}/ingresar-sala",
        headers=auth_headers,
    )

    sala_resp = await async_client.get(
        "/api/v1/agenda/sala-espera",
        headers=auth_headers,
    )
    assert sala_resp.status_code == 200
    items = sala_resp.json()
    assert any(item["turno_id"] == turno_id for item in items)


@pytest.mark.asyncio
async def test_cancelar_turno(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    paciente_fixture: Paciente,
    usuario_fixture: Usuario,
) -> None:
    """Verifica que un turno puede cancelarse via PATCH."""
    fecha_hora = datetime.now(timezone.utc) + timedelta(days=5, hours=4)
    payload = _turno_payload(paciente_fixture.id, usuario_fixture.id, fecha_hora)

    create_resp = await async_client.post(
        "/api/v1/agenda/turnos", json=payload, headers=auth_headers
    )
    assert create_resp.status_code == 201
    turno_id = create_resp.json()["id"]

    cancel_resp = await async_client.patch(
        f"/api/v1/agenda/turnos/{turno_id}",
        json={"estado": "cancelado"},
        headers=auth_headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["estado"] == "cancelado"


@pytest.mark.asyncio
async def test_turno_no_encontrado(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verifica que acceder a un turno inexistente retorna 404."""
    fake_id = str(uuid.uuid4())
    response = await async_client.patch(
        f"/api/v1/agenda/turnos/{fake_id}",
        json={"estado": "cancelado"},
        headers=auth_headers,
    )
    assert response.status_code == 404
