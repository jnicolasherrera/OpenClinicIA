"""Schemas Pydantic para el módulo de scribe (documentación clínica con IA)."""

from typing import Optional

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


class TranscripcionRequest(BaseModel):
    """Solicitud de transcripción de audio."""

    audio_url: Optional[str] = None
    episodio_id: Optional[str] = None
    contexto: Optional[str] = None


class TranscripcionResponse(BaseModel):
    """Respuesta de una solicitud de transcripción."""

    task_id: Optional[str] = None
    transcripcion: Optional[str] = None
    estado: str  # "completado", "procesando", "error"
    mensaje: Optional[str] = None


class PipelineScribeRequest(BaseModel):
    """Request para el pipeline completo: audio → transcripción → SOAP."""

    audio_url: Optional[str] = None
    transcripcion_texto: Optional[str] = None
    episodio_id: str
    contexto_paciente: Optional[str] = None
    ejecutar_async: bool = False  # True = Celery task, False = sync


class PipelineScribeResponse(BaseModel):
    """Respuesta del pipeline completo de scribe."""

    task_id: Optional[str] = None  # presente si ejecutar_async=True
    transcripcion: Optional[str] = None
    soap: Optional[SOAPResponse] = None  # presente si completado
    estado: str
