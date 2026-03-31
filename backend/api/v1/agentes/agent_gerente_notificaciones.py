"""Agente Gerente de Notificaciones — envía mensajes vía Telegram."""

from typing import Any

import httpx

from core.config import settings
from core.logging import get_logger
from api.v1.agentes.schemas import RespuestaAgente, TareaAgente

logger = get_logger(__name__)


class GerenteNotificaciones:
    """Gerente especializado en envío de notificaciones vía Telegram."""

    def __init__(self) -> None:
        """Inicializa el gerente con el token de bot de Telegram desde settings."""
        self._bot_token = settings.TELEGRAM_BOT_TOKEN
        self._api_base = f"https://api.telegram.org/bot{self._bot_token}"

    async def enviar_mensaje(self, chat_id: int, texto: str) -> bool:
        """Envía un mensaje de texto a un chat de Telegram.

        Args:
            chat_id: ID numérico del chat o usuario destino.
            texto: Texto del mensaje (soporta Markdown).

        Returns:
            True si el envío fue exitoso (HTTP 200), False en caso de error.
        """
        if not self._bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN no configurado — envío omitido")
            return False

        payload = {
            "chat_id": chat_id,
            "text": texto,
            "parse_mode": "Markdown",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self._api_base}/sendMessage",
                    json=payload,
                )
            if response.status_code == 200:
                logger.info(
                    "Mensaje de Telegram enviado exitosamente",
                    extra={"chat_token": f"[CHAT_{str(abs(chat_id))[:6]}]"},
                )
                return True
            else:
                logger.warning(
                    "Telegram devolvió error al enviar mensaje",
                    extra={"status_code": response.status_code},
                )
                return False
        except httpx.HTTPError as exc:
            logger.error(
                "Error HTTP enviando mensaje de Telegram",
                extra={"error": str(exc)},
            )
            return False

    async def ejecutar(self, tarea: TareaAgente) -> RespuestaAgente:
        """Ejecuta la tarea de notificación enviando el recordatorio solicitado.

        Args:
            tarea: Tarea con parámetros que deben incluir 'chat_id' y 'mensaje'.

        Returns:
            RespuestaAgente confirmando el envío o indicando el error.
        """
        parametros: dict[str, Any] = tarea.parametros
        chat_id_destino = parametros.get("chat_id", tarea.chat_id)
        mensaje_texto = parametros.get("mensaje", parametros.get("texto", "Recordatorio de OpenClinicIA"))

        exito = await self.enviar_mensaje(int(chat_id_destino), str(mensaje_texto))

        if exito:
            return RespuestaAgente(
                exito=True,
                mensaje="✅ Recordatorio enviado correctamente.",
                datos={"chat_id": chat_id_destino},
            )
        return RespuestaAgente(
            exito=False,
            mensaje="No pude enviar el recordatorio. Verificá la configuración del bot de Telegram.",
            error="envio_fallido",
        )
