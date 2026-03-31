"""Servicio de historia clínica y gestión de pacientes."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.pacientes.repository_pacientes import EpisodioRepository, PacienteRepository
from api.v1.pacientes.schemas import (
    EpisodioCreate,
    EpisodioResponse,
    PacienteCreate,
    PacienteResponse,
    PacienteUpdate,
)
from core.logging import get_logger
from models.episodio import Episodio
from models.paciente import Paciente

logger = get_logger(__name__)


class HistoriaClinicaService:
    """Orquesta la lógica de negocio de pacientes e historia clínica."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        """Inicializa el servicio.

        Args:
            db: Sesión async de SQLAlchemy.
            tenant_id: UUID del tenant actual.
        """
        self._paciente_repo = PacienteRepository(db, tenant_id)
        self._episodio_repo = EpisodioRepository(db, tenant_id)
        self._tenant_id = tenant_id

    async def buscar_pacientes(self, query: str) -> list[PacienteResponse]:
        """Busca pacientes por texto libre (nombre, apellido, DNI, historia).

        Args:
            query: Texto de búsqueda.

        Returns:
            Lista de PacienteResponse que coinciden.
        """
        pacientes = await self._paciente_repo.search(query)
        return [PacienteResponse.model_validate(p) for p in pacientes]

    async def obtener_paciente(self, paciente_id: uuid.UUID) -> PacienteResponse:
        """Obtiene un paciente por su ID.

        Args:
            paciente_id: UUID del paciente.

        Returns:
            PacienteResponse.

        Raises:
            HTTPException 404: Si el paciente no existe.
        """
        paciente = await self._paciente_repo.get_by_id(paciente_id)
        if paciente is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Paciente no encontrado",
            )
        return PacienteResponse.model_validate(paciente)

    async def obtener_historia_completa(self, paciente_id: uuid.UUID) -> dict:
        """Obtiene la historia clínica completa de un paciente.

        Args:
            paciente_id: UUID del paciente.

        Returns:
            Diccionario con datos del paciente y lista de episodios.

        Raises:
            HTTPException 404: Si el paciente no existe.
        """
        paciente = await self._paciente_repo.get_by_id(paciente_id)
        if paciente is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paciente no encontrado",
            )

        episodios = await self._episodio_repo.get_by_paciente(paciente_id)
        logger.info(
            "Historia clínica consultada",
            extra={
                "paciente_token": f"[PACIENTE_{paciente_id}]",
                "num_episodios": len(episodios),
            },
        )
        return {
            "paciente": PacienteResponse.model_validate(paciente),
            "episodios": [EpisodioResponse.model_validate(e) for e in episodios],
        }

    async def crear_paciente(self, data: PacienteCreate) -> PacienteResponse:
        """Registra un nuevo paciente en el sistema.

        Args:
            data: Datos del paciente a crear.

        Returns:
            PacienteResponse del paciente creado.
        """
        paciente = await self._paciente_repo.create(data.model_dump())
        logger.info(
            "Nuevo paciente registrado",
            extra={"paciente_token": f"[PACIENTE_{paciente.id}]"},
        )
        return PacienteResponse.model_validate(paciente)

    async def actualizar_paciente(
        self, paciente_id: uuid.UUID, data: PacienteUpdate
    ) -> PacienteResponse:
        """Actualiza los datos de un paciente.

        Args:
            paciente_id: UUID del paciente.
            data: Campos a actualizar.

        Returns:
            PacienteResponse actualizado.

        Raises:
            HTTPException 404: Si el paciente no existe.
        """
        paciente = await self._paciente_repo.get_by_id(paciente_id)
        if paciente is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paciente no encontrado",
            )
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        paciente = await self._paciente_repo.update(paciente, update_data)
        return PacienteResponse.model_validate(paciente)

    async def listar_episodios(self, paciente_id: uuid.UUID) -> list[EpisodioResponse]:
        """Lista todos los episodios de un paciente.

        Args:
            paciente_id: UUID del paciente.

        Returns:
            Lista de EpisodioResponse ordenados por fecha descendente.

        Raises:
            HTTPException 404: Si el paciente no existe.
        """
        paciente = await self._paciente_repo.get_by_id(paciente_id)
        if paciente is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paciente no encontrado",
            )
        episodios = await self._episodio_repo.get_by_paciente(paciente_id)
        return [EpisodioResponse.model_validate(e) for e in episodios]

    async def crear_episodio(
        self, paciente_id: uuid.UUID, data: EpisodioCreate
    ) -> EpisodioResponse:
        """Crea un nuevo episodio clínico para el paciente.

        Args:
            paciente_id: UUID del paciente.
            data: Datos del episodio.

        Returns:
            EpisodioResponse del episodio creado.

        Raises:
            HTTPException 404: Si el paciente no existe.
        """
        paciente = await self._paciente_repo.get_by_id(paciente_id)
        if paciente is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paciente no encontrado",
            )

        episodio = await self._episodio_repo.create(paciente_id, data.model_dump())
        return EpisodioResponse.model_validate(episodio)

    async def actualizar_episodio(
        self, episodio_id: uuid.UUID, data: dict
    ) -> EpisodioResponse:
        """Actualiza los campos de un episodio existente.

        Args:
            episodio_id: UUID del episodio.
            data: Campos a actualizar.

        Returns:
            EpisodioResponse actualizado.

        Raises:
            HTTPException 404: Si el episodio no existe.
        """
        episodio = await self._episodio_repo.get_by_id(episodio_id)
        if episodio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Episodio no encontrado",
            )
        updated = await self._episodio_repo.update(episodio, data)
        return EpisodioResponse.model_validate(updated)
