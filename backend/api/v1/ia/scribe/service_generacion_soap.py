"""Servicio de generación de notas SOAP usando Claude Sonnet."""

import json
import uuid

from api.v1.ia.scribe.schemas import SOAPResponse
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

_MODEL = "claude-sonnet-4-6"

_SYSTEM_PROMPT = """Eres un asistente médico especializado en documentación clínica.
Tu tarea es transformar la transcripción de una consulta médica en una nota clínica
estructurada en formato SOAP (Subjetivo, Objetivo, Assessment/Evaluación, Plan).

Reglas:
- Usa terminología médica apropiada pero comprensible.
- No inventes información que no esté en la transcripción.
- Sé conciso pero completo.
- El resumen clínico debe ser de 2-3 oraciones.
- Responde ÚNICAMENTE con un JSON válido con esta estructura:

{
  "subjetivo": "<lo que el paciente refiere: síntomas, motivo de consulta, historia>",
  "objetivo": "<hallazgos del examen físico y signos vitales si se mencionan>",
  "assessment": "<evaluación diagnóstica del médico>",
  "plan": "<plan terapéutico: medicamentos, estudios, indicaciones, seguimiento>",
  "resumen_clinico": "<resumen ejecutivo de la consulta>"
}

No uses markdown. No incluyas texto fuera del JSON."""


class SOAPGeneratorService:
    """Genera notas SOAP a partir de transcripciones de consultas médicas."""

    def __init__(self) -> None:
        """Inicializa el cliente de Anthropic."""
        import anthropic

        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def generar_soap(
        self, transcripcion: str, contexto: str = ""
    ) -> SOAPResponse:
        """Genera una nota SOAP a partir de la transcripción de una consulta.

        Args:
            transcripcion: Texto transcripto de la consulta médica.
            contexto: Contexto adicional del paciente (antecedentes, obra social, etc.).

        Returns:
            SOAPResponse con los campos de la nota SOAP.

        Raises:
            ValueError: Si la respuesta del modelo no es JSON válido.
            anthropic.APIError: Si la API de Anthropic falla.
        """
        scribe_id = str(uuid.uuid4())[:8]
        logger.info(
            "Iniciando generación SOAP",
            extra={"scribe_token": f"[SCRIBE_{scribe_id}]"},
        )

        user_content = self._build_user_content(transcripcion, contexto)

        import asyncio

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.messages.create(
                model=_MODEL,
                max_tokens=2048,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            ),
        )

        raw_text = response.content[0].text.strip()
        logger.info(
            "SOAP generado",
            extra={
                "scribe_token": f"[SCRIBE_{scribe_id}]",
                "tokens_input": response.usage.input_tokens,
                "tokens_output": response.usage.output_tokens,
            },
        )

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.error(
                "Error parseando SOAP generado",
                extra={"scribe_token": f"[SCRIBE_{scribe_id}]", "error": str(exc)},
            )
            raise ValueError(
                f"La IA retornó una respuesta no parseable: {raw_text[:200]}"
            ) from exc

        return SOAPResponse(**data)

    def _build_user_content(self, transcripcion: str, contexto: str) -> str:
        """Construye el mensaje de usuario para el modelo.

        Args:
            transcripcion: Texto de la consulta médica.
            contexto: Contexto adicional del paciente.

        Returns:
            Mensaje formateado.
        """
        parts = ["TRANSCRIPCIÓN DE CONSULTA:", transcripcion]
        if contexto:
            parts = ["CONTEXTO DEL PACIENTE:", contexto, ""] + parts
        return "\n".join(parts)
