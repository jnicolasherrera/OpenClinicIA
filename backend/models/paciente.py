"""Modelo de Paciente."""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import TimestampMixin, UUIDMixin


class Paciente(UUIDMixin, TimestampMixin, Base):
    """Representa a un paciente registrado en la clínica."""

    __tablename__ = "pacientes"

    __table_args__ = (
        Index("ix_pacientes_tenant_dni", "tenant_id", "dni"),
        Index("ix_pacientes_tenant_historia", "tenant_id", "numero_historia"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    numero_historia: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha_nacimiento: Mapped[date] = mapped_column(Date, nullable=False)
    dni: Mapped[str] = mapped_column(String(20), nullable=False)
    telefono: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    obra_social: Mapped[str | None] = mapped_column(String(100), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relaciones
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="pacientes", lazy="noload")  # type: ignore[name-defined]  # noqa: F821
    turnos: Mapped[list["Turno"]] = relationship("Turno", back_populates="paciente", lazy="noload")  # type: ignore[name-defined]  # noqa: F821
    episodios: Mapped[list["Episodio"]] = relationship("Episodio", back_populates="paciente", lazy="noload")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Paciente id={self.id}>"
