"""Configuración de logging estructurado para OpenClinicIA.

Todos los logs se emiten en formato JSON. Ningún log debe contener PII directamente;
usar tokens como [PACIENTE_{id}] o [TRIAJE_{id}].
"""

import logging
import sys
from typing import Any


class JSONFormatter(logging.Formatter):
    """Formateador que emite líneas JSON con campos estándar."""

    def format(self, record: logging.LogRecord) -> str:
        """Formatea un LogRecord como cadena JSON."""
        import json
        import datetime

        log_object: dict[str, Any] = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_object["exc_info"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            log_object.update(record.extra)  # type: ignore[arg-type]
        return json.dumps(log_object, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Configura el sistema de logging global de la aplicación.

    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if root_logger.handlers:
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Silenciar loggers ruidosos de librerías externas
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


_SENSITIVE_FIELDS = frozenset(
    {
        "password",
        "hashed_password",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "api_key",
        "nombre",
        "apellido",
        "email",
        "dni",
        "telefono",
        "fecha_nacimiento",
    }
)


def sanitize_log_data(data: dict[str, Any]) -> dict[str, Any]:
    """Elimina o enmascara campos sensibles de un diccionario antes de loguearlo.

    Los campos en _SENSITIVE_FIELDS son reemplazados por '***REDACTED***'.
    Los valores de tipo dict son procesados recursivamente.

    Args:
        data: Diccionario original con posible PII.

    Returns:
        Copia del diccionario con campos sensibles enmascarados.
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        if key.lower() in _SENSITIVE_FIELDS:
            result[key] = "***REDACTED***"
        elif isinstance(value, dict):
            result[key] = sanitize_log_data(value)
        else:
            result[key] = value
    return result


def get_logger(name: str) -> logging.Logger:
    """Retorna un logger configurado con el nombre dado.

    Args:
        name: Nombre del logger (típicamente __name__).

    Returns:
        Logger listo para usar.
    """
    return logging.getLogger(name)
