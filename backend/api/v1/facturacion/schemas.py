"""Schemas Pydantic para el módulo de Facturación (MOD_05)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ObraSocialCreate(BaseModel):
    """Schema para crear una obra social."""

    nombre: str
    codigo: str
    plan: Optional[str] = None
    porcentaje_cobertura: float = Field(ge=0, le=100, default=0.0)
    copago_consulta: float = Field(ge=0, default=0.0)
    notas: Optional[str] = None


class ObraSocialResponse(ObraSocialCreate):
    """Schema de respuesta para una obra social."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    activa: bool
    created_at: datetime


class ItemComprobanteCreate(BaseModel):
    """Schema para crear un ítem de comprobante."""

    descripcion: str
    cantidad: float = Field(gt=0, default=1.0)
    precio_unitario: float = Field(ge=0)


class ItemComprobanteResponse(ItemComprobanteCreate):
    """Schema de respuesta para un ítem de comprobante."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subtotal: float


class ComprobanteCreate(BaseModel):
    """Schema para crear un comprobante de facturación."""

    turno_id: Optional[UUID] = None
    paciente_id: UUID
    obra_social_id: Optional[UUID] = None
    tipo: str = Field(default="recibo", pattern="^(factura_a|factura_b|recibo|orden)$")
    concepto: str
    items: list[ItemComprobanteCreate]
    notas: Optional[str] = None


class ComprobanteResponse(BaseModel):
    """Schema de respuesta completo para un comprobante."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    turno_id: Optional[UUID]
    paciente_id: UUID
    obra_social_id: Optional[UUID]
    numero_comprobante: str
    tipo: str
    fecha_emision: datetime
    monto_total: float
    monto_cobertura: float
    monto_copago: float
    monto_particular: float
    estado: str
    concepto: str
    notas: Optional[str]
    pdf_url: Optional[str]
    items: list[ItemComprobanteResponse] = []


class ComprobanteUpdate(BaseModel):
    """Schema para actualización parcial de un comprobante."""

    estado: Optional[str] = Field(None, pattern="^(pendiente|pagado|cancelado|anulado)$")
    notas: Optional[str] = None
    pdf_url: Optional[str] = None


class ResumenFacturacionResponse(BaseModel):
    """Resumen de facturación del día o período."""

    total_comprobantes: int
    monto_total: float
    monto_cobrado: float  # estado=pagado
    monto_pendiente: float  # estado=pendiente
    por_obra_social: list[dict]  # [{nombre, cantidad, monto}]
