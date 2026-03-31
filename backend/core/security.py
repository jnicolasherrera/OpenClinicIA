"""Utilidades de seguridad: JWT, hashing de contraseñas."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_REFRESH_TOKEN_TYPE = "refresh"
_ACCESS_TOKEN_TYPE = "access"


def get_password_hash(password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano.

    Args:
        password: Contraseña en texto plano.

    Returns:
        Hash bcrypt de la contraseña.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica que una contraseña en texto plano coincida con su hash.

    Args:
        plain_password: Contraseña en texto plano provista por el usuario.
        hashed_password: Hash almacenado en la base de datos.

    Returns:
        True si la contraseña es válida, False en caso contrario.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Genera un JWT de acceso firmado con los datos proporcionados.

    Args:
        data: Payload a incluir en el token.
        expires_delta: Tiempo de expiración personalizado. Si es None,
            usa ACCESS_TOKEN_EXPIRE_MINUTES de la configuración.

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
        subject: Identificador único del usuario (normalmente su UUID como str).

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
        JWTError: Si el token es inválido, expirado o la firma no coincide.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as exc:
        logger.warning("Token JWT inválido", extra={"error": str(exc)})
        raise
