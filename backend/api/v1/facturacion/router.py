"""Endpoints de facturación — MOD_05."""

import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user, require_role
from api.v1.facturacion.schemas import (
    ComprobanteCreate,
    ComprobanteResponse,
    ComprobanteUpdate,
    ObraSocialCreate,
    ObraSocialResponse,
    ResumenFacturacionResponse,
)
from api.v1.facturacion.service_facturacion import FacturacionService
from core.database import get_db
from models.usuario import Usuario

router = APIRouter(prefix="/facturacion", tags=["facturacion"])


def _get_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
) -> FacturacionService:
    """Construye el FacturacionService con el tenant del usuario autenticado.

    Args:
        db: Sesión de base de datos.
        current_user: Usuario autenticado.

    Returns:
        Instancia de FacturacionService.
    """
    return FacturacionService(db=db, tenant_id=current_user.tenant_id)


# ─── Obras Sociales ───────────────────────────────────────────────────────────


@router.get("/obras-sociales", response_model=list[ObraSocialResponse])
async def listar_obras_sociales(
    service: FacturacionService = Depends(_get_service),
    _: Usuario = Depends(require_role("medico", "recepcion", "admin")),
) -> list[ObraSocialResponse]:
    """Lista todas las obras sociales activas del tenant.

    Returns:
        Lista de ObraSocialResponse.
    """
    obras = await service.listar_obras_sociales()
    return [ObraSocialResponse.model_validate(o) for o in obras]


@router.post(
    "/obras-sociales",
    response_model=ObraSocialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear_obra_social(
    body: ObraSocialCreate,
    service: FacturacionService = Depends(_get_service),
    _: Usuario = Depends(require_role("recepcion", "admin")),
) -> ObraSocialResponse:
    """Registra una nueva obra social.

    Args:
        body: Datos de la obra social.

    Returns:
        ObraSocialResponse creada.
    """
    obra = await service.crear_obra_social(body)
    return ObraSocialResponse.model_validate(obra)


# ─── Comprobantes ─────────────────────────────────────────────────────────────


@router.get("/comprobantes", response_model=list[ComprobanteResponse])
async def listar_comprobantes(
    paciente_id: Optional[uuid.UUID] = Query(default=None),
    estado: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: FacturacionService = Depends(_get_service),
    _: Usuario = Depends(require_role("medico", "recepcion", "admin")),
) -> list[ComprobanteResponse]:
    """Lista comprobantes con filtros opcionales y paginación.

    Args:
        paciente_id: Filtra por paciente.
        estado: Filtra por estado.
        limit: Máximo de resultados.
        offset: Desplazamiento para paginación.

    Returns:
        Lista de ComprobanteResponse.
    """
    comprobantes = await service._repo.get_comprobantes(
        paciente_id=paciente_id,
        estado=estado,
        limit=limit,
        offset=offset,
    )
    return [ComprobanteResponse.model_validate(c) for c in comprobantes]


@router.post(
    "/comprobantes",
    response_model=ComprobanteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear_comprobante(
    body: ComprobanteCreate,
    service: FacturacionService = Depends(_get_service),
    _: Usuario = Depends(require_role("recepcion", "admin")),
) -> ComprobanteResponse:
    """Crea un nuevo comprobante de facturación.

    Args:
        body: Datos del comprobante e ítems.

    Returns:
        ComprobanteResponse creado.
    """
    comprobante = await service.crear_comprobante(body)
    return ComprobanteResponse.model_validate(comprobante)


@router.get("/comprobantes/{comprobante_id}", response_model=ComprobanteResponse)
async def obtener_comprobante(
    comprobante_id: uuid.UUID,
    service: FacturacionService = Depends(_get_service),
    _: Usuario = Depends(require_role("medico", "recepcion", "admin")),
) -> ComprobanteResponse:
    """Obtiene un comprobante por su UUID con sus ítems.

    Args:
        comprobante_id: UUID del comprobante.

    Returns:
        ComprobanteResponse con ítems.
    """
    from fastapi import HTTPException

    comprobante = await service._repo.get_comprobante_by_id(comprobante_id)
    if comprobante is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado",
        )
    return ComprobanteResponse.model_validate(comprobante)


@router.patch("/comprobantes/{comprobante_id}", response_model=ComprobanteResponse)
async def actualizar_comprobante(
    comprobante_id: uuid.UUID,
    body: ComprobanteUpdate,
    service: FacturacionService = Depends(_get_service),
    _: Usuario = Depends(require_role("recepcion", "admin")),
) -> ComprobanteResponse:
    """Actualiza parcialmente un comprobante (estado, notas, pdf_url).

    Args:
        comprobante_id: UUID del comprobante.
        body: Campos a actualizar.

    Returns:
        ComprobanteResponse actualizado.
    """
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    comprobante = await service._repo.update_comprobante(comprobante_id, update_data)
    if comprobante is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado",
        )
    return ComprobanteResponse.model_validate(comprobante)


@router.post("/comprobantes/{comprobante_id}/pagar", response_model=ComprobanteResponse)
async def pagar_comprobante(
    comprobante_id: uuid.UUID,
    service: FacturacionService = Depends(_get_service),
    _: Usuario = Depends(require_role("recepcion", "admin")),
) -> ComprobanteResponse:
    """Marca un comprobante como pagado.

    Args:
        comprobante_id: UUID del comprobante.

    Returns:
        ComprobanteResponse en estado 'pagado'.
    """
    comprobante = await service.marcar_pagado(comprobante_id)
    return ComprobanteResponse.model_validate(comprobante)


# ─── Resumen ──────────────────────────────────────────────────────────────────


@router.get("/resumen", response_model=ResumenFacturacionResponse)
async def obtener_resumen(
    fecha_desde: Optional[datetime] = Query(default=None),
    fecha_hasta: Optional[datetime] = Query(default=None),
    service: FacturacionService = Depends(_get_service),
    _: Usuario = Depends(require_role("recepcion", "admin")),
) -> ResumenFacturacionResponse:
    """Calcula el resumen de facturación para un período.

    Si no se especifican fechas, devuelve el resumen del día actual.

    Args:
        fecha_desde: Inicio del período.
        fecha_hasta: Fin del período.

    Returns:
        ResumenFacturacionResponse con totales y desglose por obra social.
    """
    if fecha_desde is None or fecha_hasta is None:
        return await service.obtener_resumen_diario()

    data = await service._repo.get_resumen(fecha_desde, fecha_hasta)
    return ResumenFacturacionResponse(**data)
