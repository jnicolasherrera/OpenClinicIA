"""Schemas Pydantic para el módulo de triaje de urgencia."""

from pydantic import BaseModel, Field


class TriajeRequest(BaseModel):
    """Datos clínicos de entrada para evaluar el nivel de urgencia."""

    sintomas: str = Field(..., min_length=5, description="Descripción de los síntomas actuales")
    duracion_sintomas: str = Field(..., description="Cuánto tiempo llevan los síntomas")
    antecedentes: str | None = Field(
        default=None,
        description="Antecedentes clínicos relevantes (alergias, enfermedades crónicas, etc.)",
    )


class TriajeResponse(BaseModel):
    """Resultado de la evaluación de urgencia según escala ESI (1-5)."""

    nivel_urgencia: int = Field(..., ge=1, le=5, description="Nivel ESI: 1 más urgente, 5 menos urgente")
    descripcion: str = Field(..., description="Descripción del nivel de urgencia asignado")
    recomendacion: str = Field(..., description="Acción recomendada para este nivel")
    tiempo_atencion_sugerido_minutos: int = Field(
        ...,
        description="Tiempo máximo sugerido antes de atención médica",
    )
    razonamiento: str = Field(..., description="Justificación clínica de la clasificación")
