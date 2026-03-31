"""Servicio de lógica de negocio para el módulo de Facturación (MOD_05)."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.facturacion.repository_facturacion import FacturacionRepository
from api.v1.facturacion.schemas import (
    ComprobanteCreate,
    ObraSocialCreate,
    ResumenFacturacionResponse,
)
from core.logging import get_logger
from models.facturacion import Comprobante, ItemComprobante, ObraSocial

logger = get_logger(__name__)


class FacturacionService:
    """Orquesta la lógica de negocio del módulo de Facturación."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        """Inicializa el servicio con sesión y tenant.

        Args:
            db: Sesión async de SQLAlchemy.
            tenant_id: UUID del tenant actual.
        """
        self._repo = FacturacionRepository(db=db, tenant_id=tenant_id)
        self._tenant_id = tenant_id

    async def listar_obras_sociales(self) -> list[ObraSocial]:
        """Lista todas las obras sociales activas del tenant.

        Returns:
            Lista de ObraSocial activas ordenadas por nombre.
        """
        return await self._repo.get_obras_sociales(activa=True)

    async def crear_obra_social(self, data: ObraSocialCreate) -> ObraSocial:
        """Registra una nueva obra social para el tenant.

        Args:
            data: Datos de la obra social a crear.

        Returns:
            ObraSocial creada.
        """
        obra_social = await self._repo.create_obra_social(data)
        logger.info(
            "Obra social creada",
            extra={"obra_social_id": str(obra_social.id)},
        )
        return obra_social

    async def crear_comprobante(self, data: ComprobanteCreate) -> Comprobante:
        """Crea un nuevo comprobante de facturación con sus ítems.

        Calcula automáticamente los montos en función de la obra social:
        - Con OS: monto_cobertura = total * (porcentaje / 100), monto_copago = copago_fijo
        - Sin OS: monto_particular = total, cobertura y copago en 0

        Args:
            data: Datos del comprobante y sus ítems.

        Returns:
            Comprobante persistido con número generado.

        Raises:
            HTTPException 404: Si la obra social indicada no existe.
        """
        obra_social: ObraSocial | None = None
        if data.obra_social_id is not None:
            obra_social = await self._repo.get_obra_social_by_id(data.obra_social_id)
            if obra_social is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Obra social no encontrada",
                )

        # Calcular monto total a partir de los ítems
        monto_total: float = sum(
            item.cantidad * item.precio_unitario for item in data.items
        )

        # Calcular distribución de montos
        if obra_social is not None:
            monto_cobertura = monto_total * (obra_social.porcentaje_cobertura / 100.0)
            monto_copago = obra_social.copago_consulta
            monto_particular = 0.0
        else:
            monto_cobertura = 0.0
            monto_copago = 0.0
            monto_particular = monto_total

        # Generar número de comprobante correlativo
        numero_comprobante = await self._repo.get_siguiente_numero(data.tipo)

        # Construir los ítems
        items = [
            ItemComprobante(
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                subtotal=round(item.cantidad * item.precio_unitario, 2),
            )
            for item in data.items
        ]

        # Construir el comprobante
        comprobante = Comprobante(
            tenant_id=self._tenant_id,
            turno_id=data.turno_id,
            paciente_id=data.paciente_id,
            obra_social_id=data.obra_social_id,
            numero_comprobante=numero_comprobante,
            tipo=data.tipo,
            monto_total=round(monto_total, 2),
            monto_cobertura=round(monto_cobertura, 2),
            monto_copago=round(monto_copago, 2),
            monto_particular=round(monto_particular, 2),
            estado="pendiente",
            concepto=data.concepto,
            notas=data.notas,
            items=items,
        )

        persistido = await self._repo.create_comprobante(comprobante)
        logger.info(
            "Comprobante creado",
            extra={"comprobante_id": str(persistido.id)},
        )
        return persistido

    async def actualizar_estado(self, comprobante_id: uuid.UUID, estado: str) -> Comprobante:
        """Actualiza el estado de un comprobante existente.

        Args:
            comprobante_id: UUID del comprobante.
            estado: Nuevo estado (pendiente, pagado, cancelado, anulado).

        Returns:
            Comprobante con estado actualizado.

        Raises:
            HTTPException 404: Si el comprobante no existe.
        """
        comprobante = await self._repo.update_comprobante(
            comprobante_id, {"estado": estado}
        )
        if comprobante is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comprobante no encontrado",
            )
        logger.info(
            "Estado de comprobante actualizado",
            extra={"comprobante_id": str(comprobante_id), "nuevo_estado": estado},
        )
        return comprobante

    async def marcar_pagado(self, comprobante_id: uuid.UUID) -> Comprobante:
        """Marca un comprobante como pagado.

        Args:
            comprobante_id: UUID del comprobante.

        Returns:
            Comprobante en estado 'pagado'.

        Raises:
            HTTPException 404: Si el comprobante no existe.
        """
        return await self.actualizar_estado(comprobante_id, "pagado")

    async def obtener_resumen_diario(self) -> ResumenFacturacionResponse:
        """Calcula el resumen de facturación del día en curso.

        Returns:
            ResumenFacturacionResponse con totales del día.
        """
        hoy = datetime.now(tz=timezone.utc)
        fecha_desde = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_hasta = hoy.replace(hour=23, minute=59, second=59, microsecond=999999)
        data = await self._repo.get_resumen(fecha_desde, fecha_hasta)
        return ResumenFacturacionResponse(**data)
