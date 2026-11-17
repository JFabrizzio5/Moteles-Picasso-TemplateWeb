"""Datos de ejemplo para enseñar la app. NO son datos reales de Picasso.

Las seis sucursales son las del documento de la dirección. Las habitaciones
(101-112), las amenidades, las personas y todo lo que pasó en las revisiones son
inventados para que los tableros tengan algo que mostrar. Antes de usar la app
en serio: dar de alta las habitaciones reales y el personal real, y vaciar la
base (`docker volume rm picasso_database_data`).

Uso, con la API corriendo en :9800:

    jfast exec -- python scripts/sembrar.py

Cuentas de prueba (todas con la contraseña CONTRASENA de abajo):

    propietario@picasso.mx            propietarios (ve las seis sucursales)
    gerente.<clave>@picasso.mx        gerente de la sucursal (ler, tol, cir, chu, per, vaq)
    ama.<clave>@picasso.mx            ama de llaves de la sucursal
"""

from __future__ import annotations

import asyncio
import io
import os
import random
import sys
from typing import Any

import httpx
from PIL import Image, ImageDraw
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from jfastframework.accounts import AccountsService
from jfastframework.plugins.builtin.database import DatabaseSettings

API = "http://127.0.0.1:9800"
# Igual a VITE_DEMO_CLAVE del front (accesos de demo). Ponla en el entorno al sembrar.
CONTRASENA = os.environ.get("PICASSO_CLAVE_DEMO", "cambia-esta-clave")

SUCURSALES = [
    ("LER", "Picasso Lerma", "/sucursales/lerma.jpg"),
    ("TOL", "Picasso Toluca", "/sucursales/toluca.jpg"),
    ("CIR", "Picasso Circuito", "/sucursales/circuito.jpg"),
    ("CHU", "Picasso Churubusco", "/sucursales/churubusco.jpg"),
    ("PER", "Picasso Periférico", "/sucursales/periferico.jpg"),
    ("VAQ", "Picasso Vaqueritos", "/sucursales/vaqueritos.jpg"),
]

NOMBRES = {
    "LER": ("Laura Méndez", "Rosa Hernández"),
    "TOL": ("Jorge Salinas", "María Torres"),
    "CIR": ("Andrea Ruiz", "Guadalupe Díaz"),
    "CHU": ("Ricardo Peña", "Alicia Romero"),
    "PER": ("Sofía Lozano", "Carmen Vega"),
    "VAQ": ("Héctor Campos", "Isabel Flores"),
}

FALLAS_GERENTE = {
    "G04": "Fuga al abrir la regadera.",
    "G08": "Luminaria de cochera no enciende.",
    "G10": "El aire no enfría; solo ventila.",
    "G17": "Netflix pide iniciar sesión de nuevo.",
    "G18": "Recepción tardó más de un minuto en contestar.",
    "G13": "Plafón con mancha de humedad sobre la cama.",
}
FALLAS_AMA = {
    "A05": "Residuos de jabón en la regadera.",
    "A03": "Falta una toalla de manos.",
    "A15": "Solo hay una botella de agua.",
    "A12": "Bote del baño sin bolsa.",
    "A29": "Cabellos junto al buró con la linterna.",
}

azar = random.Random(20261110)


def foto(etiqueta: str) -> bytes:
    """Una imagen que dice claramente que es de ejemplo."""
    imagen = Image.new("RGB", (960, 720), (62, 56, 54))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rectangle((24, 24, 936, 696), outline=(176, 148, 126), width=3)
    dibujo.text((60, 320), "FOTO DE EJEMPLO", fill=(240, 232, 220), font_size=64)
    dibujo.text((60, 410), etiqueta, fill=(196, 170, 150), font_size=34)
    salida = io.BytesIO()
    imagen.save(salida, "JPEG", quality=70)
    return salida.getvalue()


