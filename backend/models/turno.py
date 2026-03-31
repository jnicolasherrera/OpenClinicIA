"""Modelo de Turno (cita médica)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import TimestampMixin, UUIDMixin

ESTADOS_TURNO = (
    "programado",
    "confirmado",
    "en_sala",
    "en_atencion",
    "completado",
    "cancelado",
    "ausente",
)


class Turno(UUIDMixin, TimestampMixin, Base):
    """Representa un turno (cita) médico agendado."""

    __tablename__ = "turnos"

    __table_args__ = (
        Index("ix_turnos_tenant_fecha_hora", "tenant_id", "fecha_hora"),
        Index("ix_turnos_medico_fecha_hora", "medico_id", "fecha_hora"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    paciente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pacientes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    medico_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duracion_minutos: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="programado")
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notas: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    sala_espera_ingreso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relaciones
    paciente: Mapped["Paciente"] = relationship("Paciente", back_populates="turnos", lazy="noload")  # type: ignore[name-defined]  # noqa: F821
    medico: Mapped["Usuario"] = relationship("Usuario", lazy="noload")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Turno id={self.id} estado={self.estado!r}>"
