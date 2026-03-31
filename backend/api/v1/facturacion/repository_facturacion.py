"""Repositorio de acceso a datos para el módulo de Facturación (MOD_05)."""

import uuid
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.v1.facturacion.schemas import ObraSocialCreate
from core.logging import get_logger
from models.facturacion import Comprobante, ItemComprobante, ObraSocial

logger = get_logger(__name__)

_TIPO_PREFIJOS: dict[str, str] = {
    "factura_a": "FCTA",
    "factura_b": "FCTB",
    "recibo": "REC",
    "orden": "ORD",
}


class FacturacionRepository:
    """Gestiona el acceso a datos de las entidades de facturación.

    Todos los métodos filtran por ``tenant_id`` para garantizar aislamiento multi-tenant.
    """

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        """Inicializa el repositorio con sesión y tenant.

        Args:
            db: Sesión async de SQLAlchemy.
            tenant_id: UUID del tenant actual.
        """
        self._db = db
        self._tenant_id = tenant_id

    async def get_obras_sociales(self, activa: bool = True) -> list[ObraSocial]:
        """Obtiene todas las obras sociales del tenant.

        Args:
            activa: Si True, filtra solo las activas.

        Returns:
            Lista de ObraSocial ordenadas por nombre.
        """
        stmt = select(ObraSocial).where(
            and_(
                ObraSocial.tenant_id == self._tenant_id,
                ObraSocial.activa.is_(activa),
            )
        ).order_by(ObraSocial.nombre)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_obra_social_by_id(self, obra_social_id: uuid.UUID) -> ObraSocial | None:
        """Obtiene una obra social por su UUID dentro del tenant.

        Args:
            obra_social_id: UUID de la obra social.

        Returns:
            ObraSocial encontrada o None.
        """
        result = await self._db.execute(
            select(ObraSocial).where(
                and_(
                    ObraSocial.id == obra_social_id,
                    ObraSocial.tenant_id == self._tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_obra_social(self, data: ObraSocialCreate) -> ObraSocial:
        """Crea una nueva obra social para el tenant.

        Args:
            data: Datos de la obra social a crear.

        Returns:
            ObraSocial creada con ID asignado.
        """
        obra_social = ObraSocial(
            **data.model_dump(),
            tenant_id=self._tenant_id,
        )
        self._db.add(obra_social)
        await self._db.flush()
        await self._db.refresh(obra_social)
        return obra_social

    async def get_comprobantes(
        self,
        paciente_id: uuid.UUID | None,
        estado: str | None,
        limit: int,
        offset: int,
    ) -> list[Comprobante]:
        """Lista comprobantes del tenant con filtros opcionales.

        Args:
            paciente_id: Filtra por paciente si se especifica.
            estado: Filtra por estado si se especifica.
            limit: Máximo de resultados.
            offset: Desplazamiento para paginación.

        Returns:
            Lista de Comprobante ordenados por fecha descendente.
        """
        filters = [Comprobante.tenant_id == self._tenant_id]
        if paciente_id is not None:
            filters.append(Comprobante.paciente_id == paciente_id)
        if estado is not None:
            filters.append(Comprobante.estado == estado)

        stmt = (
            select(Comprobante)
            .where(and_(*filters))
            .order_by(Comprobante.fecha_emision.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_comprobante_by_id(self, comprobante_id: uuid.UUID) -> Comprobante | None:
        """Obtiene un comprobante por su UUID con eager load de ítems.

        Args:
            comprobante_id: UUID del comprobante.

        Returns:
            Comprobante con sus ítems cargados, o None.
        """
        result = await self._db.execute(
            select(Comprobante)
            .options(selectinload(Comprobante.items))
            .where(
                and_(
                    Comprobante.id == comprobante_id,
                    Comprobante.tenant_id == self._tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_comprobante(self, comprobante: Comprobante) -> Comprobante:
        """Persiste un comprobante ya construido (con sus ítems).

        Args:
            comprobante: Instancia de Comprobante con ítems adjuntados.

        Returns:
            Comprobante persistido con ID asignado.
        """
        self._db.add(comprobante)
        await self._db.flush()
        # Recarga con ítems incluidos
        result = await self._db.execute(
            select(Comprobante)
            .options(selectinload(Comprobante.items))
            .where(Comprobante.id == comprobante.id)
        )
        refreshed = result.scalar_one()
        return refreshed

    async def update_comprobante(
        self, comprobante_id: uuid.UUID, data: dict
    ) -> Comprobante | None:
        """Actualiza campos de un comprobante existente.

        Args:
            comprobante_id: UUID del comprobante.
            data: Diccionario con campos a actualizar.

        Returns:
            Comprobante actualizado con ítems, o None si no existe.
        """
        comprobante = await self.get_comprobante_by_id(comprobante_id)
        if comprobante is None:
            return None
        for field, value in data.items():
            setattr(comprobante, field, value)
        await self._db.flush()
        result = await self._db.execute(
            select(Comprobante)
            .options(selectinload(Comprobante.items))
            .where(Comprobante.id == comprobante_id)
        )
        return result.scalar_one()

    async def get_siguiente_numero(self, tipo: str) -> str:
        """Genera el próximo número correlativo para el tipo de comprobante.

        El formato es: ``{PREFIJO}-{N:06d}`` ej: ``REC-000001``.

        Args:
            tipo: Tipo de comprobante (factura_a, factura_b, recibo, orden).

        Returns:
            Número de comprobante formateado.
        """
        prefijo = _TIPO_PREFIJOS.get(tipo, "DOC")
        # Cuenta los comprobantes existentes del mismo tenant y tipo
        result = await self._db.execute(
            select(func.count(Comprobante.id)).where(
                and_(
                    Comprobante.tenant_id == self._tenant_id,
                    Comprobante.tipo == tipo,
                )
            )
        )
        count: int = result.scalar_one() or 0
        return f"{prefijo}-{count + 1:06d}"

    async def get_resumen(
        self, fecha_desde: datetime, fecha_hasta: datetime
    ) -> dict:
        """Calcula el resumen de facturación para un período dado.

        Args:
            fecha_desde: Inicio del período (inclusive).
            fecha_hasta: Fin del período (inclusive).

        Returns:
            Diccionario con totales y desglose por obra social.
        """
        base_filter = and_(
            Comprobante.tenant_id == self._tenant_id,
            Comprobante.fecha_emision >= fecha_desde,
            Comprobante.fecha_emision <= fecha_hasta,
        )

        # Total de comprobantes y monto global
        total_result = await self._db.execute(
            select(
                func.count(Comprobante.id),
                func.coalesce(func.sum(Comprobante.monto_total), 0.0),
            ).where(base_filter)
        )
        total_row = total_result.one()
        total_comprobantes: int = total_row[0]
        monto_total: float = float(total_row[1])

        # Monto cobrado (pagado)
        pagado_result = await self._db.execute(
            select(func.coalesce(func.sum(Comprobante.monto_total), 0.0)).where(
                and_(base_filter, Comprobante.estado == "pagado")
            )
        )
        monto_cobrado: float = float(pagado_result.scalar_one())

        # Monto pendiente
        pendiente_result = await self._db.execute(
            select(func.coalesce(func.sum(Comprobante.monto_total), 0.0)).where(
                and_(base_filter, Comprobante.estado == "pendiente")
            )
        )
        monto_pendiente: float = float(pendiente_result.scalar_one())

        # Desglose por obra social
        os_result = await self._db.execute(
            select(
                ObraSocial.nombre,
                func.count(Comprobante.id),
                func.coalesce(func.sum(Comprobante.monto_total), 0.0),
            )
            .join(ObraSocial, Comprobante.obra_social_id == ObraSocial.id, isouter=True)
            .where(base_filter)
            .group_by(ObraSocial.nombre)
        )
        por_obra_social = [
            {"nombre": row[0] or "Particular", "cantidad": row[1], "monto": float(row[2])}
            for row in os_result.all()
        ]

        return {
            "total_comprobantes": total_comprobantes,
            "monto_total": monto_total,
            "monto_cobrado": monto_cobrado,
            "monto_pendiente": monto_pendiente,
            "por_obra_social": por_obra_social,
        }
