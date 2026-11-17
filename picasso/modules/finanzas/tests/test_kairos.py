# ruff: noqa: E501  (el HTML de ejemplo copia la forma de Kairos tal cual)
"""Lectura de Kairos, con HTML de la misma forma que el real (datos inventados).

La forma salió de la vista móvil de Kairos (`/kairos/mobil/ActualizaHome`,
`Ventas`) el 2026-11-17. Si Kairos cambia su HTML, estas pruebas dicen qué se
dejó de entender.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest

from modules.finanzas.services.kairos_cliente import ClienteKairos, KairosError
from modules.finanzas.services.kairos_html import (
    KairosNoEntendido,
    dinero,
    es_pantalla_de_entrada,
    fecha_kairos,
    leer_resumen,
    leer_serie_ventas,
    leer_ventas,
)

RESUMEN = """
<ol class="breadcrumb"><li><input type="text" value="16/11/2026" id="datepickerHome"></li></ol>
<div class="container-fluid"><div class="row">
 <div class="col-sm-6 col-lg-4"><div class="card"><div class="card-block p-2 clearfix">
   <i class="fa fa-bed bg-ingreso"></i>
   <div class="text-uppercase text-muted">Habitaciones</div>
   <div class="h5 text-right">$ 10,450.00 </div></div>
   <div class="card-footer"><a id="home_vts">Ver Ventas (11) <i class="fa fa-angle-right"></i></a></div>
 </div></div>
 <div class="col-sm-6 col-lg-4"><div class="card"><div class="card-block">
   <div class="text-uppercase">Ingresos Extras</div><div class="h5">$ 300.00</div></div>
   <div class="card-footer"><a id="extras_vts">Ver Extras (1) <i></i></a></div></div></div>
 <div class="col-sm-6 col-lg-4"><div class="card"><div class="card-block">
   <div class="text-uppercase">Room Service</div><div class="h5">$ 1,235.50</div></div>
   <div class="card-footer"><a id="servicios_vts">Ver Comandas (4)<i></i></a></div></div></div>
</div><div class="row">
 <div class="col-sm-6 col-lg-4"><div class="card"><div class="card-block">
   <i class="fa fa-minus-square bg-egreso"></i>
   <div class="text-uppercase">Gastos</div><div class="h5">$ .00</div></div>
   <div class="card-footer"><a id="gastos">Ver Gastos (0) <i></i></a></div></div></div>
</div><div class="row">
 <div class="col-sm-6 col-lg-4"><div class="card"><div class="card-block">
   <div class="text-uppercase">Total</div><div class="h5 text-right">$ 11,985.50</div></div></div></div>
</div></div>
<script> <!-- cargaCalendarioHome(); --> </script>
"""

VENTAS = """
<main class="main"><ol class="breadcrumb"><li><a id="btn_backInicio">REGRESAR</a></li></ol></main>
<div class="row"><div class="col-12">
<table class="table table-responsive">
  <thead class="thead-inverse"><tr><th>Tarifa</th><th>Cant.</th><th>Importe</th></tr></thead>
  <tbody>
    <tr><td>MOTEL SUITE</td><td>8</td><td class="text-right">$ 7,200.00</td></tr>
    <tr><td>HOTEL JACUZZI</td><td>3</td><td class="text-right">$ 3,250.00</td></tr>
    <tr><td class="font-weight-bold">TOTAL</td><td>11</td><td>$ 10,450.00</td></tr>
  </tbody>
</table></div></div>
<div class="row"><div class="col-12">
<table class="table table-responsive">
  <thead><tr><th></th><th>Folio</th><th>Hab.</th><th>Forma Pago</th><th>Importe</th><th></th></tr></thead>
  <tbody>
    <tr class="emitida"> <td>1</td> <td>8 </td> <td>109 </td> <td>TARJETA CREDITO</td>
      <td> $ 1,000.00 </td>
      <td><div class="view_vts" data-fecha="1794831223614" data-habitacion="109"></div></td></tr>
    <tr class="collapse collapse_checkin" id="collapse_1794831223614" data-fecha="1794831223614"
        data-habitacion="109"><td colspan="6"><img alt="Cargando..."><div class="card_ajax"></div></td></tr>
    <tr class="emitida"> <td>2</td> <td>3 </td> <td>711 </td> <td>EFECTIVO</td>
      <td> $ 9,450.00 </td><td></td></tr>
    <tr class="collapse collapse_checkin" data-fecha="1794834823614" data-habitacion="711">
      <td colspan="6"></td></tr>
    <tr><td colspan="4" class="font-weight-bold">TOTAL</td><td>$ 10,450.00 </td><td></td></tr>
  </tbody>
