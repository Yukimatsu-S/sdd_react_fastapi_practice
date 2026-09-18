"""Versioned API router composed from independently testable route modules."""

from fastapi import APIRouter

from app.api.routes.evolution_steps import router as evolution_steps_router
from app.api.routes.runs import router as runs_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(evolution_steps_router)
api_router.include_router(runs_router)
