"""Repositorio de acceso a datos para Turnos."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.logging import get_logger
from models.turno import Turno

logger = get_logger(__name__)


class TurnoRepository:
    """Gestiona el acceso a datos de la entidad Turno.

    Todos los métodos filtran siempre por ``tenant_id`` para garantizar
    aislamiento multi-tenant.
    """

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        """Inicializa el repositorio con sesión y tenant.

        Args:
            db: Sesión async de SQLAlchemy.
            tenant_id: UUID del tenant actual.
        """
        self._db = db
        self._tenant_id = tenant_id

    async def get_by_id(self, turno_id: uuid.UUID) -> Turno | None:
        """Obtiene un turno por su ID dentro del tenant.

        Args:
            turno_id: UUID del turno.

        Returns:
            El turno encontrado o None.
        """
        result = await self._db.execute(
            select(Turno)
            .where(
                and_(
                    Turno.id == turno_id,
                    Turno.tenant_id == self._tenant_id,
                )
            )
            .options(selectinload(Turno.paciente), selectinload(Turno.medico))
        )
        return result.scalar_one_or_none()

    async def get_by_medico_fecha(
        self, medico_id: uuid.UUID, fecha: date
    ) -> list[Turno]:
        """Retorna todos los turnos de un médico en una fecha dada.

        Args:
            medico_id: UUID del médico.
            fecha: Fecha a consultar.

        Returns:
            Lista de turnos ordenados por hora.
        """
        inicio = datetime(fecha.year, fecha.month, fecha.day, 0, 0, 0, tzinfo=timezone.utc)
        fin = datetime(fecha.year, fecha.month, fecha.day, 23, 59, 59, tzinfo=timezone.utc)
        result = await self._db.execute(
            select(Turno)
            .where(
                and_(
                    Turno.tenant_id == self._tenant_id,
                    Turno.medico_id == medico_id,
                    Turno.fecha_hora >= inicio,
                    Turno.fecha_hora <= fin,
                    Turno.estado.notin_(["cancelado", "ausente"]),
                )
            )
            .options(selectinload(Turno.paciente), selectinload(Turno.medico))
            .order_by(Turno.fecha_hora)
        )
        return list(result.scalars().all())

    async def get_sala_espera(self) -> list[Turno]:
        """Retorna los turnos actualmente en sala de espera o en atención.

        Returns:
            Lista de turnos en estados en_sala o en_atencion.
        """
        result = await self._db.execute(
            select(Turno)
            .where(
                and_(
                    Turno.tenant_id == self._tenant_id,
                    Turno.estado.in_(["en_sala", "en_atencion", "confirmado"]),
                )
            )
            .options(selectinload(Turno.paciente), selectinload(Turno.medico))
            .order_by(Turno.sala_espera_ingreso.asc().nullslast(), Turno.fecha_hora)
        )
        return list(result.scalars().all())

    async def create(self, data: dict) -> Turno:
        """Crea un nuevo turno.

        Args:
            data: Diccionario con los campos del turno.

        Returns:
            El turno creado con ID asignado.
        """
        turno = Turno(**data, tenant_id=self._tenant_id)
        self._db.add(turno)
        await self._db.flush()
        await self._db.refresh(turno)
        logger.info(
            "Turno creado",
            extra={"turno_id": str(turno.id), "tenant_id": str(self._tenant_id)},
        )
        return turno

    async def update(self, turno: Turno, data: dict) -> Turno:
        """Actualiza los campos de un turno existente.

        Args:
            turno: Instancia del turno a actualizar.
            data: Diccionario con los campos a actualizar (sin None).

        Returns:
            El turno actualizado.
        """
        for field, value in data.items():
            setattr(turno, field, value)
        await self._db.flush()
        await self._db.refresh(turno)
        logger.info("Turno actualizado", extra={"turno_id": str(turno.id)})
        return turno

    async def delete(self, turno: Turno) -> None:
        """Elimina un turno de la base de datos.

        Args:
            turno: Instancia del turno a eliminar.
        """
        await self._db.delete(turno)
        await self._db.flush()
        logger.info("Turno eliminado", extra={"turno_id": str(turno.id)})

    async def get_overlapping(
        self,
        medico_id: uuid.UUID,
        fecha_hora: datetime,
        duracion_minutos: int,
        exclude_id: uuid.UUID | None = None,
    ) -> list[Turno]:
        """Busca turnos que se solapen con el rango horario dado para un médico.

        Args:
            medico_id: UUID del médico.
            fecha_hora: Inicio del turno a verificar.
            duracion_minutos: Duración del turno a verificar.
            exclude_id: UUID de turno a excluir de la búsqueda (para updates).

        Returns:
            Lista de turnos que se solapan.
        """
        from datetime import timedelta

        fin_propuesto = fecha_hora + timedelta(minutes=duracion_minutos)

        query = select(Turno).where(
            and_(
                Turno.tenant_id == self._tenant_id,
                Turno.medico_id == medico_id,
                Turno.estado.notin_(["cancelado", "ausente"]),
                Turno.fecha_hora < fin_propuesto,
            )
        )
        if exclude_id:
            query = query.where(Turno.id != exclude_id)

        result = await self._db.execute(query)
        turnos = list(result.scalars().all())

        # Filtrar los que realmente se superponen
        from datetime import timedelta as td

        solapados = []
        for t in turnos:
            fin_existente = t.fecha_hora + td(minutes=t.duracion_minutos)
            if t.fecha_hora < fin_propuesto and fin_existente > fecha_hora:
                solapados.append(t)
        return solapados
