"""Tareas Celery para transcripción de audio médico con Whisper."""

import asyncio
import os

import httpx

from core.config import settings
from core.logging import get_logger
from workers.celery_app import celery_app

logger = get_logger(__name__)

_TRANSCRIPCION_SIMULADA = (
    "Paciente refiere dolor en región lumbar de 3 días de evolución. "
    "Se irradia a miembro inferior derecho. "
    "Niega fiebre. Antecedente de hernia discal L4-L5. "
    "Al examen: contractura paravertebral. Lasègue positivo derecho. "
    "Impresión diagnóstica: lumbociatalgia derecha. "
    "Se indica AINE, relajante muscular y reposo relativo. "
    "Se solicita RMN de columna lumbosacra. Control en 7 días."
)

_MIME_TYPES: dict[str, str] = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".webm": "audio/webm",
    ".flac": "audio/flac",
}


def _get_mime_type(filename: str) -> str:
    """Detecta el MIME type de audio por extensión de archivo.

    Args:
        filename: Nombre del archivo de audio.

    Returns:
        MIME type correspondiente. Default: audio/mpeg.
    """
    ext = os.path.splitext(filename)[1].lower()
    return _MIME_TYPES.get(ext, "audio/mpeg")


def _es_api_key_valida() -> bool:
    """Verifica si OPENAI_API_KEY está configurada y no es un placeholder.

    Returns:
        True si la key parece válida para uso real.
    """
    key = settings.OPENAI_API_KEY
    return bool(key and key not in ("", "sk-", "your_openai_api_key_here"))


def _llamar_whisper_sync(
    audio_bytes: bytes, filename: str, mime_type: str, episodio_id: str
) -> str:
    """Llama a la API de OpenAI Whisper de forma síncrona.

    Args:
        audio_bytes: Bytes del archivo de audio.
        filename: Nombre del archivo (para detectar formato).
        mime_type: MIME type del audio.
        episodio_id: ID del episodio (para logs sin PII).

    Returns:
        Texto transcripto por Whisper o transcripción simulada en fallback.
    """
    if not _es_api_key_valida():
        logger.warning(
            "OPENAI_API_KEY no configurada — usando transcripción simulada",
            extra={"episodio_id": f"[EPISODIO_{episodio_id}]"},
        )
        return _TRANSCRIPCION_SIMULADA

    import openai

    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    transcripcion = client.audio.transcriptions.create(
        model=settings.WHISPER_MODEL,
        file=(filename, audio_bytes, mime_type),
        language="es",
        prompt="Consulta médica en español. Términos médicos.",
    )
    return transcripcion.text


@celery_app.task(
    name="scribe.transcribir_audio",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def transcribir_audio(self, audio_url: str, episodio_id: str) -> str:  # type: ignore[override]
    """Descarga audio desde una URL y lo transcribe con OpenAI Whisper.

    Args:
        audio_url: URL accesible del archivo de audio (.mp3, .wav, .m4a, etc.).
        episodio_id: UUID del episodio al que pertenece esta transcripción.

    Returns:
        Texto transcripto del audio.

    Raises:
        Exception: Si ocurre un error recuperable, se reintenta hasta max_retries.
    """
    logger.info(
        "Iniciando transcripción de audio",
        extra={
            "episodio_id": f"[EPISODIO_{episodio_id}]",
            "task_id": self.request.id,
        },
    )

    try:
        filename = audio_url.split("?")[0].split("/")[-1] or "audio.mp3"
        mime_type = _get_mime_type(filename)

        with httpx.Client(timeout=60.0) as http:
            response = http.get(audio_url)
            response.raise_for_status()
            audio_bytes = response.content

        result = _llamar_whisper_sync(audio_bytes, filename, mime_type, episodio_id)

        logger.info(
            "Transcripción completada",
            extra={
                "episodio_id": f"[EPISODIO_{episodio_id}]",
                "chars": len(result),
            },
        )
        return result

    except Exception as exc:
        logger.error(
            "Error en transcripción",
            extra={
                "episodio_id": f"[EPISODIO_{episodio_id}]",
                "task_id": self.request.id,
                "error": str(exc),
            },
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name="scribe.transcribir_audio_local",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def transcribir_audio_local(self, filepath: str, episodio_id: str) -> str:  # type: ignore[override]
    """Lee un archivo de audio local (ej. desde MinIO) y lo transcribe con Whisper.

    Args:
        filepath: Ruta absoluta al archivo de audio en el sistema de archivos local.
        episodio_id: UUID del episodio al que pertenece esta transcripción.

    Returns:
        Texto transcripto del audio.

    Raises:
        Exception: Si ocurre un error recuperable, se reintenta hasta max_retries.
    """
    logger.info(
        "Iniciando transcripción de audio local",
        extra={
            "episodio_id": f"[EPISODIO_{episodio_id}]",
            "task_id": self.request.id,
        },
    )

    try:
        filename = os.path.basename(filepath)
        mime_type = _get_mime_type(filename)

        with open(filepath, "rb") as f:
            audio_bytes = f.read()

        result = _llamar_whisper_sync(audio_bytes, filename, mime_type, episodio_id)

        logger.info(
            "Transcripción local completada",
            extra={
                "episodio_id": f"[EPISODIO_{episodio_id}]",
                "chars": len(result),
            },
        )
        return result

    except Exception as exc:
        logger.error(
            "Error en transcripción local",
            extra={
                "episodio_id": f"[EPISODIO_{episodio_id}]",
                "task_id": self.request.id,
                "error": str(exc),
            },
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name="scribe.transcribir_y_generar_soap",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def transcribir_y_generar_soap(  # type: ignore[override]
    self, audio_url: str, episodio_id: str, contexto: str
) -> dict:
    """Pipeline completo: descarga audio, transcribe con Whisper y genera nota SOAP.

    Args:
        audio_url: URL accesible del archivo de audio.
        episodio_id: UUID del episodio clínico.
        contexto: Contexto del paciente para la generación SOAP.

    Returns:
        Diccionario con claves ``transcripcion``, ``soap`` y ``episodio_id``.

    Raises:
        Exception: Si ocurre un error recuperable, se reintenta hasta max_retries.
    """
    logger.info(
        "Iniciando pipeline transcripción + SOAP",
        extra={
            "episodio_id": f"[EPISODIO_{episodio_id}]",
            "task_id": self.request.id,
        },
    )

    try:
        # Paso 1: transcripción síncrona dentro del worker
        transcripcion_task = transcribir_audio.delay(audio_url, episodio_id)
        transcripcion_text: str = transcripcion_task.get(timeout=300)

        # Paso 2: generación SOAP (sync via asyncio.run dentro del worker)
        from api.v1.ia.scribe.service_generacion_soap import SOAPGeneratorService

        service = SOAPGeneratorService()
        soap_response = asyncio.run(
            service.generar_soap(transcripcion=transcripcion_text, contexto=contexto)
        )

        result: dict = {
            "transcripcion": transcripcion_text,
            "soap": soap_response.model_dump(),
            "episodio_id": episodio_id,
        }

        logger.info(
            "Pipeline transcripción + SOAP completado",
            extra={"episodio_id": f"[EPISODIO_{episodio_id}]"},
        )
        return result

    except Exception as exc:
        logger.error(
            "Error en pipeline transcripción + SOAP",
            extra={
                "episodio_id": f"[EPISODIO_{episodio_id}]",
                "task_id": self.request.id,
                "error": str(exc),
            },
        )
        raise self.retry(exc=exc)
