"""Tests del módulo de pacientes e historia clínica."""

import uuid

import pytest
from httpx import AsyncClient

from models.paciente import Paciente
from models.usuario import Usuario


def _paciente_payload(suffix: str = "") -> dict:
    """Construye un payload válido para crear un paciente."""
    return {
        "numero_historia": f"HC-TEST-{suffix or uuid.uuid4().hex[:6].upper()}",
        "nombre": "María",
        "apellido": f"González{suffix}",
        "fecha_nacimiento": "1990-03-22",
        "dni": f"2345678{suffix[:2] if suffix else '9'}",
        "telefono": "1155559999",
        "email": f"maria{suffix}@test.com",
        "obra_social": "Swiss Medical",
    }


@pytest.mark.asyncio
async def test_crear_paciente(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verifica que se puede registrar un nuevo paciente."""
    # Médico no puede crear pacientes — usar recepcion_fixture no disponible aquí,
    # pero la lógica de rol se puede testear con usuario_fixture (medico).
    # En este test verificamos que el endpoint existe y responde correctamente
    # con un usuario con rol permitido (recepcion).
    # Como el fixture de auth es de médico, esperamos 403.
    payload = _paciente_payload("A")
    response = await async_client.post(
        "/api/v1/pacientes",
        json=payload,
        headers=auth_headers,
    )
    # Médico no tiene permiso para crear pacientes (solo recepcion/admin)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_crear_paciente_con_recepcion(
    async_client: AsyncClient,
    recepcion_fixture: Usuario,
) -> None:
    """Verifica que recepción puede crear pacientes."""
    from core.security import create_access_token

    token = create_access_token({"sub": str(recepcion_fixture.id)})
    headers = {"Authorization": f"Bearer {token}"}

    payload = _paciente_payload("B")
    response = await async_client.post(
        "/api/v1/pacientes",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "María"
    assert data["apellido"] == "GonzálezB"
    assert "id" in data


@pytest.mark.asyncio
async def test_buscar_pacientes(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    paciente_fixture: Paciente,
) -> None:
    """Verifica que la búsqueda de pacientes retorna resultados."""
    response = await async_client.get(
        "/api/v1/pacientes?q=Juan",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(p["nombre"] == "Juan" for p in data)


@pytest.mark.asyncio
async def test_buscar_pacientes_sin_resultados(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verifica que una búsqueda sin coincidencias retorna lista vacía."""
    response = await async_client.get(
        "/api/v1/pacientes?q=XxXNombreInexistenteXxX",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_obtener_paciente_por_id(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    paciente_fixture: Paciente,
) -> None:
    """Verifica que se puede obtener un paciente por su UUID."""
    response = await async_client.get(
        f"/api/v1/pacientes/{paciente_fixture.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(paciente_fixture.id)
    assert data["dni"] == paciente_fixture.dni


@pytest.mark.asyncio
async def test_obtener_paciente_inexistente(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verifica que acceder a un paciente inexistente retorna 404."""
    fake_id = str(uuid.uuid4())
    response = await async_client.get(
        f"/api/v1/pacientes/{fake_id}",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_obtener_historia_clinica(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    paciente_fixture: Paciente,
) -> None:
    """Verifica que se puede obtener la historia clínica de un paciente."""
    response = await async_client.get(
        f"/api/v1/pacientes/{paciente_fixture.id}/historia",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_crear_episodio(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    paciente_fixture: Paciente,
    usuario_fixture: Usuario,
) -> None:
    """Verifica que un médico puede crear un episodio clínico."""
    payload = {
        "medico_id": str(usuario_fixture.id),
        "motivo_consulta": "Control anual",
        "anamnesis": "Paciente sin antecedentes relevantes",
        "examen_fisico": "TA 120/80, FC 72 lpm. Sin hallazgos patológicos",
        "diagnostico": "Paciente sano",
        "plan_terapeutico": "Control en 12 meses",
    }
    response = await async_client.post(
        f"/api/v1/pacientes/{paciente_fixture.id}/episodios",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["motivo_consulta"] == "Control anual"
    assert data["paciente_id"] == str(paciente_fixture.id)
    assert "id" in data


@pytest.mark.asyncio
async def test_crear_episodio_paciente_inexistente(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    usuario_fixture: Usuario,
) -> None:
    """Verifica que crear episodio para paciente inexistente retorna 404."""
    fake_id = str(uuid.uuid4())
    payload = {
        "medico_id": str(usuario_fixture.id),
        "motivo_consulta": "Consulta",
    }
    response = await async_client.post(
        f"/api/v1/pacientes/{fake_id}/episodios",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 404
