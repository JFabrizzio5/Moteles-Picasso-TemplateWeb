"""Las reglas del documento de la dirección, sin base de datos."""

from __future__ import annotations

from datetime import date

import pytest

from jfastframework.errors import ValidationError

from modules.inspeccion.enums import Resultado
from modules.inspeccion.models import AMA_LLAVES, GERENTE
from modules.inspeccion.validations import (
    completas_gerente,
    conformidad,
    exigibles_ama,
    exigibles_gerente,
    faltantes_para_cerrar,
    formato_folio,
    normalizar_punto,
    puntos_iniciales,
    validar_completar,
)
from shared.enums import Rol


def test_los_checklists_tienen_los_puntos_acordados() -> None:
    assert len(GERENTE) == 25
    assert len(AMA_LLAVES) == 29
    assert [p.codigo for p in GERENTE][:3] == ["G01", "G02", "G03"]
    assert AMA_LLAVES[-1].codigo == "A29"


def test_sin_jacuzzi_el_punto_entra_como_no_aplica_con_motivo() -> None:
    iniciales = {i.punto.codigo: i for i in puntos_iniciales(Rol.GERENTE, set())}
    assert iniciales["G20"].resultado is Resultado.NO_APLICA
    assert iniciales["G20"].automatico
    assert "jacuzzi" in (iniciales["G20"].motivo or "")
    assert iniciales["G04"].resultado is Resultado.SIN_REVISAR


def test_con_jacuzzi_el_punto_queda_por_revisar() -> None:
    iniciales = {i.punto.codigo: i for i in puntos_iniciales(Rol.GERENTE, {"jacuzzi"})}
    assert iniciales["G20"].resultado is Resultado.SIN_REVISAR
    assert iniciales["G11"].resultado is Resultado.SIN_REVISAR  # jacuzzi o alberca


def test_falla_pide_observacion_y_no_aplica_pide_motivo() -> None:
    with pytest.raises(ValidationError):
        normalizar_punto(Resultado.FALLA, "  ", None)
    with pytest.raises(ValidationError):
        normalizar_punto(Resultado.NO_APLICA, None, "")
    assert normalizar_punto(Resultado.BIEN, " ok ", "sobra") == ("ok", None)


def test_sin_revisar_impide_terminar() -> None:
    with pytest.raises(ValidationError, match="1 punto"):
        validar_completar(["bien", "sin_revisar", "falla"])
    validar_completar(["bien", "no_aplica", "falla"])


def test_solo_el_gerente_cierra_y_con_foto_y_explicacion() -> None:
    assert faltantes_para_cerrar("Se cambió el sello", 1, Rol.GERENTE) == []
    assert len(faltantes_para_cerrar("", 0, Rol.GERENTE)) == 2
    assert faltantes_para_cerrar("listo", 1, Rol.PROPIETARIO)
    sin_texto = faltantes_para_cerrar(None, 1, Rol.GERENTE, revisar_correccion=False)
    assert sin_texto == []


def test_folio() -> None:
    assert formato_folio("ler", 245) == "PIC-LER-000245"


def test_cumplimiento_del_gerente_por_ventana() -> None:
    desde, hasta = date(2026, 11, 9), date(2026, 11, 10)
    assert exigibles_gerente(10, desde, hasta, 1) == 20
    assert exigibles_gerente(10, desde, hasta, 2) == 10
    # Dos revisiones del mismo cuarto el mismo día cuentan una.
    fechas = {1: [date(2026, 11, 9), date(2026, 11, 9), date(2026, 11, 10)]}
    assert completas_gerente(fechas, desde, 1) == 2
    assert completas_gerente(fechas, desde, 2) == 1


def test_exigibles_de_ama_segun_la_regla() -> None:
    desde, hasta = date(2026, 11, 9), date(2026, 11, 10)
    assert exigibles_ama("por_limpieza", 10, desde, hasta, iniciadas=7) == 7
    assert exigibles_ama("diaria", 10, desde, hasta, iniciadas=7) == 20


def test_conformidad_no_cuenta_no_aplica_ni_sin_revisar() -> None:
    assert conformidad(9, 1) == 0.9
    assert conformidad(0, 0) is None


def test_ultimo_chequeo_solo_de_revisiones_terminadas() -> None:
    from datetime import UTC, datetime

    from modules.inspeccion.models import Revision
    from modules.inspeccion.services.comun import ultimo_chequeo

    base = {
        "id": 7,
        "sucursal_id": 1,
        "sucursal_clave": "LER",
        "sucursal_nombre": "Picasso Lerma",
        "habitacion_id": 3,
        "habitacion_numero": "103",
        "rol": "ama_llaves",
        "responsable_id": "u1",
        "responsable_nombre": "Rosa Hernández",
        "iniciada_en": datetime(2026, 11, 11, 17, 0, tzinfo=UTC),
    }
    a_medias = Revision(**base, estado="en_curso", completada_en=None)
    assert ultimo_chequeo(a_medias) is None
    terminada = Revision(
        **base, estado="completa", completada_en=datetime(2026, 11, 11, 17, 29, tzinfo=UTC)
    )
    chequeo = ultimo_chequeo(terminada, fallas=1)
    assert chequeo is not None
    assert chequeo.rol is Rol.AMA_LLAVES
    assert chequeo.fallas == 1
    assert ultimo_chequeo(None) is None


def test_el_equipo_del_cuarto_entra_al_checklist_segun_el_puesto() -> None:
    from modules.inspeccion.models import punto_de_equipo

    gerente = punto_de_equipo("gerente", 3, "Netflix", "Entretenimiento")
    ama = punto_de_equipo("ama_llaves", 7, "Sillón tántrico", "Mobiliario especial")
    assert gerente.codigo == "E03"
    assert "funciona" in gerente.texto
    assert ama.seccion == "Equipo del cuarto"
    assert "desinfectado" in ama.texto
    assert "limpio" in punto_de_equipo("ama_llaves", 9, "Algo nuevo", "Otra categoría").texto
