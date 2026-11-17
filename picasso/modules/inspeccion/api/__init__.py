"""HTTP del módulo inspeccion: las rutas JSON y las descargas PDF."""

from __future__ import annotations

from fastapi import APIRouter

from .pdf_routes import router as pdf_router
from .routes import router as rutas_router

router = APIRouter()
router.include_router(rutas_router)
router.include_router(pdf_router)

__all__ = ["router"]
