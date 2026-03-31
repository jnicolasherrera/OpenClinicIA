"""Dependencias reutilizables para los endpoints de FastAPI."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.logging import get_logger
from core.security import decode_token
from models.usuario import Usuario

logger = get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    """Extrae y valida el JWT Bearer del header Authorization.

    Args:
        credentials: Credenciales Bearer del header HTTP.
        db: Sesión de base de datos.

    Returns:
        El usuario autenticado.

    Raises:
        HTTPException 401: Si el token es inválido, expirado o el usuario no existe.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise unauthorized

    token_type: str | None = payload.get("type")
    if token_type != "access":
        raise unauthorized

    sub: str | None = payload.get("sub")
    if sub is None:
        raise unauthorized

    try:
        user_id = uuid.UUID(sub)
    except ValueError:
        raise unauthorized

    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user: Usuario | None = result.scalar_one_or_none()
    if user is None:
        raise unauthorized

    logger.info("Usuario autenticado", extra={"usuario_id": str(user_id), "rol": user.rol})
    return user


async def get_current_active_user(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Usuario:
    """Verifica que el usuario autenticado esté activo.

    Args:
        current_user: Usuario autenticado proveniente de get_current_user.

    Returns:
        El mismo usuario si está activo.

    Raises:
        HTTPException 400: Si el usuario está inactivo.
    """
    if not current_user.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo",
        )
    return current_user


def require_role(*roles: str):
    """Fábrica de dependencias que verifica el rol del usuario autenticado.

    Args:
        *roles: Roles permitidos para acceder al endpoint.

    Returns:
        Función de dependencia de FastAPI que valida el rol.
    """

    async def _check_role(
        current_user: Annotated[Usuario, Depends(get_current_active_user)],
    ) -> Usuario:
        """Verifica que el rol del usuario esté entre los roles permitidos.

        Args:
            current_user: Usuario autenticado activo.

        Returns:
            El usuario si su rol es permitido.

        Raises:
            HTTPException 403: Si el rol del usuario no está autorizado.
        """
        if current_user.rol not in roles:
            logger.warning(
                "Acceso denegado por rol insuficiente",
                extra={"rol_requerido": list(roles), "rol_actual": current_user.rol},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos suficientes",
            )
        return current_user

    return _check_role
