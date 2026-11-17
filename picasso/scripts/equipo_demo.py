"""Datos de ejemplo: cuenta de administración de la demo y equipo en los cuartos.

No son datos reales: el equipo de cada cuarto lo captura la administración.
Usa la contraseña de las cuentas de ejemplo (scripts/sembrar.py) y la del
administrador inicial (JFAST_ACCOUNTS_BOOTSTRAP_ADMIN_PASSWORD), solo en local.

    PYTHONPATH=. jfast exec -- python scripts/equipo_demo.py
"""

from __future__ import annotations

import asyncio
import random

import httpx

from jfastframework.plugins.builtin.accounts import AccountsSettings

from scripts.sembrar import API, CONTRASENA

azar = random.Random(11)


async def main() -> None:
    clave_admin = AccountsSettings().bootstrap_admin_password
    if clave_admin is None:
        raise SystemExit("Falta JFAST_ACCOUNTS_BOOTSTRAP_ADMIN_PASSWORD en el .env")
    async with httpx.AsyncClient(base_url=API, timeout=60) as http:
        r = await http.post(
            "/auth/login",
            json={"email": "admin@picasso.mx", "password": clave_admin.get_secret_value()},
        )
        r.raise_for_status()
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        alta = await http.post(
            "/personal",
            headers=h,
            json={
                "nombre": "Administración (demo)",
                "email": "admin.demo@picasso.mx",
                "password": CONTRASENA,
                "rol": "admin",
            },
        )
        print("cuenta admin demo:", alta.status_code)

        equipos = {e["nombre"]: e["id"] for e in (await http.get("/equipos", headers=h)).json()}
        base = ["Televisión", "Netflix", "YouTube"]
        for s in (await http.get("/sucursales", headers=h)).json():
            for c in (await http.get(f"/sucursales/{s['id']}/habitaciones", headers=h)).json():
                nombres = list(base)
                if azar.random() < 0.6:
                    nombres.append("Bocina Bluetooth")
                if c["tiene_jacuzzi"] or azar.random() < 0.3:
                    nombres.append("Sillón tántrico")
                if azar.random() < 0.25:
                    nombres.append("Potro")
                if azar.random() < 0.5:
                    nombres.append("Minibar")
                if azar.random() < 0.3:
                    nombres.append("Luces de ambiente")
                await http.put(
                    f"/habitaciones/{c['id']}/equipos",
                    headers=h,
                    json={"equipo_ids": [equipos[n] for n in nombres]},
                )
            print(f"  {s['nombre']}: equipo asignado")


if __name__ == "__main__":
    asyncio.run(main())
