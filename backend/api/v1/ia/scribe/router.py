"""Endpoints del módulo de scribe (documentación clínica con IA)."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from api.deps import require_role
from api.v1.ia.scribe.schemas import (
    ScribeRequest,
    SOAPResponse,
    TranscripcionResponse,
    TranscripcionTaskResponse,
)
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
    response_model=TranscripcionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def transcribir_audio(
    audio_url: Optional[str] = Form(default=None),
    episodio_id: Optional[str] = Form(default=None),
    contexto: Optional[str] = Form(default=None),
    audio_file: Optional[UploadFile] = File(default=None),
    _: Usuario = Depends(require_role("medico", "admin")),
) -> TranscripcionResponse:
    """Transcribe audio de una consulta médica.

    Acepta tanto ``audio_url`` (lanza tarea Celery) como ``audio_file``
    (upload directo, transcripción inmediata con WhisperService).

    Args:
        audio_url: URL del archivo de audio a transcribir (lanzamiento async).
        episodio_id: ID del episodio clínico asociado.
        contexto: Contexto del paciente para el pipeline SOAP.
        audio_file: Archivo de audio subido directamente (proceso sync).

    Returns:
        TranscripcionResponse con task_id (si async) o transcripción directa.

    Raises:
        HTTPException 400: Si no se provee ni audio_url ni audio_file.
        HTTPException 503: Si no se puede procesar la solicitud.
    """
    if audio_file is not None:
        # Upload directo → transcripción inmediata con WhisperService
        try:
            from api.v1.ia.scribe.service_whisper import WhisperService

            audio_bytes = await audio_file.read()
            filename = audio_file.filename or "audio.mp3"
            service = WhisperService()
            transcripcion_text = await service.transcribir_desde_bytes(
                audio_bytes, filename
            )
            logger.info(
                "Transcripción directa completada",
                extra={
                    "episodio_id": f"[EPISODIO_{episodio_id or 'unknown'}]",
                    "chars": len(transcripcion_text),
                },
            )
            return TranscripcionResponse(
                transcripcion=transcripcion_text,
                estado="completado",
                mensaje="Transcripción completada",
            )
        except Exception as exc:
            logger.error("Error en transcripción directa", extra={"error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo transcribir el archivo de audio",
            ) from exc

    if audio_url:
        # URL → pipeline async con Celery
        try:
            from api.v1.ia.scribe.worker_transcripcion import (
                transcribir_y_generar_soap as task,
            )

            task_result = task.delay(
                audio_url,
                episodio_id or "unknown",
                contexto or "",
            )
            logger.info(
                "Tarea de pipeline scribe encolada",
                extra={
                    "task_id": task_result.id,
                    "episodio_id": f"[EPISODIO_{episodio_id or 'unknown'}]",
                },
            )
            return TranscripcionResponse(
                task_id=task_result.id,
                estado="procesando",
                mensaje="Pipeline de transcripción + SOAP encolado",
            )
        except Exception as exc:
            logger.error("Error encolando pipeline scribe", extra={"error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo encolar la tarea de transcripción",
            ) from exc

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Se requiere 'audio_url' o 'audio_file' para transcripción",
    )


@router.post(
    "/encolar-transcripcion",
    response_model=TranscripcionTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def encolar_transcripcion(
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


@router.get("/estado/{task_id}")
async def estado_transcripcion(
    task_id: str,
    _: Usuario = Depends(require_role("medico", "admin")),
) -> dict:
    """Consulta el estado de una tarea Celery de transcripción o pipeline.

    Args:
        task_id: ID de la tarea Celery retornada al encolarse.

    Returns:
        Diccionario con task_id, estado (PENDING/STARTED/SUCCESS/FAILURE)
        y resultado si la tarea ya finalizó.
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "estado": result.state,  # PENDING, STARTED, SUCCESS, FAILURE
        "resultado": result.result if result.ready() else None,
    }
