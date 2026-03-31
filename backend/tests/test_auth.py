"""Tests del módulo de autenticación."""

import pytest
from httpx import AsyncClient

from models.usuario import Usuario


@pytest.mark.asyncio
async def test_login_exitoso(
    async_client: AsyncClient,
    usuario_fixture: Usuario,
) -> None:
    """Verifica que un usuario con credenciales válidas recibe tokens JWT."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "medico@test.com", "password": "Test1234!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


@pytest.mark.asyncio
async def test_login_credenciales_invalidas(
    async_client: AsyncClient,
    usuario_fixture: Usuario,
) -> None:
    """Verifica que credenciales incorrectas retornan 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "medico@test.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_login_email_inexistente(
    async_client: AsyncClient,
) -> None:
    """Verifica que un email que no existe retorna 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "noexiste@test.com", "password": "cualquier"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_sin_token(
    async_client: AsyncClient,
    usuario_fixture: Usuario,
) -> None:
    """Verifica que acceder a /me sin token retorna 401."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_con_token_invalido(
    async_client: AsyncClient,
    usuario_fixture: Usuario,
) -> None:
    """Verifica que un token inválido retorna 401."""
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer token.invalido.firma"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_con_token_valido(
    async_client: AsyncClient,
    usuario_fixture: Usuario,
    auth_headers: dict[str, str],
) -> None:
    """Verifica que un token válido retorna los datos del usuario."""
    response = await async_client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "medico@test.com"
    assert data["rol"] == "medico"
    assert data["nombre"] == "Carlos"
    assert data["apellido"] == "García"
    assert "id" in data


@pytest.mark.asyncio
async def test_refresh_token(
    async_client: AsyncClient,
    usuario_fixture: Usuario,
) -> None:
    """Verifica que el refresh token genera nuevos tokens válidos."""
    # Login para obtener tokens iniciales
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "medico@test.com", "password": "Test1234!"},
    )
    assert login_resp.status_code == 200
    refresh_token = login_resp.json()["refresh_token"]

    # Renovar tokens
    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # El nuevo access_token debe ser válido
    me_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_resp.status_code == 200


@pytest.mark.asyncio
async def test_refresh_con_access_token_falla(
    async_client: AsyncClient,
    usuario_fixture: Usuario,
    auth_token: str,
) -> None:
    """Verifica que usar un access_token como refresh_token retorna 401."""
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": auth_token},
    )
    assert response.status_code == 401