async def base() -> None:
    dsn = DatabaseSettings().dsn.get_secret_value()
    engine = create_async_engine(dsn)
    async with engine.begin() as conn:
        existentes = (await conn.execute(text("SELECT count(*) FROM sucursales"))).scalar_one()
        if existentes:
            print("Ya hay sucursales; no se vuelve a sembrar. Vacía la base para empezar de cero.")
            sys.exit(0)
        for clave, nombre, foto_url in SUCURSALES:
            sid = (
                await conn.execute(
                    text(
                        "INSERT INTO sucursales (clave, nombre, foto, frecuencia_gerente_dias,"
                        " ama_exigible, activa) VALUES (:c, :n, :f, 1, 'por_limpieza', true)"
                        " RETURNING id"
                    ),
                    {"c": clave, "n": nombre, "f": foto_url},
                )
            ).scalar_one()
            for numero in range(101, 113):
                await conn.execute(
                    text(
                        "INSERT INTO habitaciones (sucursal_id, numero, tiene_jacuzzi,"
                        " tiene_alberca, tiene_sauna, tiene_terraza, activa)"
                        " VALUES (:s, :n, :j, :a, :sa, :t, true)"
                    ),
                    {
                        "s": sid,
                        "n": str(numero),
                        "j": numero % 3 == 0,
                        "a": numero in (110, 111),
                        "sa": numero == 112,
                        "t": numero in (111, 112),
                    },
                )

    from sqlalchemy.ext.asyncio import AsyncSession

    from modules.sucursal.services.sucursal_service import DESCRIPCION_ROL, PERMISOS_POR_ROL

    async with AsyncSession(engine) as session, session.begin():
        cuentas = AccountsService(session)
        for rol, permisos in PERMISOS_POR_ROL.items():
            await cuentas.ensure_role(
                rol.value, tenant_id=None, permissions=permisos, description=DESCRIPCION_ROL[rol]
            )
        admin = await cuentas.row_for_email("admin@picasso.mx", tenant_id=None)
        personas: list[tuple[str, str, str, str | None]] = [
            ("propietario@picasso.mx", "Dirección Picasso", "propietario", None)
        ]
        for clave, _, _ in SUCURSALES:
            gerente, ama = NOMBRES[clave]
            personas.append((f"gerente.{clave.lower()}@picasso.mx", gerente, "gerente", clave))
            personas.append((f"ama.{clave.lower()}@picasso.mx", ama, "ama_llaves", clave))
        for email, nombre, puesto, sucursal_clave in personas:
            usuario = await cuentas.create_user(
                email,
                password=CONTRASENA,
                display_name=nombre,
                role_names=[puesto],
                email_verified=True,
            )
            sid = None
            if sucursal_clave:
                sid = (
                    await session.execute(
                        text("SELECT id FROM sucursales WHERE clave = :c"), {"c": sucursal_clave}
                    )
                ).scalar_one()
            await session.execute(
                text(
                    "INSERT INTO personal (user_id, nombre, rol, sucursal_id, activo)"
                    " VALUES (:u, :n, :r, :s, true)"
                ),
                {"u": usuario.id, "n": nombre, "r": puesto, "s": sid},
            )
        if admin is not None:
            await session.execute(
                text(
                    "INSERT INTO personal (user_id, nombre, rol, sucursal_id, activo)"
                    " VALUES (:u, 'Administración', 'admin', NULL, true)"
                ),
                {"u": admin["id"]},
            )
    await engine.dispose()


class Cliente:
    def __init__(self, http: httpx.AsyncClient, email: str) -> None:
        self.http = http
        self.email = email
        self.headers: dict[str, str] = {}

    async def entrar(self) -> None:
        r = await self.http.post("/auth/login", json={"email": self.email, "password": CONTRASENA})
        r.raise_for_status()
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    async def pedir(self, metodo: str, ruta: str, **kw: Any) -> Any:
        r = await self.http.request(metodo, ruta, headers=self.headers, **kw)
        if r.status_code >= 400:
            raise RuntimeError(f"{metodo} {ruta} -> {r.status_code} {r.text}")
        return r.json() if r.content else None


async def revisar(
    c: Cliente,
    habitacion_id: int,
    fallas: dict[str, str],
    *,
    completar: bool = True,
    hasta: int | None = None,
    con_foto: bool = True,
) -> Any:
    rev = await c.pedir("POST", "/revisiones", json={"habitacion_id": habitacion_id})
    for i, punto in enumerate(rev["puntos"]):
        if hasta is not None and i >= hasta:
            break
        if punto["resultado"] != "sin_revisar":
            continue
        codigo = punto["codigo"]
        if codigo in fallas:
            if con_foto:
                await c.pedir(
                    "POST",
                    f"/revisiones/{rev['id']}/puntos/{codigo}/fotos",
                    files={
                        "foto": (
                            f"{codigo}.jpg",
                            foto(f"{codigo} · {punto['titulo']}"),
                            "image/jpeg",
                        )
                    },
                )
            cuerpo = {"resultado": "falla", "observacion": fallas[codigo]}
        elif codigo in ("G25",) and azar.random() < 0.15:
            cuerpo = {"resultado": "no_aplica", "motivo_no_aplica": "La habitación estaba sucia."}
        else:
            cuerpo = {"resultado": "bien"}
        await c.pedir("PUT", f"/revisiones/{rev['id']}/puntos/{codigo}", json=cuerpo)
    if completar:
        await c.pedir("POST", f"/revisiones/{rev['id']}/completar")
    return await c.pedir("GET", f"/revisiones/{rev['id']}")


