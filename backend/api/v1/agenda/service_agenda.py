"""Servicio de lógica de negocio para la agenda de turnos."""

import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.agenda.repository_turnos import TurnoRepository
from api.v1.agenda.schemas import SalaEsperaItem, TurnoCreate, TurnoResponse, TurnoUpdate
from core.logging import get_logger
from models.turno import Turno

logger = get_logger(__name__)


def _build_turno_response(turno: Turno) -> TurnoResponse:
    """Construye un TurnoResponse a partir de un modelo ORM con relaciones cargadas.

    Args:
        turno: Instancia de Turno con relaciones paciente y medico cargadas.

    Returns:
        TurnoResponse con nombres calculados.
    """
    paciente_nombre: str | None = None
    medico_nombre: str | None = None

    if turno.paciente is not None:
        paciente_nombre = f"{turno.paciente.nombre} {turno.paciente.apellido}"
    if turno.medico is not None:
        medico_nombre = f"{turno.medico.nombre} {turno.medico.apellido}"

    resp = TurnoResponse.model_validate(turno)
    resp.paciente_nombre = paciente_nombre
    resp.medico_nombre = medico_nombre
    return resp


class AgendaService:
    """Orquesta la lógica de negocio de la agenda médica."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        """Inicializa el servicio con sesión y tenant.

        Args:
            db: Sesión async de SQLAlchemy.
            tenant_id: UUID del tenant actual.
        """
        self._repo = TurnoRepository(db, tenant_id)
        self._tenant_id = tenant_id

    async def crear_turno(self, data: TurnoCreate) -> TurnoResponse:
        """Crea un turno validando que no haya solapamiento horario.

        Args:
            data: Datos del turno a crear.

        Returns:
            TurnoResponse del turno creado.

        Raises:
            HTTPException 409: Si ya existe un turno en el mismo horario para el médico.
        """
        solapados = await self._repo.get_overlapping(
            medico_id=data.medico_id,
            fecha_hora=data.fecha_hora,
            duracion_minutos=data.duracion_minutos,
        )
        if solapados:
            logger.warning(
                "Intento de crear turno con solapamiento",
                extra={"medico_id": str(data.medico_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El médico ya tiene un turno en ese horario",
            )

        turno_data = data.model_dump()
        turno = await self._repo.create(turno_data)
        return _build_turno_response(turno)

    async def actualizar_turno(
        self, turno_id: uuid.UUID, data: TurnoUpdate
    ) -> TurnoResponse:
        """Actualiza los campos de un turno.

        Args:
            turno_id: UUID del turno a actualizar.
            data: Datos a actualizar.

        Returns:
            TurnoResponse actualizado.

        Raises:
            HTTPException 404: Si el turno no existe.
        """
        turno = await self._repo.get_by_id(turno_id)
        if turno is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        turno = await self._repo.update(turno, update_data)
        return _build_turno_response(turno)

    async def confirmar_ingreso_sala(self, turno_id: uuid.UUID) -> TurnoResponse:
        """Registra el ingreso del paciente a la sala de espera.

        Cambia el estado del turno a 'en_sala' y registra la hora de ingreso.

        Args:
            turno_id: UUID del turno.

        Returns:
            TurnoResponse actualizado.

        Raises:
            HTTPException 404: Si el turno no existe.
            HTTPException 400: Si el turno ya fue procesado o cancelado.
        """
        turno = await self._repo.get_by_id(turno_id)
        if turno is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")

        estados_invalidos = ("completado", "cancelado", "ausente", "en_atencion")
        if turno.estado in estados_invalidos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede ingresar a sala un turno en estado '{turno.estado}'",
            )

        turno = await self._repo.update(
            turno,
            {
                "estado": "en_sala",
                "sala_espera_ingreso": datetime.now(timezone.utc),
            },
        )
        logger.info("Paciente ingresó a sala de espera", extra={"turno_id": str(turno_id)})
        return _build_turno_response(turno)

    async def obtener_sala_espera(self) -> list[SalaEsperaItem]:
        """Retorna la lista actual de sala de espera con tiempos calculados.

        Returns:
            Lista de SalaEsperaItem ordenada por hora de ingreso.
        """
        turnos = await self._repo.get_sala_espera()
        ahora = datetime.now(timezone.utc)
        items: list[SalaEsperaItem] = []

        for turno in turnos:
            paciente_nombre = (
                f"{turno.paciente.nombre} {turno.paciente.apellido}"
                if turno.paciente
                else "Desconocido"
            )
            medico_nombre = (
                f"{turno.medico.nombre} {turno.medico.apellido}"
                if turno.medico
                else "Desconocido"
            )

            tiempo_espera: int | None = None
            if turno.sala_espera_ingreso is not None:
                ingreso = turno.sala_espera_ingreso
                if ingreso.tzinfo is None:
                    ingreso = ingreso.replace(tzinfo=timezone.utc)
                tiempo_espera = int((ahora - ingreso).total_seconds() / 60)

            items.append(
                SalaEsperaItem(
                    turno_id=turno.id,
                    paciente_nombre=paciente_nombre,
                    medico_nombre=medico_nombre,
                    hora_turno=turno.fecha_hora,
                    estado=turno.estado,
                    tiempo_espera_minutos=tiempo_espera,
                )
            )
        return items

    async def cancelar_turno(self, turno_id: uuid.UUID) -> TurnoResponse:
        """Cancela un turno cambiando su estado a 'cancelado'.

        Args:
            turno_id: UUID del turno a cancelar.

        Returns:
            TurnoResponse con el estado actualizado.

        Raises:
            HTTPException 404: Si el turno no existe.
            HTTPException 400: Si el turno ya está completado o cancelado.
        """
        turno = await self._repo.get_by_id(turno_id)
        if turno is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")

        if turno.estado in ("completado", "cancelado"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede cancelar un turno en estado '{turno.estado}'",
            )

        turno = await self._repo.update(turno, {"estado": "cancelado"})
        logger.info("Turno cancelado", extra={"turno_id": str(turno_id)})
        return _build_turno_response(turno)

    async def get_by_id(self, turno_id: uuid.UUID) -> TurnoResponse:
        """Obtiene un turno por ID.

        Args:
            turno_id: UUID del turno.

        Returns:
            TurnoResponse del turno.

        Raises:
            HTTPException 404: Si no existe.
        """
        turno = await self._repo.get_by_id(turno_id)
        if turno is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")
        return _build_turno_response(turno)

    async def listar_por_medico_fecha(
        self, medico_id: uuid.UUID, fecha: date
    ) -> list[TurnoResponse]:
        """Lista los turnos de un médico en una fecha dada.

        Args:
            medico_id: UUID del médico.
            fecha: Fecha a consultar.

        Returns:
            Lista de TurnoResponse.
        """
        turnos = await self._repo.get_by_medico_fecha(medico_id, fecha)
        return [_build_turno_response(t) for t in turnos]

    async def eliminar_turno(self, turno_id: uuid.UUID) -> None:
        """Elimina físicamente un turno.

        Args:
            turno_id: UUID del turno.

        Raises:
            HTTPException 404: Si el turno no existe.
        """
        turno = await self._repo.get_by_id(turno_id)
        if turno is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")
        await self._repo.delete(turno)
