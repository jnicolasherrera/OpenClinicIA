"""Endpoints del módulo de triaje de urgencia."""

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import require_role
from api.v1.ia.triaje.agent_triaje_urgencia import TriajeAgent
from api.v1.ia.triaje.schemas import TriajeRequest, TriajeResponse
from core.logging import get_logger
from models.usuario import Usuario

logger = get_logger(__name__)
router = APIRouter(prefix="/ia/triaje", tags=["ia-triaje"])


@router.post("", response_model=TriajeResponse, status_code=status.HTTP_200_OK)
async def evaluar_triaje(
    body: TriajeRequest,
    _: Usuario = Depends(require_role("medico", "recepcion")),
) -> TriajeResponse:
    """Evalúa el nivel de urgencia ESI de un paciente usando IA.

    Solo accesible para médicos y personal de recepción.

    Args:
        body: Síntomas y antecedentes del paciente.

    Returns:
        TriajeResponse con nivel de urgencia y recomendaciones.

    Raises:
        HTTPException 503: Si la evaluación de IA falla.
    """
    agent = TriajeAgent()
    try:
        result = await agent.evaluar_urgencia(body)
    except ValueError as exc:
        logger.error("Error en evaluación de triaje", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de triaje no pudo procesar la solicitud",
        ) from exc
    except Exception as exc:
        logger.error("Error inesperado en triaje", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error interno del servicio de triaje",
        ) from exc
    return result
