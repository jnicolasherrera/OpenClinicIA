"""Modelos SQLAlchemy para el módulo de Facturación (MOD_05)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDMixin


class ObraSocial(UUIDMixin, TimestampMixin, Base):
    """Representa una obra social o prepaga registrada para el tenant."""

    __tablename__ = "obras_sociales"

    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo", name="uq_obras_sociales_tenant_codigo"),
        Index("ix_obras_sociales_tenant_activa", "tenant_id", "activa"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    plan: Mapped[str | None] = mapped_column(String(100), nullable=True)
    porcentaje_cobertura: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    copago_consulta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relaciones
    comprobantes: Mapped[list["Comprobante"]] = relationship(
        "Comprobante", back_populates="obra_social", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<ObraSocial id={self.id} codigo={self.codigo!r}>"


class Comprobante(UUIDMixin, TimestampMixin, Base):
    """Representa un comprobante de facturación (factura, recibo u orden)."""

    __tablename__ = "comprobantes"

    __table_args__ = (
        UniqueConstraint("tenant_id", "numero_comprobante", name="uq_comprobantes_tenant_numero"),
        Index("ix_comprobantes_paciente_fecha", "paciente_id", "fecha_emision"),
        Index("ix_comprobantes_tenant_estado", "tenant_id", "estado"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    turno_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("turnos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    paciente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pacientes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    obra_social_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("obras_sociales.id", ondelete="SET NULL"),
        nullable=True,
    )
    numero_comprobante: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default="recibo")
    fecha_emision: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    monto_total: Mapped[float] = mapped_column(Float, nullable=False)
    monto_cobertura: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    monto_copago: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    monto_particular: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="pendiente")
    concepto: Mapped[str] = mapped_column(String(500), nullable=False)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relaciones
    obra_social: Mapped["ObraSocial | None"] = relationship(
        "ObraSocial", back_populates="comprobantes", lazy="noload"
    )
    items: Mapped[list["ItemComprobante"]] = relationship(
        "ItemComprobante",
        back_populates="comprobante",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Comprobante id={self.id} numero={self.numero_comprobante!r}>"


class ItemComprobante(UUIDMixin, Base):
    """Ítem de línea de un comprobante de facturación."""

    __tablename__ = "items_comprobante"

    comprobante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comprobantes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    descripcion: Mapped[str] = mapped_column(String(300), nullable=False)
    cantidad: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    precio_unitario: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    # Relaciones
    comprobante: Mapped["Comprobante"] = relationship(
        "Comprobante", back_populates="items", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<ItemComprobante id={self.id} comprobante_id={self.comprobante_id}>"
