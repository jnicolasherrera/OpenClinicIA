"""Agente de IA para clasificación de urgencia ESI (Emergency Severity Index)."""

import json
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import anthropic

from api.v1.ia.triaje.schemas import TriajeRequest, TriajeResponse
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = """Eres un sistema experto de triaje médico que clasifica la urgencia de pacientes
usando la escala ESI (Emergency Severity Index) de 1 a 5, donde:

- ESI 1: Reanimación inmediata — riesgo de vida inminente (tiempo: 0 min)
- ESI 2: Emergencia — condición de riesgo alto, mucho dolor (tiempo: ≤10 min)
- ESI 3: Urgente — múltiples recursos necesarios pero estable (tiempo: ≤30 min)
- ESI 4: Semi-urgente — un recurso necesario, estable (tiempo: ≤60 min)
- ESI 5: No urgente — sin recursos o mínimos necesarios (tiempo: ≤120 min)

Debes analizar los síntomas presentados y responder ÚNICAMENTE con un objeto JSON válido con esta estructura:
{
  "nivel_urgencia": <número 1-5>,
  "descripcion": "<descripción breve del nivel asignado>",
  "recomendacion": "<acción recomendada concreta>",
  "tiempo_atencion_sugerido_minutos": <número entero>,
  "razonamiento": "<justificación clínica detallada>"
}

No incluyas texto antes ni después del JSON. No uses markdown. Solo JSON puro."""


class TriajeAgent:
    """Agente que evalúa la urgencia de un paciente usando la API de Anthropic."""

    def __init__(self) -> None:
        """Inicializa el cliente de Anthropic."""
        import anthropic as _anthropic

        self._client = _anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def evaluar_urgencia(self, request: TriajeRequest) -> TriajeResponse:
        """Evalúa el nivel de urgencia ESI dados los síntomas del paciente.

        Usa el modelo claude-haiku para clasificación rápida. El ID de triaje
        en los logs nunca contiene PII del paciente.

        Args:
            request: Datos clínicos de entrada.

        Returns:
            TriajeResponse con el nivel de urgencia y recomendaciones.

        Raises:
            ValueError: Si la respuesta del modelo no puede parsearse como JSON válido.
            anthropic.APIError: Si la API de Anthropic devuelve un error.
        """
        triaje_id = str(uuid.uuid4())[:8]
        logger.info(
            "Iniciando evaluación de triaje",
            extra={"triaje_token": f"[TRIAJE_{triaje_id}]"},
        )

        user_message = self._build_user_message(request)

        # Llamada síncrona a la API (el cliente de Anthropic SDK es síncrono)
        import asyncio

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.messages.create(
                model=_MODEL,
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            ),
        )

        raw_text = response.content[0].text.strip()
        logger.info(
            "Respuesta de triaje recibida",
            extra={"triaje_token": f"[TRIAJE_{triaje_id}]", "tokens_used": response.usage.output_tokens},
        )

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.error(
                "Error parseando respuesta de triaje",
                extra={"triaje_token": f"[TRIAJE_{triaje_id}]", "error": str(exc)},
            )
            raise ValueError(
                f"La IA retornó una respuesta no parseable: {raw_text[:200]}"
            ) from exc

        return TriajeResponse(**data)

    def _build_user_message(self, request: TriajeRequest) -> str:
        """Construye el mensaje de usuario para el modelo.

        Args:
            request: Datos del triaje.

        Returns:
            Mensaje formateado en español.
        """
        parts = [
            f"SÍNTOMAS: {request.sintomas}",
            f"DURACIÓN: {request.duracion_sintomas}",
        ]
        if request.antecedentes:
            parts.append(f"ANTECEDENTES: {request.antecedentes}")
        return "\n".join(parts)
