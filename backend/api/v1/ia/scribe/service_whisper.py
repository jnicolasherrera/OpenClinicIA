"""Servicio de transcripción de audio con Whisper (sync y async)."""

import asyncio
import os
from typing import Optional

import httpx

from core.config import settings
from core.logging import get_logger

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


class WhisperService:
    """Servicio de transcripción de audio médico usando OpenAI Whisper.

    Soporta modo async para uso desde endpoints FastAPI y modo sync para Celery.
    Cuando OPENAI_API_KEY no está configurada opera en modo fallback con
    transcripción simulada, permitiendo desarrollo sin credenciales.
    """

    def __init__(self) -> None:
        """Inicializa el cliente OpenAI y detecta si hay API key válida."""
        self._modo_fallback: bool = not self._api_key_valida()

        if self._modo_fallback:
            logger.warning(
                "WhisperService iniciado en modo fallback — OPENAI_API_KEY no configurada"
            )
        else:
            import openai

            self._client: Optional[object] = openai.OpenAI(
                api_key=settings.OPENAI_API_KEY
            )

    # ------------------------------------------------------------------
    # Métodos públicos async
    # ------------------------------------------------------------------

    async def transcribir_desde_url(self, audio_url: str) -> str:
        """Descarga el audio desde una URL y lo transcribe con Whisper.

        Args:
            audio_url: URL pública o firmada del archivo de audio.

        Returns:
            Texto transcripto. Retorna transcripción simulada en modo fallback.
        """
        async with httpx.AsyncClient(timeout=60.0) as http:
            response = await http.get(audio_url)
            response.raise_for_status()
            audio_bytes = response.content

        filename = audio_url.split("?")[0].split("/")[-1] or "audio.mp3"
        return await self.transcribir_desde_bytes(audio_bytes, filename)

    async def transcribir_desde_bytes(
        self, audio_bytes: bytes, filename: str
    ) -> str:
        """Transcribe audio recibido como bytes (útil para upload directo).

        Args:
            audio_bytes: Contenido binario del archivo de audio.
            filename: Nombre del archivo, usado para detectar el MIME type.

        Returns:
            Texto transcripto. Retorna transcripción simulada en modo fallback.
        """
        mime_type = self._get_mime_type(filename)
        loop = asyncio.get_event_loop()
        result: str = await loop.run_in_executor(
            None,
            lambda: self._llamar_whisper_sync(audio_bytes, filename, mime_type),
        )
        return result

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def _llamar_whisper_sync(
        self, audio_bytes: bytes, filename: str, mime_type: str
    ) -> str:
        """Llama a la API de OpenAI Whisper de forma síncrona (para thread pool).

        Args:
            audio_bytes: Bytes del archivo de audio.
            filename: Nombre del archivo de audio.
            mime_type: MIME type del audio (ej. audio/mpeg).

        Returns:
            Texto transcripto o transcripción simulada si no hay API key.
        """
        if self._modo_fallback:
            logger.warning("Whisper en modo fallback — retornando transcripción simulada")
            return _TRANSCRIPCION_SIMULADA

        import openai as _openai_module

        assert self._client is not None  # validado en __init__
        client: _openai_module.OpenAI = self._client  # type: ignore[assignment]

        transcripcion = client.audio.transcriptions.create(
            model=settings.WHISPER_MODEL,
            file=(filename, audio_bytes, mime_type),
            language="es",
            prompt="Consulta médica en español. Términos médicos.",
        )

        result: str = transcripcion.text
        logger.info(
            "Transcripción Whisper completada",
            extra={"chars": len(result), "filename": filename},
        )
        return result

    def _get_mime_type(self, filename: str) -> str:
        """Detecta el MIME type por extensión de archivo.

        Args:
            filename: Nombre del archivo de audio.

        Returns:
            MIME type correspondiente. Default: audio/mpeg.
        """
        ext = os.path.splitext(filename)[1].lower()
        return _MIME_TYPES.get(ext, "audio/mpeg")

    @staticmethod
    def _api_key_valida() -> bool:
        """Verifica si OPENAI_API_KEY está configurada y no es un placeholder.

        Returns:
            True si la key parece válida para uso real.
        """
        key = settings.OPENAI_API_KEY
        return bool(key and key not in ("", "sk-", "your_openai_api_key_here"))
