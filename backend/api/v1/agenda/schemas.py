"""Schemas Pydantic para el módulo de agenda."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TurnoCreate(BaseModel):
    """Datos necesarios para crear un turno."""

    paciente_id: uuid.UUID
    medico_id: uuid.UUID
    fecha_hora: datetime
    duracion_minutos: int = Field(default=30, ge=5, le=480)
    motivo: str | None = None


class TurnoUpdate(BaseModel):
    """Campos actualizables de un turno. Todos son opcionales."""

    estado: str | None = None
    notas: str | None = None
    motivo: str | None = None
    duracion_minutos: int | None = Field(default=None, ge=5, le=480)


class TurnoResponse(BaseModel):
    """Representación completa de un turno incluyendo datos relacionados."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    paciente_id: uuid.UUID
    medico_id: uuid.UUID
    fecha_hora: datetime
    duracion_minutos: int
    estado: str
    motivo: str | None
    notas: str | None
    sala_espera_ingreso: datetime | None
    created_at: datetime
    updated_at: datetime

    # Campos calculados / desnormalizados
    paciente_nombre: str | None = None
    medico_nombre: str | None = None

    model_config = {"from_attributes": True}


class SalaEsperaItem(BaseModel):
    """Item de la lista de sala de espera."""

    turno_id: uuid.UUID
    paciente_nombre: str
    medico_nombre: str
    hora_turno: datetime
    estado: str
    tiempo_espera_minutos: int | None
