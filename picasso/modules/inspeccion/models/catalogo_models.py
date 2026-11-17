"""Los dos checklists acordados, tal como vienen en el documento de la dirección.

Gerente: 25 puntos (G01-G25). Ama de llaves: 29 puntos (A01-A29).

Viven en código y no en una tabla porque cambiarlos es una decisión de la
dirección, no una captura: un cambio aquí se revisa como cualquier otro. Cada
revisión guarda una copia del texto de cada punto, así que editar un criterio
no reescribe revisiones pasadas.

`requiere` marca los puntos que solo aplican si la habitación tiene algo
(jacuzzi, alberca, sauna, terraza). Si no lo tiene, el punto entra como
No aplica con el motivo escrito por el sistema, y nadie tiene que marcarlo.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(frozen=True, slots=True)
class Punto:
    codigo: str
    rol: str
    seccion: str
    titulo: str
    texto: str
    #: Amenidades de las que depende; aplica si la habitación tiene cualquiera.
    requiere: tuple[str, ...] = ()


def _g(codigo: str, seccion: str, titulo: str, texto: str, *requiere: str) -> Punto:
    return Punto(codigo, "gerente", seccion, titulo, texto, requiere)


def _a(codigo: str, seccion: str, titulo: str, texto: str, *requiere: str) -> Punto:
    return Punto(codigo, "ama_llaves", seccion, titulo, texto, requiere)


GERENTE: tuple[Punto, ...] = (
    _g(
        "G01",
        "Acceso y seguridad",
        "Puerta y cerradura",
        "Puerta, cerradura y seguro de la habitación cierran y funcionan correctamente.",
    ),
    _g(
        "G02",
        "Acceso y seguridad",
        "Portón y acceso",
        "El portón de la cochera y el acceso operan sin trabas.",
    ),
    _g(
        "G03",
        "Acceso y seguridad",
        "Mapa, precios y QR",
        "Revisar que el mapa de emergencia, los letreros de precios y el QR de quejas y "
        "sugerencias estén visibles y en buen estado, y que el QR funcione.",
    ),
    _g("G04", "Agua y baño", "Fugas en baño", "Lavabo, regadera e inodoro sin fugas visibles."),
    _g(
        "G05",
        "Agua y baño",
        "Agua fría y caliente",
        "Agua fría y caliente disponibles; el caudal permite usar lavabo y regadera.",
    ),
    _g(
        "G06",
        "Agua y baño",
        "Descarga del inodoro",
        "El inodoro descarga correctamente, recupera su nivel de agua y no deja correr agua "
        "continuamente.",
    ),
    _g(
        "G07",
        "Agua y baño",
        "Desagües",
        "Los desagües del lavabo y la regadera funcionan sin retorno de agua ni acumulación "
        "anormal.",
    ),
    _g(
        "G08",
        "Electricidad y clima",
        "Luces y apagadores",
        "Las luces y los apagadores de la cochera, la habitación y el baño funcionan "
        "correctamente.",
    ),
    _g(
        "G09",
        "Electricidad y clima",
        "Contactos y placas",
        "Los contactos y sus placas están firmes, sin quemaduras ni cables expuestos.",
    ),
    _g(
        "G10",
        "Electricidad y clima",
        "Aire acondicionado",
        "El aire acondicionado funciona correctamente.",
    ),
    _g(
        "G11",
        "Electricidad y clima",
        "Extractor",
        "En habitaciones con jacuzzi o alberca, revisar que el extractor funcione y sus "
        "rejillas estén despejadas. Donde no exista extractor, marcar No aplica.",
        "jacuzzi",
        "alberca",
    ),
    _g(
        "G12",
        "Habitación",
        "Humedad y olores",
        "No hay humedad persistente, filtraciones ni olores anormales en la habitación.",
    ),
    _g(
        "G13",
        "Habitación",
        "Pintura, muros y plafones",
        "La pintura, los muros y los plafones no presentan deterioro ni desprendimientos.",
    ),
    _g("G14", "Habitación", "Piso", "El piso no tiene piezas sueltas, levantadas o rotas."),
    _g(
        "G15",
        "Habitación",
        "Cama y muebles",
        "La cama y los muebles están estables, sin piezas flojas ni bordes dañados.",
    ),
    _g(
        "G16",
        "Habitación",
        "Ventanas, espejos y cristales",
        "Las ventanas, los espejos y los cristales están íntegros, y sus cierres funcionan "
        "correctamente cuando aplique.",
    ),
    _g(
        "G17",
        "Entretenimiento y servicio",
        "Televisión y canales",
        "La televisión, la señal y el control remoto funcionan correctamente; los canales "
        "corresponden a la lista autorizada y funcionan Netflix y YouTube.",
    ),
    _g(
        "G18",
        "Entretenimiento y servicio",
        "Teléfono con recepción",
        "El teléfono o intercomunicador funciona correctamente. El gerente debe comunicarse "
        "con recepción y comprobar que contesten en un máximo de 30 segundos.",
    ),
    _g(
        "G19",
        "Entretenimiento y servicio",
        "Amenidades, vasos y agua",
        "Revisar que las amenidades estén completas y que haya vasos y botellas de agua en "
        "la habitación.",
    ),
    _g(
        "G20",
        "Áreas especiales",
        "Jacuzzi",
        "Cuando haya jacuzzi, verificar que llene, funcione y desagüe correctamente, sin "
        "fugas visibles.",
        "jacuzzi",
    ),
    _g(
        "G21",
        "Áreas especiales",
        "Alberca",
        "Cuando haya alberca, revisar que no existan fugas ni daños visibles en sus equipos "
        "o superficies.",
        "alberca",
    ),
    _g(
        "G22",
        "Áreas especiales",
        "Sauna",
        "Cuando haya sauna, verificar que sus controles y puerta funcionen correctamente.",
        "sauna",
    ),
    _g(
        "G23",
        "Áreas especiales",
        "Terraza o jardín",
        "Cuando haya terraza o jardín, revisar que la vegetación y los asientos estén "
        "limpios y en buen estado.",
        "terraza",
    ),
    _g(
        "G24",
        "Cochera",
        "Cochera",
        "Revisar que el piso, los muros y el drenaje de la cochera estén en buen estado, "
        "sin encharcamientos, y que la puerta abra y cierre correctamente.",
    ),
    _g(
        "G25",
        "Revisión final",
        "Piso con linterna",
        "Si la habitación está limpia, revisar el piso con una linterna y verificar que no "
        "haya pelos. Si la habitación está sucia, marcar No aplica.",
    ),
)

AMA_LLAVES: tuple[Punto, ...] = (
    _a(
        "A01",
        "Cama y blancos",
        "Sábanas",
        "Las sábanas están limpias, sin manchas, cabellos ni residuos.",
    ),
    _a(
        "A02",
        "Cama y blancos",
        "Colchón y almohadas",
        "El protector del colchón, la superficie de la cama, las almohadas y sus fundas "
        "están limpios, secos, sin roturas y sin olores.",
    ),
    _a(
        "A03",
        "Cama y blancos",
        "Toallas",
        "Las toallas están completas según la dotación de la habitación, secas y sin manchas.",
    ),
    _a(
        "A04",
        "Baño",
        "Inodoro",
        "El inodoro, el asiento y la tapa están limpios, sin residuos ni olores. El inodoro "
        "tiene el sello de limpio y el producto azul.",
    ),
    _a(
        "A05",
        "Baño",
        "Regadera y muros",
        "La regadera, los muros y sus accesorios están limpios, sin residuos de jabón, "
        "sarro visible ni cabellos.",
    ),
    _a(
        "A06",
        "Baño",
        "Lavabo y grifería",
        "El lavabo, la grifería y la cubierta están limpios y secos.",
    ),
    _a(
        "A07",
        "Baño",
        "Piso del baño",
        "El piso del baño y las coladeras están limpios, sin residuos, cabellos ni agua acumulada.",
    ),
    _a(
        "A08",
        "Habitación",
        "Piso y esquinas",
        "El piso, las esquinas y las zonas accesibles debajo de los muebles están libres "
        "de basura.",
    ),
    _a(
        "A09",
        "Habitación",
        "Muebles",
        "Los burós, las mesas y el mobiliario están limpios, sin polvo ni manchas.",
    ),
    _a(
        "A10",
        "Habitación",
        "Manijas y controles",
        "Las manijas, los apagadores y los controles están limpios.",
    ),
    _a(
        "A11",
        "Habitación",
        "Espejos y cristales",
        "Los espejos y cristales están limpios, sin marcas. Se reportan las roturas visibles.",
    ),
    _a(
        "A12",
        "Habitación",
        "Botes de basura",
        "Los botes de basura están vacíos, limpios y con bolsa cuando corresponda.",
    ),
    _a(
        "A13",
        "Habitación",
        "Olores",
        "La habitación no presenta olores persistentes a basura, humo o humedad.",
    ),
    _a(
        "A14",
        "Amenidades",
        "Papel, jabón y amenidades",
        "El papel, el jabón y las amenidades están completos según la lista autorizada.",
    ),
    _a(
        "A15",
        "Amenidades",
        "Vasos y agua",
        "Hay 2 vasos limpios y 2 botellas de agua por habitación. Los accesorios de "
        "servicio están limpios y completos.",
    ),
    _a(
        "A16",
        "Amenidades",
        "Menús",
        "Revisar que en la habitación estén los menús de comida, bebidas y juguetes sexuales.",
    ),
    _a(
        "A17",
        "Funcionamiento",
        "Luces de la habitación",
        "Las luces encienden y las lámparas no presentan daños visibles.",
    ),
    _a(
        "A18",
        "Funcionamiento",
        "Televisión y Bluetooth",
        "La televisión y el control remoto funcionan correctamente; Netflix tiene una "
        "cuenta activa y el Bluetooth para reproducir música funciona.",
    ),
    _a(
        "A19",
        "Funcionamiento",
        "Aire acondicionado",
        "El aire acondicionado enciende correctamente.",
    ),
    _a(
        "A20",
        "Cochera",
        "Acceso y cochera",
        "El acceso y la cochera asignada a la habitación están limpios, sin basura ni residuos.",
    ),
    _a(
        "A21",
        "Áreas especiales",
        "Jacuzzi",
        "Cuando haya jacuzzi, revisar que esté limpio y sin residuos en sus superficies y desagüe.",
        "jacuzzi",
    ),
    _a(
        "A22",
        "Áreas especiales",
        "Alberca",
        "Cuando haya alberca, revisar que ésta y su alrededor estén libres de residuos "
        "visibles, que el agua esté a la temperatura establecida y que mantenga un flujo "
        "continuo de recirculación.",
        "alberca",
    ),
    _a(
        "A23",
        "Áreas especiales",
        "Sauna o terraza",
        "Cuando haya sauna o terraza, verificar que estén limpios conforme al estándar de "
        "la sucursal.",
        "sauna",
        "terraza",
    ),
    _a(
        "A24",
        "Cierre",
        "Blancos y utensilios olvidados",
        "No quedan blancos usados ni utensilios o productos de limpieza olvidados en la "
        "habitación.",
    ),
    _a(
        "A25",
        "Cierre",
        "Cama y muebles acomodados",
        "La cama y los muebles están acomodados según el estándar de la sucursal.",
    ),
    _a(
        "A26",
        "Cierre",
        "Objetos olvidados",
        "Revisar que no queden objetos olvidados del huésped. Si se encuentra alguno, "
        "registrarlo para su resguardo.",
    ),
    _a(
        "A27",
        "Cierre",
        "Plagas",
        "Verificar que no haya insectos, excrementos ni otros rastros visibles de plagas.",
    ),
    _a("A28", "Cierre", "Aromatizante", "Confirmar que se aplicó aromatizante en la habitación."),
    _a(
        "A29",
        "Cierre",
        "Piso con linterna",
        "Revisar el piso con una linterna y verificar que no haya pelos ni residuos.",
    ),
)

CHECKLISTS: dict[str, tuple[Punto, ...]] = {"gerente": GERENTE, "ama_llaves": AMA_LLAVES}
PUNTOS: dict[str, Punto] = {p.codigo: p for p in (*GERENTE, *AMA_LLAVES)}

NOMBRE_AMENIDAD = {
    "jacuzzi": "jacuzzi",
    "alberca": "alberca",
    "sauna": "sauna",
    "terraza": "terraza ni jardín",
}


class PuntoRead(BaseModel):
    codigo: str
    rol: str
    seccion: str
    titulo: str
    texto: str
    requiere: list[str]


# -- equipo del cuarto -----------------------------------------------------------
# Lo que cada cuarto tiene (Netflix, sillón tántrico, minibar…) lo configura la
# administración. Cada cosa entra al checklist del cuarto como un punto más,
# con un criterio según el puesto: el gerente ve que funcione, la ama de llaves
# que esté limpio.

SECCION_EQUIPO = "Equipo del cuarto"

_CRITERIO: dict[tuple[str, str], str] = {
    ("gerente", "Entretenimiento"): "enciende y funciona correctamente.",
    ("gerente", "Mobiliario especial"): "está firme, estable y sin daños.",
    ("gerente", "Confort"): "funciona y está completo.",
    ("gerente", "Baño"): "funciona sin fugas ni daños.",
    (
        "ama_llaves",
        "Entretenimiento",
    ): "está limpio y, si tiene control, el control está en su lugar.",
    ("ama_llaves", "Mobiliario especial"): "está limpio, desinfectado y en su lugar.",
    ("ama_llaves", "Confort"): "está limpio, surtido y en su lugar.",
    ("ama_llaves", "Baño"): "está limpio y sin residuos.",
}
_CRITERIO_GENERAL = {
    "gerente": "funciona correctamente y está en buen estado.",
    "ama_llaves": "está limpio y en su lugar.",
}


def punto_de_equipo(rol: str, equipo_id: int, nombre: str, categoria: str) -> Punto:
    criterio = _CRITERIO.get((rol, categoria), _CRITERIO_GENERAL[rol])
    return Punto(
        codigo=f"E{equipo_id:02d}",
        rol=rol,
        seccion=SECCION_EQUIPO,
        titulo=nombre[:80],
        texto=f"{nombre}: {criterio}",
    )
