"""Reporte por habitación: últimas revisiones de ambos puestos, pendientes,
folios y la decisión de renta con motivo, fecha y gerente."""

from __future__ import annotations

from datetime import datetime

from reportlab.platypus import Flowable, Spacer

from ...models import HabitacionExpediente
from .base import (
    ANCHO_UTIL,
    CELDA,
    CHICO,
    COLOR_RESULTADO,
    PRIORIDADES,
    ROLES,
    caja,
    chip_estado,
    documento,
    encabezado,
    etiqueta,
    fecha_hora,
    p,
    seccion,
    t,
    tabla,
)

AMENIDADES = {"jacuzzi": "Jacuzzi", "alberca": "Alberca", "sauna": "Sauna", "terraza": "Terraza"}


def construir_habitacion(exp: HabitacionExpediente, generado: datetime) -> bytes:
    def contenido() -> list[Flowable]:
        amenidades = (
            " · ".join(AMENIDADES.get(a, a) for a in exp.amenidades) or "Sin amenidades especiales"
        )
        historia: list[Flowable] = encabezado(
            "Reporte por habitación",
            f"{exp.sucursal_nombre} · Hab. {exp.numero}",
            t(amenidades),
        )

        if exp.renta is not None:
            r = exp.renta
            color = COLOR_RESULTADO["bien" if r.puede_rentarse else "falla"].hexval()
            decision = "Puede rentarse" if r.puede_rentarse else "No puede rentarse"
            renta: list[Flowable] = [
                etiqueta("Decisión vigente de renta"),
                p(f'<font color="{color}" size="14"><b>{decision}</b></font>'),
                Spacer(1, 3),
                p(
                    f"Motivo: {t(r.motivo)}<br/>"
                    f"{t(r.gerente_nombre)} · {fecha_hora(r.decidida_en)}",
                    CHICO,
                ),
            ]
        else:
            renta = [etiqueta("Decisión vigente de renta"), p("Sin decisión registrada.")]
        historia.append(caja(renta))

        if len(exp.decisiones) > 1:
            historia.append(seccion("Decisiones anteriores"))
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
                            for d in exp.decisiones[1:]
                        ],
                    ],
                    [100, 82, ANCHO_UTIL - 292, 110],
                )
            )

        historia.append(seccion("Puntos pendientes"))
        if exp.pendientes:
            historia.append(
                tabla(
                    [
                        ["Código", "Punto", "Sección"],
                        *[
                            [x.codigo, p(t(x.titulo), CELDA), p(t(x.seccion), CELDA)]
                            for x in exp.pendientes
                        ],
                    ],
                    [50, ANCHO_UTIL - 210, 160],
                )
            )
        else:
            historia.append(p("No hay revisiones a medias."))

        historia.append(seccion("Folios"))
        if exp.incidencias:
            historia.append(
                tabla(
                    [
                        ["Folio", "Problema", "Estado", "Prior.", "Reportado", "Cerrado"],
                        *[
                            [
                                p(f"<b>{t(i.folio)}</b>", CELDA),
                                p(t(i.titulo), CELDA),
                                chip_estado(i.estado),
                                PRIORIDADES.get(i.prioridad, i.prioridad).replace("Prioridad ", ""),
                                fecha_hora(i.reportada_en),
                                fecha_hora(i.cerrada_en) if i.cerrada_en else "—",
                            ]
                            for i in exp.incidencias
                        ],
                    ],
                    [92, ANCHO_UTIL - 92 - 72 - 50 - 92 - 92, 72, 50, 92, 92],
                )
            )
        else:
            historia.append(p("Esta habitación no tiene folios."))

        historia.append(seccion("Revisiones"))
        if exp.revisiones:
            historia.append(
                tabla(
                    [
                        ["Fecha", "Puesto", "Responsable", "Estado", "Revisados", "Fallas"],
                        *[
                            [
                                fecha_hora(r.completada_en or r.iniciada_en),
                                ROLES.get(r.rol, r.rol),
                                p(t(r.responsable_nombre), CELDA),
                                "Completa" if r.estado == "completa" else "A medias",
                                f"{r.revisados} / {r.total}",
                                str(r.fallas),
                            ]
                            for r in exp.revisiones
                        ],
                    ],
                    [100, 80, ANCHO_UTIL - 100 - 80 - 66 - 64 - 46, 66, 64, 46],
                )
            )
        else:
            historia.append(p("Sin revisiones."))
        return historia

    return documento(
        f"Habitación · {exp.numero}",
        generado,
        contenido,
        asunto="Reporte por habitación",
    )
