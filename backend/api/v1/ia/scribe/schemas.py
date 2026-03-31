"""Schemas Pydantic para el módulo de scribe (documentación clínica con IA)."""

from pydantic import BaseModel, model_validator


class ScribeRequest(BaseModel):
    """Solicitud de generación de nota SOAP.

    Al menos uno de ``audio_url`` o ``transcripcion_texto`` debe estar presente.
    """

    audio_url: str | None = None
    transcripcion_texto: str | None = None
    contexto_paciente: str | None = None

    @model_validator(mode="after")
    def validate_input(self) -> "ScribeRequest":
        """Valida que al menos una fuente de entrada esté presente.

        Returns:
            La instancia validada.

        Raises:
            ValueError: Si ni audio_url ni transcripcion_texto están presentes.
        """
        if not self.audio_url and not self.transcripcion_texto:
            raise ValueError(
                "Debe proveer al menos 'audio_url' o 'transcripcion_texto'"
            )
        return self


class SOAPResponse(BaseModel):
    """Nota clínica en formato SOAP generada por IA."""

    subjetivo: str
    objetivo: str
    assessment: str
    plan: str
    resumen_clinico: str


class TranscripcionTaskResponse(BaseModel):
    """Respuesta al enqueue de una tarea de transcripción."""

    task_id: str
    status: str = "queued"
    message: str = "Transcripción encolada correctamente"
