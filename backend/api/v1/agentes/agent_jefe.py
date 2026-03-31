"""Agente Jefe — Claude clasifica intenciones y delega a gerentes."""

import asyncio
import json
import uuid

from core.config import settings
from core.logging import get_logger
from api.v1.agentes.schemas import DecisionJefe, MensajeTelegram, TipoAgente

logger = get_logger(__name__)

_MODEL = "claude-sonnet-4-6"

_SYSTEM_PROMPT = """Sos el Agente Jefe de OpenClinicIA, un asistente médico inteligente.
Recibís mensajes de médicos y recepcionistas y debés clasificar la intención.

Acciones disponibles:
- tipo_agente: "agenda", accion: "crear_turno" | "ver_turnos" | "cancelar_turno" | "sala_espera"
- tipo_agente: "historia", accion: "buscar_paciente" | "ver_historia" | "crear_episodio"
- tipo_agente: "facturacion", accion: "crear_comprobante" | "ver_comprobantes" | "resumen_dia"
- tipo_agente: "notificaciones", accion: "enviar_recordatorio"

Respondé SOLO con JSON válido: {"tipo_agente": "...", "accion": "...", "parametros": {}, "razonamiento": "...", "respuesta_inmediata": null}
Si el mensaje es un saludo o pregunta simple, usá "respuesta_inmediata" con el texto a responder."""


class AgenteJefe:
    """Agente principal que clasifica intenciones y delega a gerentes especializados."""

    def __init__(self) -> None:
        """Inicializa el cliente Anthropic con la API key de settings."""
        import anthropic as _anthropic

        self._client = _anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def clasificar_intencion(self, mensaje: MensajeTelegram) -> DecisionJefe:
        """Clasifica la intención del mensaje y devuelve una decisión de ruteo.

        Llama a Claude con temperatura 0 para obtener una decisión determinista
        sobre qué agente gerente debe manejar la solicitud.

        Args:
            mensaje: Mensaje entrante de Telegram con texto y metadata.

        Returns:
            DecisionJefe con el tipo de agente, acción, parámetros y razonamiento.
        """
        clasificacion_id = str(uuid.uuid4())[:8]
        logger.info(
            "Jefe clasificando intención",
            extra={"clasificacion_token": f"[JEFE_{clasificacion_id}]"},
        )

        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._client.messages.create(
                    model=_MODEL,
                    max_tokens=512,
                    temperature=0,
                    system=_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": mensaje.texto}],
                ),
            )
        except Exception as exc:
            logger.error(
                "Error llamando a la API de Anthropic",
                extra={"clasificacion_token": f"[JEFE_{clasificacion_id}]", "error": str(exc)},
            )
            return DecisionJefe(
                tipo_agente=TipoAgente.NOTIFICACIONES,
                accion="enviar_recordatorio",
                parametros={},
                razonamiento="Error de comunicación con la IA",
                respuesta_inmediata="Lo siento, tuve un problema procesando tu solicitud. Por favor intentá de nuevo.",
            )

        raw_text = response.content[0].text.strip()

        try:
            # Extraer JSON si viene envuelto en markdown
            if "```" in raw_text:
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]

            data = json.loads(raw_text)
            decision = DecisionJefe(**data)
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning(
                "Error parseando respuesta del Jefe",
                extra={
                    "clasificacion_token": f"[JEFE_{clasificacion_id}]",
                    "error": str(exc),
                },
            )
            return DecisionJefe(
                tipo_agente=TipoAgente.NOTIFICACIONES,
                accion="enviar_recordatorio",
                parametros={},
                razonamiento="No se pudo parsear la respuesta de la IA",
                respuesta_inmediata="No pude entender tu solicitud. ¿Podés reformularla? Por ejemplo: 'ver sala de espera', 'turnos de hoy', 'buscar paciente García'.",
            )

        logger.info(
            "Jefe clasificó intención",
            extra={"accion": decision.accion, "tipo_agente": decision.tipo_agente},
        )
        return decision
