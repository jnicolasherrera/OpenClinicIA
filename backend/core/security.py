"""Utilidades de seguridad: JWT, hashing de contrasenas."""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


def get_password_hash(password: str) -> str:
    """Genera el hash bcrypt de una contrasena en texto plano.

    Args:
        password: Contrasena en texto plano (max. 72 bytes para bcrypt).

    Returns:
        Hash bcrypt de la contrasena como cadena UTF-8.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica que una contrasena en texto plano coincida con su hash.

    Args:
        plain_password: Contrasena en texto plano provista por el usuario.
        hashed_password: Hash almacenado en la base de datos.

    Returns:
        True si la contrasena es valida, False en caso contrario.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


_REFRESH_TOKEN_TYPE = "refresh"
_ACCESS_TOKEN_TYPE = "access"


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Genera un JWT de acceso firmado con los datos proporcionados.

    Args:
        data: Payload a incluir en el token.
        expires_delta: Tiempo de expiracion personalizado. Si es None,
            usa ACCESS_TOKEN_EXPIRE_MINUTES de la configuracion.

    Returns:
        Token JWT como cadena.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": _ACCESS_TOKEN_TYPE})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Genera un JWT de refresh para el sujeto indicado.

    Args:
        subject: Identificador unico del usuario (normalmente su UUID como str).

    Returns:
        Token JWT de refresh como cadena.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "type": _REFRESH_TOKEN_TYPE,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decodifica y valida un JWT.

    Args:
        token: Cadena JWT a decodificar.

    Returns:
        Payload decodificado como diccionario.

    Raises:
        JWTError: Si el token es invalido, expirado o la firma no coincide.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as exc:
        logger.warning("Token JWT invalido", extra={"error": str(exc)})
        raise
