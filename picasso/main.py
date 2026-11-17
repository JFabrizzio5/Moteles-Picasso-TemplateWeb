"""Picasso service entry point.

Everything this service does beyond routing -- logging, metrics, database,
error shape, health probes -- arrives through the plugin graph in jfast.toml.
Add a module with `jfast new module <name>`; it registers itself below.
"""

from __future__ import annotations

from fastapi import APIRouter

from jfastframework import create_app

# `jfast new module <name>` adds its import here, in sorted order, and its
# router to the list below. Keep both markers: they are where the next module
# goes, and without them the generator refuses rather than guessing a line.
from modules.inspeccion import router as inspeccion_router
from modules.sucursal import router as sucursal_router

# [jfast:imports]

ROUTERS: list[APIRouter] = [
    sucursal_router,
    inspeccion_router,
    # [jfast:routers]
]

app = create_app(routers=ROUTERS)
