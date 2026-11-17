"""Cliente HTTP para el Kairos de un motel.

Entra como lo hace la vista móvil (formulario de LoginMobil) y pide lo mismo
que pide esa pantalla. Solo lee: nunca llama a las acciones que escriben
(ActualizaInventario, ActualizaPassword).

Kairos corre en una PC de cada motel, por HTTP y detrás de su internet: las
pausas entre peticiones son para no cargarle la línea al motel.
"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import date, timedelta
from types import TracebackType

import httpx

from .kairos_html import (
    KairosNoEntendido,
    ResumenDia,
    VentasDia,
    es_pantalla_de_entrada,
    fecha_kairos,
    leer_resumen,
    leer_serie_ventas,
    leer_ventas,
)

#: Usuario y contraseña de Kairos; los mismos en todos los moteles. Solo del
#: entorno (picasso/.env del servidor), nunca del repo.
VAR_USUARIO = "PICASSO_KAIROS_USUARIO"
VAR_CLAVE = "PICASSO_KAIROS_CLAVE"


class KairosError(RuntimeError):
    """No se pudo leer Kairos: sin red, credenciales malas o respuesta rara."""


def credenciales() -> tuple[str, str]:
    usuario = os.environ.get(VAR_USUARIO, "")
    clave = os.environ.get(VAR_CLAVE, "")
    if not usuario or not clave:
        raise KairosError(f"Faltan {VAR_USUARIO} y {VAR_CLAVE} en el entorno del servidor.")
    return usuario, clave


class ClienteKairos:
    def __init__(
        self,
        url_base: str,
        *,
        usuario: str,
        clave: str,
        pausa: float = 0.4,
        timeout: float = 30.0,
        transporte: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.url_base = url_base.rstrip("/")
        self._usuario = usuario
        self._clave = clave
        self.pausa = pausa
        self._http = httpx.AsyncClient(
            base_url=self.url_base,
            timeout=timeout,
            follow_redirects=True,
            transport=transporte,
            headers={"User-Agent": "Picasso-Inspecciones/1.0 (lectura de ingresos)"},
        )
        self._dentro = False

    async def __aenter__(self) -> ClienteKairos:
        return self

    async def __aexit__(
        self, tipo: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        await self._http.aclose()

    # -- sesión -------------------------------------------------------------------

    async def entrar(self) -> None:
        try:
            pagina = await self._http.get("/kairos/Mobil.action")
            pagina.raise_for_status()
            accion = re.search(r'<form[^>]+action="([^"]+)"', pagina.text)
            movil = re.search(r'name="ismovil"[^>]*value="([^"]*)"', pagina.text) or re.search(
                r'value="([^"]*)"[^>]*name="ismovil"', pagina.text
            )
            if accion is None:
                raise KairosError("Kairos no mostró el formulario de entrada.")
            respuesta = await self._http.post(
                accion.group(1),
                data={
                    "ismovil": movil.group(1) if movil else "",
                    "username": self._usuario,
                    "password": self._clave,
                },
            )
            respuesta.raise_for_status()
        except httpx.HTTPError as e:
            raise KairosError(f"Sin respuesta de Kairos ({type(e).__name__}).") from e
        if es_pantalla_de_entrada(respuesta.text):
            raise KairosError("Kairos no aceptó el usuario y la contraseña.")
        self._dentro = True

    async def _get(self, ruta: str, params: dict[str, str]) -> httpx.Response:
        if not self._dentro:
            await self.entrar()
        for intento in range(2):
            await asyncio.sleep(self.pausa)
            try:
                r = await self._http.get(f"/kairos/mobil/{ruta}", params=params)
                r.raise_for_status()
            except httpx.HTTPError as e:
                raise KairosError(f"Kairos no respondió {ruta} ({type(e).__name__}).") from e
            if "json" not in r.headers.get("content-type", "") and es_pantalla_de_entrada(r.text):
                # Se venció la sesión: una vez más tras volver a entrar.
                if intento == 0:
                    await self.entrar()
                    continue
                raise KairosError("Kairos pidió entrar de nuevo y no dejó.")
            return r
        raise KairosError("Kairos pidió entrar de nuevo y no dejó.")

    # -- lecturas -----------------------------------------------------------------

    async def resumen(self, dia: date) -> ResumenDia:
        r = await self._get("ActualizaHome", {"fecha": fecha_kairos(dia)})
        try:
            return leer_resumen(r.text)
        except KairosNoEntendido as e:
            raise KairosError(str(e)) from e

    async def ventas(self, dia: date) -> VentasDia:
        r = await self._get("Ventas", {"fecha": fecha_kairos(dia)})
        try:
            return leer_ventas(r.text)
        except KairosNoEntendido as e:
            raise KairosError(str(e)) from e

    async def rentas_por_dia(self, desde: date, hasta: date) -> dict[date, int]:
        """Cuántas rentas hubo cada día, de la gráfica de ventas (JSON, un año por vuelta)."""
        resultado: dict[date, int] = {}
        inicio = desde
        while inicio <= hasta:
            fin = min(hasta, inicio + timedelta(days=364))
            r = await self._get(
                "UpdateGraphVts",
                {"fecha_inicial": fecha_kairos(inicio), "fecha_final": fecha_kairos(fin)},
            )
            try:
                datos = r.json()
            except ValueError as e:
                raise KairosError("La gráfica de ventas no llegó en JSON.") from e
            try:
                serie = leer_serie_ventas(datos, inicio)
            except KairosNoEntendido as e:
                raise KairosError(str(e)) from e
            resultado.update({d: n for d, n in serie.items() if d <= fin})
            inicio = fin + timedelta(days=1)
        return resultado
