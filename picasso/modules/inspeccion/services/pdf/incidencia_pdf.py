"""Reporte por incidencia: el expediente completo de un folio."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from reportlab.platypus import Flowable, KeepTogether, Spacer, Table, TableStyle

from ...models import IncidenciaDetalle
from .base import (
    ANCHO_UTIL,
    CELDA,
    CHICO,
    PRIORIDADES,
    ROLES,
    FotoPdf,
    caja,
    chip_estado,
    documento,
    encabezado,
    etiqueta,
    fecha_hora,
    galeria,
    p,
    seccion,
    t,
    tabla,
)

TIPOS = {"punto": "Foto inicial", "avance": "Avance", "reparacion": "Foto de reparación"}


def construir_incidencia(
    inc: IncidenciaDetalle,
    fotos: Sequence[tuple[str, FotoPdf]],
    generado: datetime,
) -> bytes:
    """`fotos` son pares (tipo de evidencia, foto)."""

    def contenido() -> list[Flowable]:
        historia: list[Flowable] = encabezado(
            f"Reporte por incidencia · {inc.folio}",
            inc.titulo,
            f"{t(inc.sucursal_nombre)} · Hab. {t(inc.habitacion_numero)} · "
            f"{PRIORIDADES.get(inc.prioridad, inc.prioridad)} · {t(inc.categoria)}",
        )
        historia.append(chip_estado(inc.estado))
        historia.append(Spacer(1, 12))

        mitad = (ANCHO_UTIL - 10) / 2
        original = caja(
            [
                etiqueta("Reporte original"),
                p(f"<b>{t(inc.descripcion)}</b>"),
                p(
                    f"Origen: {ROLES.get(inc.origen_rol, inc.origen_rol)} · "
                    f"checklist {t(inc.codigo_punto)}<br/>"
                    f"Reportó: {t(inc.reporto_nombre)}<br/>{fecha_hora(inc.reportada_en)}",
                    CHICO,
                ),
            ],
            mitad,
        )
        atencion_texto = [
            etiqueta("Atención y corrección"),
            p(
                f"Atiende: {t(inc.responsable_atencion)}"
                if inc.responsable_atencion
                else "Sin responsable asignado."
            ),
        ]
        if inc.correccion:
            atencion_texto.append(p(t(inc.correccion)))
        if inc.cerrada_en:
            atencion_texto.append(
                p(
                    f"Verificó y cerró: {t(inc.cerrada_por_nombre)} · {fecha_hora(inc.cerrada_en)}",
                    CHICO,
                )
            )
        atencion = caja(atencion_texto, mitad)
        dos = Table([[original, atencion]], colWidths=[mitad + 10, mitad])
        dos.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (0, 0), 10),
                    ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ]
            )
        )
        historia.append(dos)

        historia.append(seccion("Decisión de renta"))
        if inc.renta_vigente is not None:
            r = inc.renta_vigente
            decision = "Puede rentarse" if r.puede_rentarse else "No puede rentarse"
            historia.append(
                p(
                    f"<b>Vigente: {decision}</b> · {t(r.motivo)} · "
                    f"{t(r.gerente_nombre)} · {fecha_hora(r.decidida_en)}"
                )
            )
        else:
            historia.append(p("El gerente no ha registrado una decisión para esta habitación."))
        if inc.decisiones:
            historia.append(Spacer(1, 6))
            historia.append(
                tabla(
                    [
                        ["Fecha", "Decisión", "Motivo", "Gerente"],
                        *[
                            [
                                fecha_hora(d.decidida_en),
                                "Puede rentarse" if d.puede_rentarse else "No rentar",
                                p(t(d.motivo), CELDA),
                                p(t(d.gerente_nombre), CELDA),
                            ]
                            for d in inc.decisiones
                        ],
                    ],
                    [100, 82, ANCHO_UTIL - 100 - 82 - 110, 110],
                )
            )

        historia.append(seccion("Historial · quién hizo qué y cuándo"))
        historia.append(
            tabla(
                [
                    ["Fecha", "Quién", "Qué"],
                    *[
                        [
                            fecha_hora(e.fecha),
                            p(
                                f"<b>{t(e.actor_nombre)}</b><br/>"
                                f"{ROLES.get(e.actor_rol, e.actor_rol)}",
                                CELDA,
                            ),
                            p(t(e.detalle), CELDA),
                        ]
                        for e in inc.historial
                    ],
                ],
                [100, 120, ANCHO_UTIL - 220],
            )
        )

        if fotos:
            titulo: list[Flowable] = [seccion("Evidencias")]
            for tipo in ("punto", "avance", "reparacion"):
                grupo = [f for k, f in fotos if k == tipo]
                if grupo:
                    historia.append(
                        KeepTogether([*titulo, etiqueta(TIPOS[tipo]), Spacer(1, 4), galeria(grupo)])
                    )
                    titulo = []
        else:
            historia.append(seccion("Evidencias"))
            historia.append(p("Este folio no tiene fotos."))
        return historia

    return documento(f"Folio · {inc.folio}", generado, contenido, asunto="Reporte por incidencia")
