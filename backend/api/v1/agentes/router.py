"""Router de agentes — webhooks para n8n y health check del sistema."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user
from api.v1.agentes.agent_gerente_agenda import GerenteAgenda
from api.v1.agentes.agent_gerente_notificaciones import GerenteNotificaciones
from api.v1.agentes.agent_jefe import AgenteJefe
from api.v1.agentes.schemas import MensajeTelegram, RespuestaAgente, TipoAgente
from core.config import settings
from core.database import get_db
from core.logging import get_logger
from models.usuario import Usuario

logger = get_logger(__name__)
router = APIRouter(prefix="/agentes", tags=["agentes"])

# UUID de tenant por defecto para operaciones sin contexto de usuario autenticado
import uuid as _uuid

_DEFAULT_TENANT_ID = _uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post("/webhook/telegram", response_model=RespuestaAgente, status_code=status.HTTP_200_OK)
async def webhook_telegram(
    payload: MensajeTelegram,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_n8n_secret: str = Header(default=""),
) -> RespuestaAgente:
    """Recibe mensajes de Telegram via n8n y los procesa con el árbol de agentes.

    No requiere autenticación JWT — usa un secret header compartido con n8n.
    El Agente Jefe clasifica la intención y delega al gerente correspondiente.

    Args:
        payload: Datos del mensaje de Telegram (chat_id, texto, usuario).
        db: Sesión de base de datos.
        x_n8n_secret: Header de seguridad compartido entre n8n y este backend.

    Returns:
        RespuestaAgente con el mensaje a enviar de vuelta al usuario en Telegram.

    Raises:
        HTTPException 403: Si el secret header no coincide con el configurado.
    """
    # Verificar secret de n8n
    if settings.N8N_WEBHOOK_SECRET:
        if x_n8n_secret != settings.N8N_WEBHOOK_SECRET:
            logger.warning("Intento de acceso a webhook con secret inválido")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Secret de webhook inválido",
            )
    else:
        logger.warning("N8N_WEBHOOK_SECRET no configurado — webhook sin autenticación")

    # Clasificar intención con el Agente Jefe
    jefe = AgenteJefe()
    decision = await jefe.clasificar_intencion(payload)

    # Si hay respuesta inmediata (saludo, pregunta simple), retornar directamente
    if decision.respuesta_inmediata:
        return RespuestaAgente(
            exito=True,
            mensaje=decision.respuesta_inmediata,
        )

    # Delegar al gerente correspondiente
    if decision.tipo_agente == TipoAgente.AGENDA:
        gerente = GerenteAgenda(db=db, tenant_id=_DEFAULT_TENANT_ID)
    elif decision.tipo_agente == TipoAgente.NOTIFICACIONES:
        gerente = GerenteNotificaciones()  # type: ignore[assignment]
    else:
        # Para tipos no implementados, informar al usuario
        logger.info(
            "Tipo de agente no implementado",
            extra={"tipo_agente": decision.tipo_agente, "accion": decision.accion},
        )
        return RespuestaAgente(
            exito=False,
            mensaje=f"La funcionalidad '{decision.tipo_agente}' está en desarrollo. Pronto estará disponible.",
            error="agente_no_implementado",
        )

    from api.v1.agentes.schemas import TareaAgente

    tarea = TareaAgente(
        tipo_agente=decision.tipo_agente,
        accion=decision.accion,
        parametros=decision.parametros,
        chat_id=payload.chat_id,
        contexto=payload.texto,
    )

    return await gerente.ejecutar(tarea)


@router.get("/estado", status_code=status.HTTP_200_OK)
async def estado_agentes(
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
) -> dict:
    """Health check del sistema de agentes — requiere autenticación JWT.

    Args:
        current_user: Usuario autenticado (inyectado por dependencia).

    Returns:
        Diccionario con estado de los agentes y configuración de n8n.
    """
    return {
        "agentes_activos": ["jefe", "agenda", "notificaciones"],
        "n8n_configurado": bool(settings.N8N_WEBHOOK_SECRET),
        "telegram_configurado": bool(settings.TELEGRAM_BOT_TOKEN),
        "anthropic_configurado": bool(settings.ANTHROPIC_API_KEY),
    }
