"""Agente Gerente de Agenda — ejecuta acciones de turnos."""

from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logging import get_logger
from api.v1.agentes.schemas import RespuestaAgente, TareaAgente

logger = get_logger(__name__)

_API_BASE = "http://localhost:8000"


class GerenteAgenda:
    """Gerente especializado en operaciones de agenda y turnos."""

    def __init__(self, db: AsyncSession, tenant_id: UUID) -> None:
        """Inicializa el gerente con sesión de base de datos y tenant.

        Args:
            db: Sesión asíncrona de SQLAlchemy.
            tenant_id: UUID del tenant activo para filtrar datos.
        """
        self._db = db
        self._tenant_id = tenant_id

    def _get_headers(self) -> dict[str, str]:
        """Construye los headers HTTP para llamadas a la API interna.

        Returns:
            Diccionario de headers con Authorization si hay token configurado.
        """
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if settings.INTERNAL_API_TOKEN:
            headers["Authorization"] = f"Bearer {settings.INTERNAL_API_TOKEN}"
        return headers

    async def ejecutar(self, tarea: TareaAgente) -> RespuestaAgente:
        """Ejecuta la acción de agenda solicitada y retorna una respuesta formateada.

        Despacha la acción al método correspondiente según tarea.accion.

        Args:
            tarea: Tarea con acción y parámetros a ejecutar.

        Returns:
            RespuestaAgente con mensaje formateado para Telegram.
        """
        acciones: dict[str, Any] = {
            "sala_espera": self._sala_espera,
            "ver_turnos": self._ver_turnos,
            "crear_turno": self._crear_turno,
            "cancelar_turno": self._cancelar_turno,
        }

        handler = acciones.get(tarea.accion)
        if handler is None:
            logger.warning(
                "Acción de agenda desconocida",
                extra={"accion": tarea.accion},
            )
            return RespuestaAgente(
                exito=False,
                mensaje=f"No reconozco la acción '{tarea.accion}' para la agenda.",
                error="accion_desconocida",
            )

        try:
            return await handler(tarea.parametros)
        except httpx.HTTPError as exc:
            logger.error(
                "Error HTTP al llamar la API interna de agenda",
                extra={"accion": tarea.accion, "error": str(exc)},
            )
            return RespuestaAgente(
                exito=False,
                mensaje="Hubo un problema conectando con el sistema de turnos. Intentá de nuevo.",
                error="http_error",
            )

    async def _sala_espera(self, parametros: dict[str, Any]) -> RespuestaAgente:
        """Obtiene y formatea la sala de espera actual.

        Args:
            parametros: Parámetros adicionales (no requeridos para esta acción).

        Returns:
            RespuestaAgente con lista de pacientes en sala de espera.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{_API_BASE}/api/v1/agenda/sala-espera",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

        pacientes = data if isinstance(data, list) else data.get("turnos", [])

        if not pacientes:
            return RespuestaAgente(
                exito=True,
                mensaje="✅ La sala de espera está vacía por ahora.",
                datos={"cantidad": 0},
            )

        lineas = ["🏥 *Sala de Espera*\n"]
        for i, p in enumerate(pacientes, 1):
            nombre = p.get("paciente_nombre", "Sin nombre")
            hora = p.get("hora_inicio", "")
            medico = p.get("medico_nombre", "")
            estado = p.get("estado", "")
            lineas.append(f"{i}. *{nombre}*")
            if hora:
                lineas.append(f"   🕐 {hora}")
            if medico:
                lineas.append(f"   👨‍⚕️ {medico}")
            if estado:
                lineas.append(f"   📋 {estado}")

        return RespuestaAgente(
            exito=True,
            mensaje="\n".join(lineas),
            datos={"cantidad": len(pacientes)},
        )

    async def _ver_turnos(self, parametros: dict[str, Any]) -> RespuestaAgente:
        """Obtiene y formatea los turnos del día.

        Args:
            parametros: Puede incluir 'fecha' (YYYY-MM-DD). Sin fecha usa hoy.

        Returns:
            RespuestaAgente con lista de turnos del día.
        """
        from datetime import date

        fecha = parametros.get("fecha", date.today().isoformat())

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{_API_BASE}/api/v1/agenda/turnos",
                headers=self._get_headers(),
                params={"fecha": fecha},
            )
            response.raise_for_status()
            data = response.json()

        turnos = data if isinstance(data, list) else data.get("turnos", [])

        if not turnos:
            return RespuestaAgente(
                exito=True,
                mensaje=f"📅 No hay turnos programados para el {fecha}.",
                datos={"cantidad": 0, "fecha": fecha},
            )

        lineas = [f"📅 *Turnos del {fecha}*\n"]
        for t in turnos:
            hora = t.get("hora_inicio", "")
            nombre = t.get("paciente_nombre", "Sin nombre")
            medico = t.get("medico_nombre", "")
            estado = t.get("estado", "")
            estado_emoji = {"programado": "🟡", "confirmado": "🟢", "cancelado": "🔴", "completado": "✅"}.get(estado, "⚪")
            lineas.append(f"{estado_emoji} {hora} — *{nombre}*")
            if medico:
                lineas.append(f"   👨‍⚕️ {medico}")

        return RespuestaAgente(
            exito=True,
            mensaje="\n".join(lineas),
            datos={"cantidad": len(turnos), "fecha": fecha},
        )

    async def _crear_turno(self, parametros: dict[str, Any]) -> RespuestaAgente:
        """Crea un nuevo turno si los parámetros son suficientes.

        Requiere: paciente_id o paciente_nombre, fecha, hora, medico_id.
        Si faltan datos, devuelve un mensaje solicitando la información.

        Args:
            parametros: Datos del turno a crear.

        Returns:
            RespuestaAgente con confirmación o solicitud de datos faltantes.
        """
        campos_requeridos = ["fecha", "hora"]
        faltantes = [c for c in campos_requeridos if not parametros.get(c)]

        if faltantes or (not parametros.get("paciente_id") and not parametros.get("paciente_nombre")):
            datos_faltantes = faltantes + (
                ["nombre o ID del paciente"]
                if not parametros.get("paciente_id") and not parametros.get("paciente_nombre")
                else []
            )
            return RespuestaAgente(
                exito=False,
                mensaje=(
                    "Para crear el turno necesito más información:\n"
                    + "\n".join(f"• {d}" for d in datos_faltantes)
                ),
                error="datos_insuficientes",
            )

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{_API_BASE}/api/v1/agenda/turnos",
                headers=self._get_headers(),
                json=parametros,
            )
            response.raise_for_status()
            turno = response.json()

        return RespuestaAgente(
            exito=True,
            mensaje=(
                f"✅ Turno creado exitosamente\n"
                f"📅 Fecha: {turno.get('fecha', parametros.get('fecha'))}\n"
                f"🕐 Hora: {turno.get('hora_inicio', parametros.get('hora'))}\n"
                f"🆔 ID: {turno.get('id', 'N/A')}"
            ),
            datos=turno,
        )

    async def _cancelar_turno(self, parametros: dict[str, Any]) -> RespuestaAgente:
        """Cancela un turno por su ID.

        Args:
            parametros: Debe incluir 'turno_id' con el UUID del turno.

        Returns:
            RespuestaAgente con confirmación de cancelación.
        """
        turno_id = parametros.get("turno_id")
        if not turno_id:
            return RespuestaAgente(
                exito=False,
                mensaje="Para cancelar el turno necesito el ID del turno. ¿Podés proporcionarlo?",
                error="turno_id_requerido",
            )

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.patch(
                f"{_API_BASE}/api/v1/agenda/turnos/{turno_id}",
                headers=self._get_headers(),
                json={"estado": "cancelado"},
            )
            response.raise_for_status()

        logger.info(
            "Turno cancelado via agente",
            extra={"turno_token": f"[TURNO_{str(turno_id)[:8]}]"},
        )
        return RespuestaAgente(
            exito=True,
            mensaje=f"✅ Turno cancelado correctamente.",
            datos={"turno_id": str(turno_id)},
        )
