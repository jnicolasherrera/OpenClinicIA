"""Endpoints de autenticación."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user
from api.v1.auth.schemas import LoginRequest, RefreshRequest, TokenResponse, UserResponse
from core.database import get_db
from core.logging import get_logger
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from models.usuario import Usuario

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Autentica un usuario y retorna tokens JWT.

    Args:
        body: Email y contraseña del usuario.
        db: Sesión de base de datos.

    Returns:
        Tokens de acceso y refresh.

    Raises:
        HTTPException 401: Si las credenciales son incorrectas o el usuario está inactivo.
    """
    result = await db.execute(
        select(Usuario).where(Usuario.email == body.email)
    )
    user: Usuario | None = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        logger.warning("Intento de login fallido")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo",
        )

    logger.info("Login exitoso", extra={"usuario_id": str(user.id), "rol": user.rol})
    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Renueva los tokens JWT usando un refresh token válido.

    Args:
        body: Refresh token actual.
        db: Sesión de base de datos.

    Returns:
        Nuevos tokens de acceso y refresh.

    Raises:
        HTTPException 401: Si el refresh token es inválido o el usuario no existe.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido o expirado",
    )
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise unauthorized

    if payload.get("type") != "refresh":
        raise unauthorized

    sub: str | None = payload.get("sub")
    if sub is None:
        raise unauthorized

    import uuid

    try:
        user_id = uuid.UUID(sub)
    except ValueError:
        raise unauthorized

    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user: Usuario | None = result.scalar_one_or_none()

    if user is None or not user.activo:
        raise unauthorized

    logger.info("Tokens renovados", extra={"usuario_id": str(user_id)})
    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_me(
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
) -> UserResponse:
    """Retorna los datos del usuario actualmente autenticado.

    Args:
        current_user: Usuario autenticado extraído del JWT.

    Returns:
        Datos públicos del usuario.
    """
    return UserResponse.model_validate(current_user)
