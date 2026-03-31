"""Tareas Celery para transcripción de audio médico."""

import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="scribe.transcribir_audio",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def transcribir_audio(self, audio_url: str, episodio_id: str) -> str:  # type: ignore[override]
    """Transcribe un archivo de audio de consulta médica a texto.

    En MVP retorna un texto de ejemplo para integración.
    En producción llamaría a OpenAI Whisper u otro servicio ASR.

    Args:
        audio_url: URL accesible del archivo de audio (.mp3, .wav, .m4a).
        episodio_id: UUID del episodio al que pertenece esta transcripción.

    Returns:
        Texto transcripto del audio.

    Raises:
        Exception: Si ocurre un error recuperable, se reintenta hasta max_retries.
    """
    logger.info(
        "Iniciando transcripción de audio",
        extra={"episodio_id": episodio_id, "task_id": self.request.id},
    )

    try:
        # MVP: simulación de transcripción
        # En producción se integraría con:
        # import openai
        # client = openai.OpenAI()
        # with httpx.Client() as http:
        #     audio_bytes = http.get(audio_url).content
        # transcripcion = client.audio.transcriptions.create(
        #     model="whisper-1",
        #     file=("audio.mp3", audio_bytes, "audio/mpeg"),
        # )
        # return transcripcion.text

        transcripcion_simulada = (
            "Paciente refiere dolor en región lumbar de 3 días de evolución. "
            "Se irradia a miembro inferior derecho. "
            "Niega fiebre. Antecedente de hernia discal L4-L5. "
            "Al examen: contractura paravertebral. Lasègue positivo derecho. "
            "Impresión diagnóstica: lumbociatalgia derecha. "
            "Se indica AINE, relajante muscular y reposo relativo. "
            "Se solicita RMN de columna lumbosacra. Control en 7 días."
        )

        logger.info(
            "Transcripción completada",
            extra={"episodio_id": episodio_id, "task_id": self.request.id},
        )
        return transcripcion_simulada

    except Exception as exc:
        logger.error(
            "Error en transcripción",
            extra={
                "episodio_id": episodio_id,
                "task_id": self.request.id,
                "error": str(exc),
            },
        )
        raise self.retry(exc=exc)
