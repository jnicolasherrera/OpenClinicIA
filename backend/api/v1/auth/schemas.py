"""Schemas Pydantic para el módulo de autenticación."""

import uuid

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Credenciales de inicio de sesión."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Respuesta con tokens JWT de acceso y refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Solicitud de renovación de token."""

    refresh_token: str


class UserResponse(BaseModel):
    """Datos públicos del usuario autenticado."""

    id: uuid.UUID
    email: str
    nombre: str
    apellido: str
    rol: str

    model_config = {"from_attributes": True}
