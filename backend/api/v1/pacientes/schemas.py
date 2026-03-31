"""Schemas Pydantic para pacientes e historia clínica."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr


# ─── Paciente ────────────────────────────────────────────────────────────────

class PacienteCreate(BaseModel):
    """Datos necesarios para registrar un nuevo paciente."""

    numero_historia: str
    nombre: str
    apellido: str
    fecha_nacimiento: date
    dni: str
    telefono: str
    email: EmailStr | None = None
    obra_social: str | None = None


class PacienteUpdate(BaseModel):
    """Campos actualizables de un paciente. Todos son opcionales."""

    nombre: str | None = None
    apellido: str | None = None
    fecha_nacimiento: date | None = None
    telefono: str | None = None
    email: EmailStr | None = None
    obra_social: str | None = None
    activo: bool | None = None


class PacienteResponse(BaseModel):
    """Representación pública de un paciente."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    numero_historia: str
    nombre: str
    apellido: str
    fecha_nacimiento: date
    dni: str
    telefono: str
    email: str | None
    obra_social: str | None
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Episodio ─────────────────────────────────────────────────────────────────

class EpisodioCreate(BaseModel):
    """Datos para crear un nuevo episodio de historia clínica."""

    turno_id: uuid.UUID | None = None
    medico_id: uuid.UUID
    motivo_consulta: str
    anamnesis: str | None = None
    examen_fisico: str | None = None
    diagnostico: str | None = None
    plan_terapeutico: str | None = None
    soap_subjetivo: str | None = None
    soap_objetivo: str | None = None
    soap_assessment: str | None = None
    soap_plan: str | None = None
    transcripcion_raw: str | None = None


class EpisodioResponse(BaseModel):
    """Representación pública de un episodio clínico."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    paciente_id: uuid.UUID
    turno_id: uuid.UUID | None
    medico_id: uuid.UUID
    fecha: datetime
    motivo_consulta: str
    anamnesis: str | None
    examen_fisico: str | None
    diagnostico: str | None
    plan_terapeutico: str | None
    soap_subjetivo: str | None
    soap_objetivo: str | None
    soap_assessment: str | None
    soap_plan: str | None
    transcripcion_raw: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
