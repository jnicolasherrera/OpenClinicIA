"""Endpoints de pacientes e historia clínica."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user, require_role
from api.v1.pacientes.schemas import (
    EpisodioCreate,
    EpisodioResponse,
    PacienteCreate,
    PacienteResponse,
    PacienteUpdate,
)
from api.v1.pacientes.service_historia_clinica import HistoriaClinicaService
from core.database import get_db
from models.usuario import Usuario

router = APIRouter(prefix="/pacientes", tags=["pacientes"])


def _get_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
) -> HistoriaClinicaService:
    """Construye el HistoriaClinicaService con el tenant del usuario autenticado.

    Args:
        db: Sesión de base de datos.
        current_user: Usuario autenticado.

    Returns:
        Instancia de HistoriaClinicaService.
    """
    return HistoriaClinicaService(db=db, tenant_id=current_user.tenant_id)


@router.get("", response_model=list[PacienteResponse])
async def buscar_pacientes(
    q: str = Query(default="", min_length=1),
    service: HistoriaClinicaService = Depends(_get_service),
    _: Usuario = Depends(require_role("medico", "recepcion", "admin")),
) -> list[PacienteResponse]:
    """Busca pacientes por nombre, apellido, DNI o número de historia.

    Args:
        q: Texto de búsqueda.
        service: Servicio de historia clínica.

    Returns:
        Lista de pacientes coincidentes.
    """
    return await service.buscar_pacientes(q)


@router.get("/{paciente_id}", response_model=PacienteResponse)
async def obtener_paciente(
    paciente_id: uuid.UUID,
    service: HistoriaClinicaService = Depends(_get_service),
    _: Usuario = Depends(require_role("medico", "recepcion", "admin")),
) -> PacienteResponse:
    """Obtiene los datos de un paciente por su ID.

    Args:
        paciente_id: UUID del paciente.
        service: Servicio de historia clínica.

    Returns:
        PacienteResponse.
    """
    return await service.obtener_paciente(paciente_id)


@router.post("", response_model=PacienteResponse, status_code=status.HTTP_201_CREATED)
async def crear_paciente(
    body: PacienteCreate,
    service: HistoriaClinicaService = Depends(_get_service),
    _: Usuario = Depends(require_role("recepcion", "admin")),
) -> PacienteResponse:
    """Registra un nuevo paciente.

    Args:
        body: Datos del nuevo paciente.
        service: Servicio de historia clínica.

    Returns:
        PacienteResponse del paciente creado.
    """
    return await service.crear_paciente(body)


@router.patch("/{paciente_id}", response_model=PacienteResponse)
async def actualizar_paciente(
    paciente_id: uuid.UUID,
    body: PacienteUpdate,
    service: HistoriaClinicaService = Depends(_get_service),
    _: Usuario = Depends(require_role("recepcion", "admin")),
) -> PacienteResponse:
    """Actualiza parcialmente los datos de un paciente.

    Args:
        paciente_id: UUID del paciente.
        body: Campos a actualizar.
        service: Servicio de historia clínica.

    Returns:
        PacienteResponse actualizado.
    """
    return await service.actualizar_paciente(paciente_id, body)


@router.get("/{paciente_id}/historia", response_model=list[EpisodioResponse])
async def obtener_historia(
    paciente_id: uuid.UUID,
    service: HistoriaClinicaService = Depends(_get_service),
    _: Usuario = Depends(require_role("medico", "admin")),
) -> list[EpisodioResponse]:
    """Lista todos los episodios de la historia clínica de un paciente.

    Args:
        paciente_id: UUID del paciente.
        service: Servicio de historia clínica.

    Returns:
        Lista de episodios ordenados por fecha descendente.
    """
    return await service.listar_episodios(paciente_id)


@router.post(
    "/{paciente_id}/episodios",
    response_model=EpisodioResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear_episodio(
    paciente_id: uuid.UUID,
    body: EpisodioCreate,
    service: HistoriaClinicaService = Depends(_get_service),
    _: Usuario = Depends(require_role("medico", "admin")),
) -> EpisodioResponse:
    """Crea un nuevo episodio clínico para un paciente.

    Args:
        paciente_id: UUID del paciente.
        body: Datos del episodio.
        service: Servicio de historia clínica.

    Returns:
        EpisodioResponse del episodio creado.
    """
    return await service.crear_episodio(paciente_id, body)
