"""Entra una vez con cada cuenta de ejemplo y reutiliza los tokens mientras sirvan.

La API deja 20 entradas por IP cada 5 minutos y cada corrida necesita 13 (el
propietario, 6 gerentes y 6 amas de llaves): dos corridas seguidas chocarían
con el límite. Los tokens se guardan en resultados/.fichas.json (permisos
600, fuera de git) y se reutilizan mientras les quede vida para la corrida.

    python3 fichas.py <API> <minutos que dura la corrida>

Escribe el JSON en la salida estándar para que correr.sh lo pase a k6 por una
variable de entorno; no lo imprime en pantalla. La contraseña sale de
PICASSO_CLAVE_DEMO (la de picasso/scripts/sembrar.py).
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

AQUI = pathlib.Path(__file__).resolve().parent
CACHE = AQUI / "resultados" / ".fichas.json"
SUCURSALES = ["ler", "tol", "cir", "chu", "per", "vaq"]
CORREOS = ["propietario@picasso.mx"] + [
    f"{puesto}.{s}@picasso.mx" for s in SUCURSALES for puesto in ("gerente", "ama")
]


def clave() -> str:
    # La misma que usa scripts/sembrar.py para las cuentas de ejemplo.
    valor = os.environ.get("PICASSO_CLAVE_DEMO", "")
    if not valor:
        raise SystemExit("Falta PICASSO_CLAVE_DEMO (la contraseña de las cuentas de sembrar.py).")
    return valor


def entrar(api: str, correo: str, contrasena: str) -> tuple[str, int]:
    pet = urllib.request.Request(
        f"{api}/auth/login",
        data=json.dumps({"email": correo, "password": contrasena}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        d = json.load(urllib.request.urlopen(pet, timeout=30))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise SystemExit(
                "La API frenó las entradas (429): son 20 por IP cada 5 minutos. "
                "Espera 5 minutos y vuelve a correr."
            ) from None
        raise SystemExit(f"No pude entrar como {correo}: {e.code} {e.read()[:200]!r}") from None
    tokens = d.get("tokens", d)
    return tokens["access_token"], int(tokens.get("expires_in", 900))


def main() -> None:
    api, minutos = sys.argv[1].rstrip("/"), float(sys.argv[2])
    hace_falta = minutos * 60 + 60
    try:
        guardado = json.loads(CACHE.read_text())
        if guardado["api"] == api and guardado["vence"] - time.time() > hace_falta:
            print(json.dumps(guardado))
            return
    except (FileNotFoundError, KeyError, ValueError):
        pass

    contrasena = clave()
    tokens: dict[str, str] = {}
    vida = 10**9
    for correo in CORREOS:
        tokens[correo], expira = entrar(api, correo, contrasena)
        vida = min(vida, expira)
    if vida < hace_falta:
        raise SystemExit(
            f"La corrida dura {minutos:g} min y el token vive {vida // 60}. Para una "
            "resistencia más larga sube JFAST_AUTH_ACCESS_LIFETIME_MINUTES en el servidor "
            "de prueba (ver README)."
        )
    datos = {"api": api, "vence": time.time() + vida, "tokens": tokens}
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.touch(mode=0o600)
    os.chmod(CACHE, 0o600)
    CACHE.write_text(json.dumps(datos))
    print(json.dumps(datos))


if __name__ == "__main__":
    main()
