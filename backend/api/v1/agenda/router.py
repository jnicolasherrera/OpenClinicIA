"""Endpoints de la agenda médica."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user, require_role
from api.v1.agenda.schemas import SalaEsperaItem, TurnoCreate, TurnoResponse, TurnoUpdate
from api.v1.agenda.service_agenda import AgendaService
from core.database import get_db
from models.usuario import Usuario

router = APIRouter(prefix="/agenda", tags=["agenda"])


def _get_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
) -> AgendaService:
    """Construye el AgendaService con el tenant del usuario autenticado.

    Args:
        db: Sesión de base de datos.
        current_user: Usuario autenticado.

    Returns:
        Instancia de AgendaService lista para usar.
    """
    return AgendaService(db=db, tenant_id=current_user.tenant_id)


@router.get("/turnos", response_model=list[TurnoResponse])
async def listar_turnos(
    fecha: date | None = Query(default=None),
    medico_id: uuid.UUID | None = Query(default=None),
    service: AgendaService = Depends(_get_service),
    _: Usuario = Depends(require_role("medico", "recepcion", "admin")),
) -> list[TurnoResponse]:
    """Lista turnos opcionalmente filtrados por fecha y/o médico.

    Args:
        fecha: Fecha a consultar (opcional).
        medico_id: UUID del médico a filtrar (opcional).
        service: Servicio de agenda.

    Returns:
        Lista de TurnoResponse.
    """
    if medico_id is not None and fecha is not None:
        return await service.listar_por_medico_fecha(medico_id, fecha)
    # Retornar sala de espera como fallback si no hay parámetros
    return []


@router.post("/turnos", response_model=TurnoResponse, status_code=status.HTTP_201_CREATED)
async def crear_turno(
    body: TurnoCreate,
    service: AgendaService = Depends(_get_service),
    _: Usuario = Depends(require_role("medico", "recepcion", "admin")),
) -> TurnoResponse:
    """Crea un nuevo turno en la agenda.

    Args:
        body: Datos del turno a crear.
        service: Servicio de agenda.

    Returns:
        TurnoResponse del turno creado.
    """
    return await service.crear_turno(body)


@router.patch("/turnos/{turno_id}", response_model=TurnoResponse)
async def actualizar_turno(
    turno_id: uuid.UUID,
    body: TurnoUpdate,
    service: AgendaService = Depends(_get_service),
    _: Usuario = Depends(require_role("medico", "recepcion", "admin")),
) -> TurnoResponse:
    """Actualiza parcialmente un turno.

    Args:
        turno_id: UUID del turno a actualizar.
        body: Campos a actualizar.
        service: Servicio de agenda.

    Returns:
        TurnoResponse actualizado.
    """
    return await service.actualizar_turno(turno_id, body)


@router.delete("/turnos/{turno_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_turno(
    turno_id: uuid.UUID,
    service: AgendaService = Depends(_get_service),
    _: Usuario = Depends(require_role("admin")),
) -> None:
    """Elimina un turno. Solo accesible para administradores.

    Args:
        turno_id: UUID del turno.
        service: Servicio de agenda.
    """
    await service.eliminar_turno(turno_id)


@router.get("/sala-espera", response_model=list[SalaEsperaItem])
async def obtener_sala_espera(
    service: AgendaService = Depends(_get_service),
    _: Usuario = Depends(require_role("medico", "recepcion", "admin")),
) -> list[SalaEsperaItem]:
    """Retorna la lista de pacientes actualmente en sala de espera.

    Args:
        service: Servicio de agenda.

    Returns:
        Lista de SalaEsperaItem con tiempo de espera calculado.
    """
    return await service.obtener_sala_espera()


@router.post("/turnos/{turno_id}/ingresar-sala", response_model=TurnoResponse)
async def ingresar_sala(
    turno_id: uuid.UUID,
    service: AgendaService = Depends(_get_service),
    _: Usuario = Depends(require_role("medico", "recepcion", "admin")),
) -> TurnoResponse:
    """Registra el ingreso de un paciente a la sala de espera.

    Args:
        turno_id: UUID del turno.
        service: Servicio de agenda.

    Returns:
        TurnoResponse con estado actualizado a 'en_sala'.
    """
    return await service.confirmar_ingreso_sala(turno_id)
