"""Modelo de Usuario del sistema."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import TimestampMixin, UUIDMixin

ROLES_VALIDOS = ("medico", "recepcion", "admin", "paciente")


class Usuario(UUIDMixin, TimestampMixin, Base):
    """Usuario autenticado asociado a un tenant.

    El campo ``rol`` determina los permisos dentro del sistema.
    Los valores permitidos son: medico, recepcion, admin, paciente.
    """

    __tablename__ = "usuarios"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False, default="recepcion")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relaciones
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="usuarios", lazy="noload")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Usuario id={self.id} rol={self.rol!r}>"