</table></div></div>
"""

ENTRADA = """
<form action="/kairos/mobil/LoginMobil.action;jsessionid=ABC" method="post">
  <input type="hidden" name="ismovil" value="SI">
  <input type="text" name="username"><input type="password" name="password">
</form>
"""


def test_dinero_entiende_los_formatos_de_kairos() -> None:
    assert dinero("$ 112,950.00 ") == Decimal("112950.00")
    assert dinero("$ .00") == Decimal("0.00")
    assert dinero("") == Decimal("0.00")


def test_fecha_en_el_formato_que_pide_kairos() -> None:
    assert fecha_kairos(date(2026, 11, 6)) == "06/11/2026"


def test_resumen_del_dia() -> None:
    r = leer_resumen(RESUMEN)
    assert r.habitaciones == Decimal("10450.00")
    assert r.rentas == 11
    assert r.extras == Decimal("300.00") and r.extras_n == 1
    assert r.room_service == Decimal("1235.50") and r.comandas == 4
    assert r.gastos == Decimal("0.00") and r.gastos_n == 0
    assert r.total == Decimal("11985.50")
    assert not r.vacio


def test_resumen_que_no_es_resumen_avisa() -> None:
    with pytest.raises(KairosNoEntendido):
        leer_resumen("<html><body>Error 500</body></html>")


def test_ventas_por_tarifa_y_cada_renta() -> None:
    v = leer_ventas(VENTAS)
    assert [(t.tarifa, t.cantidad, t.importe) for t in v.tarifas] == [
        ("MOTEL SUITE", 8, Decimal("7200.00")),
        ("HOTEL JACUZZI", 3, Decimal("3250.00")),
    ]
    assert v.total_tarifas == Decimal("10450.00")
    assert [(r.renglon, r.folio, r.habitacion, r.forma_pago) for r in v.rentas] == [
        (1, "8", "109", "TARJETA CREDITO"),
        (2, "3", "711", "EFECTIVO"),
    ]
    assert sum(r.importe for r in v.rentas) == v.total_rentas == v.total_tarifas
    assert v.rentas[0].entrada == datetime.fromtimestamp(1794831223.614, tz=UTC)


def test_ventas_sin_tablas_avisa() -> None:
    with pytest.raises(KairosNoEntendido):
        leer_ventas("<div>otra cosa</div>")


def test_serie_de_la_grafica_empieza_en_la_fecha_pedida() -> None:
    serie = leer_serie_ventas({"ventas": [0, 0, 83, 85]}, date(2026, 11, 12))
    assert serie[date(2026, 11, 14)] == 83
    assert serie[date(2026, 11, 12)] == 0


def test_reconoce_la_pantalla_de_entrada() -> None:
    assert es_pantalla_de_entrada(ENTRADA)
    assert not es_pantalla_de_entrada(RESUMEN)


# -- cliente contra un Kairos de mentira -------------------------------------------


def _kairos_falso(clave_buena: str) -> tuple[httpx.MockTransport, list[str]]:
    vistas: list[str] = []
    dentro = {"si": False}

    def responder(request: httpx.Request) -> httpx.Response:
        vistas.append(f"{request.method} {request.url.path}")
        if request.url.path == "/kairos/Mobil.action":
            return httpx.Response(200, text=ENTRADA)
        if request.url.path.startswith("/kairos/mobil/LoginMobil.action"):
            datos = dict(httpx.QueryParams(request.content.decode()))
            if datos.get("password") == clave_buena and datos.get("ismovil") == "SI":
                dentro["si"] = True
                return httpx.Response(200, text="<a>Salir</a> datepickerHome")
            return httpx.Response(200, text=ENTRADA)
        if not dentro["si"]:
            return httpx.Response(200, text=ENTRADA)
        if request.url.path == "/kairos/mobil/ActualizaHome":
            assert request.url.params["fecha"] == "16/11/2026"
            return httpx.Response(200, text=RESUMEN)
        if request.url.path == "/kairos/mobil/Ventas":
            return httpx.Response(200, text=VENTAS)
        if request.url.path == "/kairos/mobil/UpdateGraphVts":
            return httpx.Response(200, json={"ventas": [0, 2, 0]})
        return httpx.Response(404)

    return httpx.MockTransport(responder), vistas


@pytest.mark.asyncio
async def test_cliente_entra_y_lee_el_dia() -> None:
    transporte, vistas = _kairos_falso("buena")
    async with ClienteKairos(
        "http://kairos.test:1000/", usuario="u", clave="buena", pausa=0, transporte=transporte
    ) as k:
        r = await k.resumen(date(2026, 11, 16))
        v = await k.ventas(date(2026, 11, 16))
        serie = await k.rentas_por_dia(date(2026, 11, 15), date(2026, 11, 17))
    assert r.rentas == 11 and len(v.rentas) == 2
    assert serie == {date(2026, 11, 15): 0, date(2026, 11, 16): 2, date(2026, 11, 17): 0}
    assert vistas[0] == "GET /kairos/Mobil.action"
    # Solo lee: nunca toca acciones que escriben.
    assert not any("Actualiza" in v and "ActualizaHome" not in v for v in vistas)


@pytest.mark.asyncio
async def test_cliente_con_clave_mala_avisa() -> None:
    transporte, _ = _kairos_falso("buena")
    async with ClienteKairos(
        "http://kairos.test:1000", usuario="u", clave="mala", pausa=0, transporte=transporte
    ) as k:
        with pytest.raises(KairosError, match="no aceptó"):
            await k.resumen(date(2026, 11, 16))


@pytest.mark.asyncio
async def test_cliente_sin_red_avisa() -> None:
    def caido(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("sin red", request=request)

    async with ClienteKairos(
        "http://kairos.test:1000",
        usuario="u",
        clave="x",
        pausa=0,
        transporte=httpx.MockTransport(caido),
    ) as k:
        with pytest.raises(KairosError, match="Sin respuesta"):
            await k.resumen(date(2026, 11, 16))


# -- tipo de cada cuarto ----------------------------------------------------------

DETALLE_RENTA = """
<div class="card"><div class="card-header">Habitacion 505 <span>Ocupada</span></div>
<table><tr><td>Folio</td><td>4345</td></tr><tr><td>Entrada</td><td>14 noviembre 11:49 PM</td></tr>
<tr><td>Tiempo</td><td>10 hrs 35 min</td></tr><tr><td>Placas</td><td>ABC123</td></tr>
<tr><td>Tarifa</td><td>HOTEL   JACUZZI SAUNA</td></tr><tr><td>Subtotal</td><td>$ 750.00</td></tr></table></div>
"""


def test_la_renta_trae_su_marca_para_pedir_el_detalle() -> None:
    v = leer_ventas(VENTAS)
    assert v.rentas[0].marca == "1794831223614"


def test_tarifa_del_detalle_de_una_renta() -> None:
    from modules.finanzas.services.kairos_html import leer_tarifa_de_renta

    assert leer_tarifa_de_renta(DETALLE_RENTA) == "HOTEL JACUZZI SAUNA"
    assert leer_tarifa_de_renta("<p>sin datos</p>") is None


@pytest.mark.parametrize(
    ("tarifa", "seccion", "tipo", "jacuzzi", "sauna"),
    [
        ("MOTEL SUITE", "motel", "Suite", False, False),
        ("HOTEL JACUZZI", "hotel", "Jacuzzi", True, False),
        ("MOTEL JACUZZI SAUNA", "motel", "Jacuzzi y sauna", True, True),
        ("HOTEL JACUZZI PENT HOUSE", "hotel", "Pent house con jacuzzi", True, False),
        ("SUITE", None, "Suite", False, False),
    ],
)
def test_tipo_de_cuarto_desde_la_tarifa(
    tarifa: str, seccion: str | None, tipo: str, jacuzzi: bool, sauna: bool
) -> None:
    from modules.finanzas.services.kairos_html import tipo_de_tarifa

    t = tipo_de_tarifa(tarifa)
    assert (t.seccion, t.tipo, t.tiene_jacuzzi, t.tiene_sauna) == (seccion, tipo, jacuzzi, sauna)


def test_una_renta_suelta_no_cambia_el_tipo_del_cuarto() -> None:
    from modules.finanzas.services.kairos_html import tipo_mayoritario

    t = tipo_mayoritario(["HOTEL SUITE", "HOTEL JACUZZI", "HOTEL SUITE", "HOTEL SUITE"])
    assert t is not None and t.tipo == "Suite"
    assert tipo_mayoritario([]) is None
