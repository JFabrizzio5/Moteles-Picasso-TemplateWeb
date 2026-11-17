"""Piezas compartidas del módulo finanzas: fechas del negocio y comprobantes."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, date, datetime
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from jfastframework.errors import ValidationError

from ..enums import TipoArchivo

ZONA = ZoneInfo("America/Mexico_City")

#: Tipo de contenido → (tipo de comprobante, extensión).
TIPOS_COMPROBANTE: dict[str, tuple[TipoArchivo, str]] = {
    "image/jpeg": (TipoArchivo.FOTO, "jpg"),
    "image/png": (TipoArchivo.FOTO, "png"),
    "image/webp": (TipoArchivo.FOTO, "webp"),
    "application/pdf": (TipoArchivo.PDF, "pdf"),
    "text/xml": (TipoArchivo.XML, "xml"),
    "application/xml": (TipoArchivo.XML, "xml"),
}
MAX_COMPROBANTE = 8 * 1024 * 1024
VIGENCIA_LIGA = 2 * 60 * 60

_UUID_CFDI = re.compile(rb'UUID\s*=\s*"([0-9A-Fa-f-]{36})"')


def ahora() -> datetime:
    return datetime.now(UTC)


def hoy() -> date:
    return ahora().astimezone(ZONA).date()


def tipo_de(nombre: str, contenido: str | None) -> tuple[TipoArchivo, str]:
    """El navegador no siempre manda el tipo del XML: se mira la extensión también."""
    tipo = (contenido or "").split(";")[0].strip().lower()
    if tipo in TIPOS_COMPROBANTE:
        return TIPOS_COMPROBANTE[tipo]
    extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    if extension == "xml":
        return TipoArchivo.XML, "xml"
    if extension == "pdf":
        return TipoArchivo.PDF, "pdf"
    raise ValidationError(
        "El comprobante debe ser foto (JPG, PNG, WebP), PDF o el XML de la factura."
    )


def uuid_de_cfdi(datos: bytes) -> str | None:
    """El folio fiscal del timbre (TimbreFiscalDigital), si el XML es un CFDI."""
    m = _UUID_CFDI.search(datos)
    return m.group(1).decode().upper() if m else None


class Disco(Protocol):
    async def put(self, key: str, data: bytes, **kwargs: Any) -> Any: ...
    async def get(self, key: str) -> bytes: ...
    async def temporary_url(self, key: str, *, expires_in: int = 300) -> str: ...


class Comprobantes:
    """Van al disco privado, como las fotos de los folios."""

    def __init__(self, disco: Disco) -> None:
        self.disco = disco

    async def guardar(
        self, datos: bytes, nombre: str, contenido: str | None
    ) -> tuple[TipoArchivo, str]:
        tipo, extension = tipo_de(nombre, contenido)
        if not datos:
            raise ValidationError("El archivo llegó vacío.")
        if len(datos) > MAX_COMPROBANTE:
            raise ValidationError("El comprobante pesa más de 8 MB.")
        if tipo is TipoArchivo.XML and b"<" not in datos[:200]:
            raise ValidationError("Ese archivo no parece un XML.")
        momento = ahora()
        llave = f"gastos/{momento:%Y/%m}/{uuid.uuid4().hex}.{extension}"
        await self.disco.put(llave, datos, content_type=contenido or f"application/{extension}")
        return tipo, llave

    async def leer(self, llave: str) -> bytes | None:
        try:
            return await self.disco.get(llave)
        except Exception:
            return None

    async def liga(self, llave: str) -> str:
        return await self.disco.temporary_url(llave, expires_in=VIGENCIA_LIGA)
