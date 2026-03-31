"""Endpoints del módulo de scribe (documentación clínica con IA)."""

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import require_role
from api.v1.ia.scribe.schemas import ScribeRequest, SOAPResponse, TranscripcionTaskResponse
from api.v1.ia.scribe.service_generacion_soap import SOAPGeneratorService
from core.logging import get_logger
from models.usuario import Usuario

logger = get_logger(__name__)
router = APIRouter(prefix="/ia/scribe", tags=["ia-scribe"])


@router.post("/generar-soap", response_model=SOAPResponse, status_code=status.HTTP_200_OK)
async def generar_soap(
    body: ScribeRequest,
    _: Usuario = Depends(require_role("medico", "admin")),
) -> SOAPResponse:
    """Genera una nota SOAP a partir de transcripción o audio de consulta.

    Si se provee ``audio_url`` sin ``transcripcion_texto``, usa un texto placeholder
    hasta que la tarea de transcripción esté disponible.

    Args:
        body: Solicitud con transcripción o URL de audio.

    Returns:
        SOAPResponse con la nota clínica estructurada.

    Raises:
        HTTPException 503: Si el servicio de generación SOAP falla.
    """
    transcripcion = body.transcripcion_texto
    if not transcripcion:
        # Si solo se provee audio_url, usamos un mensaje indicativo
        # En flujo real, primero se encola la transcripción
        transcripcion = f"[Audio pendiente de transcripción: {body.audio_url}]"

    service = SOAPGeneratorService()
    try:
        result = await service.generar_soap(
            transcripcion=transcripcion,
            contexto=body.contexto_paciente or "",
        )
    except ValueError as exc:
        logger.error("Error generando SOAP", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de generación SOAP no pudo procesar la solicitud",
        ) from exc
    except Exception as exc:
        logger.error("Error inesperado en scribe", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error interno del servicio de scribe",
        ) from exc
    return result


@router.post(
    "/transcribir",
    response_model=TranscripcionTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def transcribir_audio(
    body: ScribeRequest,
    _: Usuario = Depends(require_role("medico", "admin")),
) -> TranscripcionTaskResponse:
    """Encola una tarea de transcripción de audio de forma asíncrona.

    Args:
        body: Solicitud con URL del audio y ID de episodio opcional en contexto.

    Returns:
        TranscripcionTaskResponse con el ID de la tarea encolada.

    Raises:
        HTTPException 400: Si no se provee audio_url.
        HTTPException 503: Si no se puede encolar la tarea.
    """
    if not body.audio_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere 'audio_url' para transcripción",
        )

    try:
        from api.v1.ia.scribe.worker_transcripcion import transcribir_audio as task

        task_result = task.delay(
            audio_url=body.audio_url,
            episodio_id=body.contexto_paciente or "unknown",
        )
        logger.info("Tarea de transcripción encolada", extra={"task_id": task_result.id})
        return TranscripcionTaskResponse(
            task_id=task_result.id,
            status="queued",
            message="Transcripción encolada correctamente",
        )
    except Exception as exc:
        logger.error("Error encolando transcripción", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo encolar la tarea de transcripción",
        ) from exc
