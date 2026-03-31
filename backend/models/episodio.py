"""Modelo de Episodio clínico (historia clínica)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import TimestampMixin, UUIDMixin


class Episodio(UUIDMixin, TimestampMixin, Base):
    """Episodio de historia clínica de un paciente.

    Almacena la información de una consulta médica en formato libre y en
    formato SOAP (Subjetivo, Objetivo, Assessment, Plan).
    """

    __tablename__ = "episodios"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paciente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pacientes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    turno_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("turnos.id", ondelete="SET NULL"),
        nullable=True,
    )
    medico_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Campos de historia clínica
    motivo_consulta: Mapped[str] = mapped_column(String(500), nullable=False)
    anamnesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    examen_fisico: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnostico: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_terapeutico: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Campos SOAP generados por IA
    soap_subjetivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    soap_objetivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    soap_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    soap_plan: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Transcripción cruda
    transcripcion_raw: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relaciones
    paciente: Mapped["Paciente"] = relationship("Paciente", back_populates="episodios", lazy="noload")  # type: ignore[name-defined]  # noqa: F821
    medico: Mapped["Usuario"] = relationship("Usuario", lazy="noload")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Episodio id={self.id}>"
