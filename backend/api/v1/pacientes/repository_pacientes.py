"""Repositorios de acceso a datos para Pacientes y Episodios."""

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from models.episodio import Episodio
from models.paciente import Paciente

logger = get_logger(__name__)


class PacienteRepository:
    """Gestiona el acceso a datos de la entidad Paciente.

    Todos los métodos filtran siempre por ``tenant_id``.
    """

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        """Inicializa el repositorio con sesión y tenant.

        Args:
            db: Sesión async de SQLAlchemy.
            tenant_id: UUID del tenant actual.
        """
        self._db = db
        self._tenant_id = tenant_id

    async def get_by_id(self, paciente_id: uuid.UUID) -> Paciente | None:
        """Obtiene un paciente por su UUID dentro del tenant.

        Args:
            paciente_id: UUID del paciente.

        Returns:
            Paciente encontrado o None.
        """
        result = await self._db.execute(
            select(Paciente).where(
                and_(
                    Paciente.id == paciente_id,
                    Paciente.tenant_id == self._tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def search(self, query: str, limit: int = 20) -> list[Paciente]:
        """Busca pacientes por nombre, apellido, DNI o número de historia.

        La búsqueda es case-insensitive y usa LIKE para compatibilidad.

        Args:
            query: Texto a buscar.
            limit: Máximo de resultados.

        Returns:
            Lista de pacientes que coinciden.
        """
        pattern = f"%{query}%"
        result = await self._db.execute(
            select(Paciente)
            .where(
                and_(
                    Paciente.tenant_id == self._tenant_id,
                    Paciente.activo.is_(True),
                    or_(
                        Paciente.nombre.ilike(pattern),
                        Paciente.apellido.ilike(pattern),
                        Paciente.dni.ilike(pattern),
                        Paciente.numero_historia.ilike(pattern),
                    ),
                )
            )
            .order_by(Paciente.apellido, Paciente.nombre)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, data: dict) -> Paciente:
        """Crea un nuevo paciente en la base de datos.

        Args:
            data: Diccionario con los campos del paciente.

        Returns:
            Paciente creado con ID asignado.
        """
        paciente = Paciente(**data, tenant_id=self._tenant_id)
        self._db.add(paciente)
        await self._db.flush()
        await self._db.refresh(paciente)
        logger.info(
            "Paciente creado",
            extra={"paciente_token": f"[PACIENTE_{paciente.id}]"},
        )
        return paciente

    async def update(self, paciente: Paciente, data: dict) -> Paciente:
        """Actualiza los campos de un paciente existente.

        Args:
            paciente: Instancia del paciente.
            data: Campos a actualizar.

        Returns:
            Paciente actualizado.
        """
        for field, value in data.items():
            setattr(paciente, field, value)
        await self._db.flush()
        await self._db.refresh(paciente)
        logger.info(
            "Paciente actualizado",
            extra={"paciente_token": f"[PACIENTE_{paciente.id}]"},
        )
        return paciente


class EpisodioRepository:
    """Gestiona el acceso a datos de la entidad Episodio."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        """Inicializa el repositorio.

        Args:
            db: Sesión async de SQLAlchemy.
            tenant_id: UUID del tenant actual.
        """
        self._db = db
        self._tenant_id = tenant_id

    async def get_by_paciente(
        self, paciente_id: uuid.UUID, limit: int = 50
    ) -> list[Episodio]:
        """Obtiene todos los episodios de un paciente ordenados por fecha descendente.

        Args:
            paciente_id: UUID del paciente.
            limit: Máximo de episodios a retornar.

        Returns:
            Lista de episodios.
        """
        result = await self._db.execute(
            select(Episodio)
            .where(
                and_(
                    Episodio.tenant_id == self._tenant_id,
                    Episodio.paciente_id == paciente_id,
                )
            )
            .order_by(Episodio.fecha.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, paciente_id: uuid.UUID, data: dict) -> Episodio:
        """Crea un nuevo episodio clínico.

        Args:
            paciente_id: UUID del paciente.
            data: Datos del episodio.

        Returns:
            Episodio creado.
        """
        episodio = Episodio(
            **data,
            paciente_id=paciente_id,
            tenant_id=self._tenant_id,
        )
        self._db.add(episodio)
        await self._db.flush()
        await self._db.refresh(episodio)
        logger.info(
            "Episodio creado",
            extra={
                "paciente_token": f"[PACIENTE_{paciente_id}]",
                "episodio_id": str(episodio.id),
            },
        )
        return episodio

    async def update(self, episodio: Episodio, data: dict) -> Episodio:
        """Actualiza los campos de un episodio existente.

        Args:
            episodio: Instancia del episodio.
            data: Campos a actualizar.

        Returns:
            Episodio actualizado.
        """
        for field, value in data.items():
            setattr(episodio, field, value)
        await self._db.flush()
        await self._db.refresh(episodio)
        return episodio

    async def get_by_id(self, episodio_id: uuid.UUID) -> Episodio | None:
        """Obtiene un episodio por su UUID.

        Args:
            episodio_id: UUID del episodio.

        Returns:
            Episodio encontrado o None.
        """
        result = await self._db.execute(
            select(Episodio).where(
                and_(
                    Episodio.id == episodio_id,
                    Episodio.tenant_id == self._tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()
