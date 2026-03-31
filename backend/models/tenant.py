"""Modelo de Tenant (organización/clínica)."""

import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import TimestampMixin, UUIDMixin


class Tenant(UUIDMixin, TimestampMixin, Base):
    """Representa una organización o clínica dentro del sistema multi-tenant."""

    __tablename__ = "tenants"

    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="basic")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relaciones
    usuarios: Mapped[list["Usuario"]] = relationship("Usuario", back_populates="tenant", lazy="noload")  # type: ignore[name-defined]  # noqa: F821
    pacientes: Mapped[list["Paciente"]] = relationship("Paciente", back_populates="tenant", lazy="noload")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} slug={self.slug!r}>"
