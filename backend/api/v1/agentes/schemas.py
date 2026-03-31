"""Schemas Pydantic para el módulo de agentes n8n + Telegram."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class TipoAgente(str, Enum):
    """Tipos de agentes disponibles en el árbol."""

    JEFE = "jefe"
    AGENDA = "agenda"
    HISTORIA = "historia"
    NOTIFICACIONES = "notificaciones"
    FACTURACION = "facturacion"


class MensajeTelegram(BaseModel):
    """Mensaje entrante de Telegram via n8n."""

    chat_id: int
    message_id: int
    texto: str
    usuario_telegram: str
    fecha: Optional[str] = None


class TareaAgente(BaseModel):
    """Tarea delegada por el Agente Jefe a un Gerente."""

    tipo_agente: TipoAgente
    accion: str  # "crear_turno", "buscar_paciente", "generar_soap", etc.
    parametros: dict[str, Any]
    chat_id: int
    contexto: Optional[str] = None


class RespuestaAgente(BaseModel):
    """Respuesta de un agente al completar una tarea."""

    exito: bool
    mensaje: str  # Texto para enviar al usuario en Telegram
    datos: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class DecisionJefe(BaseModel):
    """Decisión del Agente Jefe sobre cómo rutear la solicitud."""

    tipo_agente: TipoAgente
    accion: str
    parametros: dict[str, Any]
    razonamiento: str
    respuesta_inmediata: Optional[str] = None  # Si puede responder sin delegar