async def actividad() -> None:
    async with httpx.AsyncClient(base_url=API, timeout=60) as http:
        prop = Cliente(http, "propietario@picasso.mx")
        await prop.entrar()
        sucursales = await prop.pedir("GET", "/sucursales")

        for s in sucursales:
            clave = s["clave"].lower()
            gerente = Cliente(http, f"gerente.{clave}@picasso.mx")
            ama = Cliente(http, f"ama.{clave}@picasso.mx")
            await gerente.entrar()
            await ama.entrar()
            cuartos = await prop.pedir("GET", f"/sucursales/{s['id']}/habitaciones")
            por_numero = {h["numero"]: h["id"] for h in cuartos}

            # Ama de llaves: una revisión por limpieza, casi todas enviadas.
            for h in cuartos:
                fallas = {}
                if azar.random() < 0.18:
                    codigo = azar.choice(list(FALLAS_AMA))
                    fallas = {codigo: FALLAS_AMA[codigo]}
                incompleta = azar.random() < 0.08
                await revisar(
                    ama, h["id"], fallas, completar=not incompleta, hasta=18 if incompleta else None
                )

            # Gerente: revisión diaria, algunas pendientes.
            for h in cuartos:
                if azar.random() < 0.12:
                    continue
                fallas = {}
                if azar.random() < 0.2:
                    codigo = azar.choice(list(FALLAS_GERENTE))
                    fallas = {codigo: FALLAS_GERENTE[codigo]}
                rev = await revisar(gerente, h["id"], fallas)
                for p in rev["puntos"]:
                    if p["incidencia_id"] and p["codigo"] in ("G04", "G10", "G13"):
                        await gerente.pedir(
                            "PATCH",
                            f"/incidencias/{p['incidencia_id']}",
                            json={"prioridad": "alta"},
                        )
                        await gerente.pedir(
                            "POST",
                            f"/habitaciones/{h['id']}/renta",
                            json={
                                "puede_rentarse": False,
                                "motivo": f"{p['titulo']}: {p['observacion']}",
                                "incidencia_id": p["incidencia_id"],
                            },
                        )

            # El caso del documento, en Lerma: falla en G04 de la 105, de la
            # detección al cierre con foto y la renta de vuelta.
            if s["clave"] == "LER":
                hab = por_numero["105"]
                await revisar(gerente, hab, {"G04": "Fuga al abrir la regadera."}, completar=False)

            # Uno de cada sucursal pasa a atención y otro se cierra con foto.
            folios = await gerente.pedir("GET", "/incidencias", params={"estado": "abiertas"})
            for i, folio in enumerate(folios[:2]):
                await gerente.pedir(
                    "PATCH",
                    f"/incidencias/{folio['id']}",
                    json={"responsable_atencion": "Mantenimiento", "en_atencion": True},
                )
                if i == 1:
                    await gerente.pedir(
                        "POST",
                        f"/incidencias/{folio['id']}/fotos",
                        data={"tipo": "reparacion"},
                        files={
                            "foto": ("rep.jpg", foto(f"Reparación {folio['folio']}"), "image/jpeg")
                        },
                    )
                    await gerente.pedir(
                        "POST",
                        f"/incidencias/{folio['id']}/cerrar",
                        json={"correccion": "Se corrigió y se verificó el funcionamiento."},
                    )
                    await gerente.pedir(
                        "POST",
                        f"/habitaciones/{folio['habitacion_id']}/renta",
                        json={
                            "puede_rentarse": True,
                            "motivo": "Reparación verificada.",
                            "incidencia_id": folio["id"],
                        },
                    )
            print(f"  {s['nombre']}: listo")


async def ayer() -> None:
    """Mueve un tercio de lo hecho a ayer, para que el periodo tenga dos días."""
    engine = create_async_engine(DatabaseSettings().dsn.get_secret_value())
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE revisiones SET iniciada_en = iniciada_en - interval '1 day',"
                " completada_en = completada_en - interval '1 day' WHERE id % 3 = 0"
                " AND estado = 'completa'"
            )
        )
    await engine.dispose()


async def main() -> None:
    print("Sucursales, habitaciones y cuentas...")
    await base()
    print("Revisiones y folios (por la API)...")
    await actividad()
    await ayer()
    print("Listo. Cuentas en el encabezado de este archivo.")


if __name__ == "__main__":
    asyncio.run(main())
