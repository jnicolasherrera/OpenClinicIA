"""Router principal de la API v1."""

from fastapi import APIRouter

from api.v1.agenda.router import router as agenda_router
from api.v1.auth.router import router as auth_router
from api.v1.ia.scribe.router import router as scribe_router
from api.v1.ia.triaje.router import router as triaje_router
from api.v1.pacientes.router import router as pacientes_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(agenda_router)
api_v1_router.include_router(pacientes_router)
api_v1_router.include_router(triaje_router)
api_v1_router.include_router(scribe_router)
