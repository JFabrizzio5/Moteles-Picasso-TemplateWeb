"""Revisiones: el checklist de gerente y el de ama de llaves.

Una revisión identifica sucursal, habitación, puesto, responsable, fecha y
hora. Cada punto lleva uno de cuatro resultados; una Falla abre un folio (o se
vincula al folio abierto de la misma falla en esa habitación).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from jfastframework.errors import NotFoundError, ValidationError

from modules.sucursal import public as sucursal_publica
from shared.enums import Rol

from ..enums import EstadoIncidencia, EstadoRevision, Resultado, TipoEvidencia
from ..models import (
    PUNTOS,
    Actor,
    DecisionCrear,
    DecisionRead,
    DecisionRenta,
    Evidencia,
    EvidenciaRead,
    HabitacionEstado,
    Incidencia,
    PuntoGuardar,
    ResultadoPunto,
    ResultadoRead,
    Revision,
    RevisionDetalle,
    RevisionResumen,
    UltimaRevision,
    punto_de_equipo,
)
from ..repositories import InspeccionRepository
from ..validations import (
    exigir_puesto,
    exigir_sucursal,
    formato_folio,
    normalizar_punto,
    puntos_iniciales,
    validar_completar,
)
from .comun import (
    Archivos,
    ahora,
    amenidades,
    decision_read,
    evento,
    fecha_local,
    hoy,
    resultado_read,
    resumen_revision,
    ultimo_chequeo,
)

NOMBRE_PUESTO = {Rol.GERENTE: "gerente", Rol.AMA_LLAVES: "ama de llaves"}


class RevisionService:
    def __init__(self, repo: InspeccionRepository, archivos: Archivos) -> None:
        self.repo = repo
        self.archivos = archivos

    @property
    def session(self) -> AsyncSession:
        return self.repo.session

    async def _habitacion(self, habitacion_id: int) -> sucursal_publica.HabitacionDTO:
        habitacion = await sucursal_publica.habitacion(
            self.session, tenant_id=None, habitacion_id=habitacion_id
        )
        if habitacion is None or not habitacion.activa:
            raise NotFoundError(f"la habitación {habitacion_id} no existe")
        return habitacion

    async def _sucursal(self, sucursal_id: int) -> sucursal_publica.SucursalDTO:
        for sucursal in await sucursal_publica.sucursales(self.session, tenant_id=None):
            if sucursal.id == sucursal_id:
                return sucursal
        raise NotFoundError(f"la sucursal {sucursal_id} no existe")

    # -- abrir y leer ----------------------------------------------------

    async def iniciar(self, actor: Actor, habitacion_id: int) -> RevisionDetalle:
        """Abre la revisión del puesto, o retoma la que quedó a medias."""
        exigir_puesto(actor, Rol.GERENTE, Rol.AMA_LLAVES)
        habitacion = await self._habitacion(habitacion_id)
        exigir_sucursal(actor, habitacion.sucursal_id)
        abierta = await self.repo.revision_en_curso(habitacion_id, actor.rol.value)
        if abierta is not None:
            return await self.detalle(actor, abierta.id)

        sucursal = await self._sucursal(habitacion.sucursal_id)
        revision = await self.repo.agregar(
            Revision(
                sucursal_id=sucursal.id,
                sucursal_clave=sucursal.clave,
                sucursal_nombre=sucursal.nombre,
                habitacion_id=habitacion.id,
                habitacion_numero=habitacion.numero,
                rol=actor.rol.value,
                responsable_id=actor.user_id,
                responsable_nombre=actor.nombre,
                estado=EstadoRevision.EN_CURSO.value,
                iniciada_en=ahora(),
            )
        )
        iniciales = puntos_iniciales(actor.rol, set(amenidades(habitacion)))
        for orden, inicial in enumerate(iniciales):
            self.session.add(
                ResultadoPunto(
                    revision_id=revision.id,
                    codigo=inicial.punto.codigo,
                    orden=orden,
                    seccion=inicial.punto.seccion,
                    titulo=inicial.punto.titulo,
                    texto=inicial.punto.texto,
                    resultado=inicial.resultado.value,
                    motivo_no_aplica=inicial.motivo,
                    automatico=inicial.automatico,
                )
            )
        # Lo que tiene este cuarto (Netflix, sillón, minibar…) entra al final.
        equipos = await sucursal_publica.equipos_por_habitacion(
            self.session, tenant_id=None, habitacion_ids=[habitacion.id]
        )
        for desplazamiento, equipo in enumerate(equipos.get(habitacion.id, [])):
            punto = punto_de_equipo(actor.rol.value, equipo.id, equipo.nombre, equipo.categoria)
            self.session.add(
                ResultadoPunto(
                    revision_id=revision.id,
                    codigo=punto.codigo,
                    orden=len(iniciales) + desplazamiento,
                    seccion=punto.seccion,
                    titulo=punto.titulo,
                    texto=punto.texto,
                    resultado=Resultado.SIN_REVISAR.value,
                )
            )
        await self.session.flush()
        return await self.detalle(actor, revision.id)

    async def detalle(self, actor: Actor, revision_id: int) -> RevisionDetalle:
        revision = await self.repo.revision(revision_id)
        exigir_sucursal(actor, revision.sucursal_id)
        filas = await self.repo.resultados([revision.id])
        folios = await self.repo.folios([f.incidencia_id for f in filas if f.incidencia_id])
        por_punto: dict[str, list[EvidenciaRead]] = {}
        for evidencia in await self.repo.evidencias_de_revision(revision.id):
            por_punto.setdefault(evidencia.codigo_punto or "", []).append(
                await self.archivos.evidencia(evidencia)
            )
        conteo: dict[str, int] = {}
        for fila in filas:
            conteo[fila.resultado] = conteo.get(fila.resultado, 0) + 1
        vigentes = await self.repo.decisiones(revision.habitacion_id)
        anteriores = [
            r
            for r in await self.repo.revisiones(
                habitacion_id=revision.habitacion_id, estado="completa", limite=2
            )
            if r.id != revision.id
        ]
        previo = anteriores[0] if anteriores else None
        fallas_previo = (
            (await self.repo.conteo_resultados([previo.id])).get(previo.id, {}).get("falla", 0)
            if previo
            else 0
        )
        return RevisionDetalle(
            **resumen_revision(revision, conteo).model_dump(),
            puntos=[resultado_read(f, folios, por_punto.get(f.codigo)) for f in filas],
            renta=decision_read(vigentes[0] if vigentes else None),
            ultimo_chequeo=ultimo_chequeo(previo, fallas_previo),
        )

    async def listar(
        self,
        actor: Actor,
        *,
        sucursal_id: int | None,
        habitacion_id: int | None,
        rol: Rol | None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
    ) -> list[RevisionResumen]:
        if not actor.ve_todas:
            sucursal_id = actor.sucursal_id
        filas = await self.repo.revisiones(
            sucursal_id=sucursal_id,
            habitacion_id=habitacion_id,
            rol=rol.value if rol else None,
            desde=desde,
            hasta=hasta,
        )
        conteos = await self.repo.conteo_resultados([f.id for f in filas])
        return [resumen_revision(f, conteos.get(f.id)) for f in filas]

    # -- capturar --------------------------------------------------------

    async def _editable(self, actor: Actor, revision_id: int) -> Revision:
        revision = await self.repo.revision(revision_id)
        exigir_sucursal(actor, revision.sucursal_id)
        if revision.rol != actor.rol.value:
            raise ValidationError(
                f"Esta revisión es del checklist de {NOMBRE_PUESTO[Rol(revision.rol)]}."
            )
        if revision.estado != EstadoRevision.EN_CURSO:
            raise ValidationError("La revisión ya se cerró; su registro no se modifica.")
        return revision

    async def guardar_punto(
        self, actor: Actor, revision_id: int, codigo: str, payload: PuntoGuardar
    ) -> ResultadoRead:
        revision = await self._editable(actor, revision_id)
        punto = await self.repo.resultado(revision.id, codigo.upper())
        observacion, motivo = normalizar_punto(
            payload.resultado, payload.observacion, payload.motivo_no_aplica
        )

        if payload.resultado is Resultado.FALLA:
            await self._registrar_falla(actor, revision, punto, observacion or "")
        elif punto.incidencia_id is not None:
            await self._quitar_falla(actor, revision, punto, payload.resultado)

        punto.resultado = payload.resultado.value
        punto.observacion = observacion
        punto.motivo_no_aplica = motivo
        punto.automatico = False
        punto.en_bloque = False
        punto.revisado_en = None if payload.resultado is Resultado.SIN_REVISAR else ahora()
        await self.session.flush()

        folios = await self.repo.folios([punto.incidencia_id] if punto.incidencia_id else [])
        evidencias = await self.archivos.evidencias(
            await self.repo.evidencias_de_punto(revision.id, punto.codigo)
        )
        return resultado_read(punto, folios, evidencias)

    async def _registrar_falla(
        self, actor: Actor, revision: Revision, punto: ResultadoPunto, observacion: str
    ) -> None:
        if punto.incidencia_id is not None:
            incidencia = await self.repo.incidencia(punto.incidencia_id)
            if incidencia.estado in (EstadoIncidencia.REPORTADA, EstadoIncidencia.EN_ATENCION):
                if observacion != (punto.observacion or ""):
                    self.session.add(
                        evento(
                            incidencia.id,
                            actor,
                            "observacion",
                            f"Amplió la observación: {observacion}",
                        )
                    )
                return
            punto.incidencia_id = None

        abierta = await self.repo.incidencia_abierta_de(revision.habitacion_id, punto.codigo)
        if abierta is not None:
            punto.incidencia_id = abierta.id
            self.session.add(
                evento(
                    abierta.id,
                    actor,
                    "reincidencia",
                    f"Volvió a reportarse en la revisión de {NOMBRE_PUESTO[actor.rol]}: "
                    f"{observacion}",
                )
            )
        else:
            numero = await self.repo.siguiente_folio(revision.sucursal_id)
            incidencia = await self.repo.agregar(
                Incidencia(
                    folio=formato_folio(revision.sucursal_clave, numero),
                    sucursal_id=revision.sucursal_id,
                    sucursal_clave=revision.sucursal_clave,
                    sucursal_nombre=revision.sucursal_nombre,
                    habitacion_id=revision.habitacion_id,
                    habitacion_numero=revision.habitacion_numero,
                    codigo_punto=punto.codigo,
                    categoria=punto.seccion,
                    titulo=punto.titulo,
                    descripcion=observacion,
                    origen_rol=revision.rol,
                    origen_revision_id=revision.id,
                    reporto_id=actor.user_id,
                    reporto_nombre=actor.nombre,
                    reportada_en=ahora(),
                    prioridad="media",
                    estado=EstadoIncidencia.REPORTADA.value,
                )
            )
            punto.incidencia_id = incidencia.id
            self.session.add(
                evento(
                    incidencia.id,
                    actor,
                    "registro",
                    f"Registró la falla en {punto.codigo} · {punto.titulo}: {observacion}",
                )
            )
        # Las fotos que se tomaron antes de marcar la falla son su evidencia inicial.
        for foto in await self.repo.evidencias_de_punto(revision.id, punto.codigo):
            if foto.incidencia_id is None:
                foto.incidencia_id = punto.incidencia_id

    async def _quitar_falla(
        self, actor: Actor, revision: Revision, punto: ResultadoPunto, nuevo: Resultado
    ) -> None:
        incidencia = await self.repo.incidencia(punto.incidencia_id)  # type: ignore[arg-type]
        nombre = {Resultado.BIEN: "Bien", Resultado.NO_APLICA: "No aplica"}.get(
            nuevo, "Sin revisar"
        )
        if (
            incidencia.origen_revision_id == revision.id
            and incidencia.codigo_punto == punto.codigo
            and incidencia.estado == EstadoIncidencia.REPORTADA
        ):
            incidencia.estado = EstadoIncidencia.ANULADA.value
            self.session.add(
                evento(
                    incidencia.id,
                    actor,
                    "anulacion",
                    f"Cambió el punto a {nombre} en la misma revisión; el folio queda anulado.",
                )
            )
        else:
            self.session.add(
                evento(
                    incidencia.id,
                    actor,
                    "nota",
                    f"La revisión de {NOMBRE_PUESTO[actor.rol]} marcó este punto como {nombre}.",
                )
            )
        punto.incidencia_id = None

    async def foto_de_punto(
        self, actor: Actor, revision_id: int, codigo: str, datos: bytes, tipo: str | None
    ) -> EvidenciaRead:
        revision = await self._editable(actor, revision_id)
        punto = await self.repo.resultado(revision.id, codigo.upper())
        llave = await self.archivos.guardar(datos, tipo)
        fila = await self.repo.agregar(
            Evidencia(
                tipo=TipoEvidencia.PUNTO.value,
                archivo=llave,
                revision_id=revision.id,
                codigo_punto=punto.codigo,
                incidencia_id=punto.incidencia_id,
                subida_por_id=actor.user_id,
                subida_por_nombre=actor.nombre,
                subida_por_rol=actor.rol.value,
                creada_en=ahora(),
            )
        )
        if punto.incidencia_id is not None:
            self.session.add(
                evento(punto.incidencia_id, actor, "evidencia", f"Agregó foto en {punto.codigo}.")
            )
        return await self.archivos.evidencia(fila)

    async def quitar_foto(self, actor: Actor, revision_id: int, evidencia_id: int) -> None:
        revision = await self._editable(actor, revision_id)
        fila = await self.repo.evidencia(evidencia_id)
        if fila.revision_id != revision.id or fila.subida_por_id != actor.user_id:
            raise ValidationError("Solo quien tomó la foto puede quitarla, y solo en su revisión.")
        if fila.incidencia_id is not None:
            raise ValidationError("La foto ya es evidencia de un folio y se conserva.")
        await self.repo.borrar(fila)

    async def resto_bien(self, actor: Actor, revision_id: int) -> RevisionDetalle:
        """ "Lo demás está bien": los puntos sin tocar pasan a Bien, marcados en bloque.

        Quien revisa solo marca lo que está mal y confirma el resto. Queda
        registrado como en bloque para que el reporte no lo haga pasar por una
        revisión punto por punto.
        """
        revision = await self._editable(actor, revision_id)
        sucursal = await self._sucursal(revision.sucursal_id)
        if not sucursal.permite_bien_en_bloque:
            raise ValidationError("En esta sucursal cada punto se revisa uno por uno.")
        momento = ahora()
        for fila in await self.repo.resultados([revision.id]):
            if fila.resultado == Resultado.SIN_REVISAR:
                fila.resultado = Resultado.BIEN.value
                fila.en_bloque = True
                fila.revisado_en = momento
        await self.session.flush()
        return await self.detalle(actor, revision.id)

    async def completar(self, actor: Actor, revision_id: int) -> RevisionResumen:
        revision = await self._editable(actor, revision_id)
        filas = await self.repo.resultados([revision.id])
        validar_completar(f.resultado for f in filas)
        revision.estado = EstadoRevision.COMPLETA.value
        revision.completada_en = ahora()
        await self.session.flush()
        conteo: dict[str, int] = {}
        for fila in filas:
            conteo[fila.resultado] = conteo.get(fila.resultado, 0) + 1
        return resumen_revision(revision, conteo)

    # -- renta -----------------------------------------------------------

    async def decidir_renta(
        self, actor: Actor, habitacion_id: int, payload: DecisionCrear
    ) -> DecisionRead:
        """ "La decisión de rentar se registra por separado y corresponde al gerente." """
        exigir_puesto(actor, Rol.GERENTE)
        habitacion = await self._habitacion(habitacion_id)
        exigir_sucursal(actor, habitacion.sucursal_id)
        sucursal = await self._sucursal(habitacion.sucursal_id)
        if payload.incidencia_id is not None:
            incidencia = await self.repo.incidencia(payload.incidencia_id)
            if incidencia.habitacion_id != habitacion.id:
                raise ValidationError("El folio es de otra habitación.")
        fila = await self.repo.agregar(
            DecisionRenta(
                sucursal_id=sucursal.id,
                sucursal_clave=sucursal.clave,
                habitacion_id=habitacion.id,
                habitacion_numero=habitacion.numero,
                puede_rentarse=payload.puede_rentarse,
                motivo=payload.motivo.strip(),
                gerente_id=actor.user_id,
                gerente_nombre=actor.nombre,
                incidencia_id=payload.incidencia_id,
                decidida_en=ahora(),
            )
        )
        if payload.incidencia_id is not None:
            decision = "puede rentarse" if payload.puede_rentarse else "no puede rentarse"
            self.session.add(
                evento(
                    payload.incidencia_id, actor, "renta", f"Decidió: {decision}; {payload.motivo}"
                )
            )
        return DecisionRead.model_validate(fila, from_attributes=True)

    # -- tablero del personal ---------------------------------------------

    async def tablero(self, actor: Actor, sucursal_id: int | None) -> list[HabitacionEstado]:
        """Las habitaciones de la sucursal con lo que cada una tiene pendiente."""
        if not actor.ve_todas:
            sucursal_id = actor.sucursal_id
        if sucursal_id is None:
            raise ValidationError("Elige una sucursal.")
        sucursal = await self._sucursal(sucursal_id)
        habitaciones = await sucursal_publica.habitaciones(
            self.session, tenant_id=None, sucursal_id=sucursal_id
        )
        ultimas = await self.repo.ultimas_por_habitacion(sucursal_id)
        conteos = await self.repo.conteo_resultados([r.id for r in ultimas])
        abiertas = await self.repo.abiertas_por_habitacion(sucursal_id)
        rentas = await self.repo.rentas_vigentes(sucursal_id)
        gerente_ok = await self.repo.ultima_gerente_completa(sucursal_id)
        chequeos = await self.repo.ultimos_chequeos(sucursal_id=sucursal_id)
        equipos = await sucursal_publica.equipos_por_habitacion(
            self.session, tenant_id=None, habitacion_ids=[h.id for h in habitaciones]
        )
        fallas_chequeo = await self.repo.conteo_resultados([r.id for r in chequeos.values()])
        limite = hoy() - timedelta(days=max(sucursal.frecuencia_gerente_dias, 1) - 1)

        por_cuarto: dict[tuple[int, str], Revision] = {(r.habitacion_id, r.rol): r for r in ultimas}

        def ultima(habitacion_id: int, rol: str) -> UltimaRevision | None:
            fila = por_cuarto.get((habitacion_id, rol))
            if fila is None:
                return None
            resumen = resumen_revision(fila, conteos.get(fila.id))
            return UltimaRevision(
                id=fila.id,
                estado=resumen.estado,
                responsable_nombre=fila.responsable_nombre,
                iniciada_en=fila.iniciada_en,
                completada_en=fila.completada_en,
                revisados=resumen.revisados,
                total=resumen.total,
            )

        salida = []
        for habitacion in habitaciones:
            gerente = ultima(habitacion.id, Rol.GERENTE.value)
            ama = ultima(habitacion.id, Rol.AMA_LLAVES.value)
            mia = por_cuarto.get((habitacion.id, actor.rol.value))
            ultima_ok = gerente_ok.get(habitacion.id)
            salida.append(
                HabitacionEstado(
                    habitacion_id=habitacion.id,
                    sucursal_id=habitacion.sucursal_id,
                    numero=habitacion.numero,
                    amenidades=amenidades(habitacion),
                    gerente=gerente,
                    ama_llaves=ama,
                    mi_revision_en_curso=mia.id if mia and mia.estado == "en_curso" else None,
                    gerente_pendiente=ultima_ok is None or fecha_local(ultima_ok) < limite,
                    ama_enviada_sin_gerente=bool(
                        ama
                        and ama.completada_en
                        and (ultima_ok is None or ultima_ok < ama.completada_en)
                    ),
                    incidencias_abiertas=abiertas.get(habitacion.id, 0),
                    renta=decision_read(rentas.get(habitacion.id)),
                    equipo=[e.nombre for e in equipos.get(habitacion.id, [])],
                    ultimo_chequeo=ultimo_chequeo(
                        chequeos.get(habitacion.id),
                        fallas_chequeo.get(
                            chequeos[habitacion.id].id if habitacion.id in chequeos else -1, {}
                        ).get("falla", 0),
                    ),
                )
            )
        return salida

    @staticmethod
    def catalogo(rol: Rol) -> list[dict[str, object]]:
        return [
            {
                "codigo": p.codigo,
                "seccion": p.seccion,
                "titulo": p.titulo,
                "texto": p.texto,
                "requiere": list(p.requiere),
            }
            for p in PUNTOS.values()
            if p.rol == rol.value
        ]
