# -*- coding: utf-8 -*-
"""Gestor de Crianza de Reinas (Streamlit).

Requiere Streamlit >= 1.39. Para guardar los datos de forma permanente
configura Supabase (ver la pestaña "Ajustes" dentro de la app).
"""
import calendar
import copy
import hashlib
import html
import json
import os
import re
import uuid
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Gestor Apícola de Reinas", page_icon="🐝", layout="wide")

# ---------------------------------------------------------------------------
# ZONA HORARIA (Perú: UTC-5, sin horario de verano)
# ---------------------------------------------------------------------------
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/Lima")
except Exception:
    TZ = timezone(timedelta(hours=-5))


def hoy_peru():
    return datetime.now(TZ).date()


# ---------------------------------------------------------------------------
# CONSTANTES
# ---------------------------------------------------------------------------
ARCHIVO_DATOS = "lotes_reinas.json"
TABLA = "estado_app"
CLAVE_ESTADO = "reinas"
VERSION_DATOS = 3

COLORES = ["#ff9999", "#66b3ff", "#99ff99", "#ffcc99", "#c299ff", "#ff99ff", "#ffe666",
           "#8fd9c7", "#f2a65a", "#b5e48c"]
DIAS_SEMANA = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]
DIAS_SEMANA_LARGO = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES_ES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
TIPOS_CRIANZA = ["Sin especificar", "Traslarve (Doolittle)", "Sistema Jenter / Nicot",
                 "Cupularve", "Celdas de emergencia", "Otro"]

# Rango de días (respecto al traslarve) que se pueden usar en las actividades
DIA_MIN, DIA_MAX = -30, 365

# Estados de las tareas: clave -> (icono, nombre, sufijo para CSS)
ESTADOS = {
    "pendiente": ("⏳", "Pendiente", "pend"),
    "completada": ("✅", "Completada", "comp"),
    "no_realizada": ("⏭️", "No realizada", "nore"),
    "vencida": ("⚠️", "Vencida", "venc"),
    "info": ("ℹ️", "Solo aviso (no hay que hacer nada)", "info"),
}

# Cantidades registradas por etapa (en orden) y porcentajes entre etapas
ETAPAS = [
    ("cant_traslarve", "Larvas traslarvadas"),
    ("celdas_aceptadas", "Celdas aceptadas"),
    ("celdas_operculadas", "Celdas operculadas"),
    ("celdas_insertadas", "Celdas insertadas en núcleos"),
    ("reinas_nacidas", "Reinas nacidas"),
    ("reinas_fecundadas", "Reinas fecundadas con postura"),
]
ETIQUETA = dict(ETAPAS)
RATIOS = [
    ("Aceptación", "celdas_aceptadas", "cant_traslarve"),
    ("Operculación", "celdas_operculadas", "celdas_aceptadas"),
    ("Inserción", "celdas_insertadas", "celdas_operculadas"),
    ("Nacimiento", "reinas_nacidas", "celdas_insertadas"),
    ("Fecundación", "reinas_fecundadas", "reinas_nacidas"),
    ("Éxito final", "reinas_fecundadas", "cant_traslarve"),
]

# Calidad de los datos de un lote (para decidir si entra en las estadísticas)
CALIDADES = {
    "validos": ("🟢", "Datos válidos"),
    "incompletos": ("🟡", "Datos incompletos"),
    "incoherentes": ("🔴", "Datos con incoherencias"),
}

# Alimentación del lote
CLASES_ALIM = ["Energética", "Proteica", "Energética y proteica"]
ENERGETICA_DEF = "Jarabe"
PROTEICA_DEF = "Torta proteica"
OPCIONES_ENERGETICA = [ENERGETICA_DEF]
OPCIONES_PROTEICA = [PROTEICA_DEF, "Aminoácidos"]
OTRO_ALIMENTO = "Otro (escribir)"

# ---------------------------------------------------------------------------
# GUÍAS DE CADA TAREA
# ---------------------------------------------------------------------------
GUIA_TRASLARVE = """
**¿Qué es?**
Es pasar larvas recién nacidas (de menos de 24 horas) desde las celdas de obrera de tu mejor colmena hacia copas artificiales de cera o plástico. Una colmena iniciadora las alimenta con mucha jalea real y las convierte en reinas.

**Cómo se hace**
1. **Prepara la iniciadora:** una colmena fuerte, bien alimentada (jarabe), con muchas abejas nodrizas y sin reina o con la reina aislada.
2. **Consigue larvas de la edad justa:** deja que la reina madre ponga en un panal limpio. Los huevos eclosionan a los 3 días, así que el traslarve se hace cuando las larvas tienen menos de 24 h de nacidas (alrededor del día 4 de la postura).
3. **Trabaja en un lugar cálido, húmedo y sin viento** (cubre con un paño húmedo): las larvas se secan y mueren muy rápido.
4. **Con la aguja de traslarve**, levanta cada larva por debajo, sin tocarla ni voltearla, y deposítala en el fondo de la copa (si quieres, sobre una gota de jalea real diluida).
5. **Coloca enseguida el marco con las copas** en la iniciadora.
6. **Al día siguiente** revisa cuántas copas aceptaron las abejas y anótalo en "Cantidades".
"""

GUIA_NUCLEOS = """
**¿Qué es?**
Un núcleo es una colmena pequeña (2 a 5 cuadros) donde la reina va a nacer, salir a aparearse y empezar a poner.

⚠️ **El núcleo NO debe tener reina.** Si tiene una, atacará la celda real o a la reina virgen que nazca.

**Opción 1: armar un núcleo nuevo**
1. Toma 2 o 3 cuadros: uno o dos con cría operculada y naciente, y uno con miel y polen, con muchas abejas jóvenes encima.
2. **Revisa cuadro por cuadro que no pase la reina** a la caja.
3. Colócalos en la caja de núcleo y completa con un cuadro con cera si hace falta.
4. Reduce la piquera y dales jarabe. Las pecoreadoras vuelven a su colmena de origen, así que añade abejas jóvenes extra (sacude un cuadro más) o lleva el núcleo a un apiario a 3 km o más.

**Opción 2: usar una colmena o núcleo que ya existe**
No hace falta armar uno nuevo: puedes sacarle la reina a una colmena o núcleo existente (guárdala en una jaula para usarla en otro lado). Así queda huérfano y listo para recibir la celda.

💡 Con 1 o 2 días sin reina aceptan mejor la celda. Pero pueden empezar a criar celdas de emergencia: **destrúyelas** antes de introducir la celda real.
"""

GUIA_CELDAS = """
**¿Qué es?**
Es el momento de introducir las celdas reales (ya operculadas) en los núcleos o colmenas huérfanas que preparaste en "Preparar núcleos".

**Cómo se hace**
1. **Revisa el núcleo o la colmena antes:** confirma que no tiene reina y destruye cualquier celda de emergencia.
2. **Saca las celdas de la iniciadora con cuidado.** Sujétalas por la parte ancha (la base), nunca por la punta, y no las golpees ni las sacudas.
3. **Protégelas del frío y del sol:** llévalas en un recipiente tibio y con tapa, y colócalas cuanto antes.
4. **Colócala entre dos cuadros de cría**, con la punta hacia abajo: con un protector de celda o presionando suavemente la base contra el panal, sin aplastarla.
5. **Cierra y déjalo tranquilo.** La reina nace unos 12 días después del traslarve; evita abrir más de lo necesario.
"""

GUIA_NACIMIENTO = """
**¿Qué pasa?**
Las reinas nacen de sus celdas (aprox. 12 días después del traslarve).

**Qué hacer**
- **Nada: aquí no se debe hacer ninguna intervención.** Deja los núcleos tranquilos.
- Evita abrir los núcleos estos días: podrías perjudicar a la reina durante los vuelos de fecundación.
- Cuando lo sepas, anota cuántas nacieron en "Cantidades".
- La reina virgen sale a aparearse a partir de los 5-6 días de vida y empieza a poner 2 o 3 días después.
"""

GUIA_POSTURA = """
**¿Qué es?**
Es la primera inspección para confirmar que la reina nació, se apareó y ya está poniendo huevos.

**Cómo se hace**
1. **Elige un día cálido y soleado**, en las horas centrales, con las pecoreadoras activas.
2. **Busca huevos:** uno por celda, en el fondo, y larvas pequeñas. Un patrón de cría compacto indica una buena reina.
3. **Si hay huevos, la reina está lista.** Anótala en "Cantidades" (reinas fecundadas con postura).
4. **Si todavía no hay huevos**, espera unos días y revisa de nuevo (hasta cerca del día 28). Si sigue sin poner, es posible que se perdiera en el vuelo de fecundación: une el núcleo a otro o dale otra celda.

**🎨 Pinta (marca) la reina**
Es muy recomendable hacerlo cuando ya está poniendo:
- Atrápala con suavidad por el tórax o con un tubo/jaula de marcaje.
- Pon un punto pequeño de pintura no tóxica para reinas sobre el tórax, sin tocar cabeza, alas ni abdomen.
- Deja secar unos segundos antes de soltarla sobre el panal.
- Así la encuentras más fácil y sabes su edad por el color del año.
"""

# ---------------------------------------------------------------------------
# ACTIVIDADES PREDEFINIDAS (valores de fábrica; se pueden cambiar en Ajustes)
#   fija   -> el traslarve es siempre el día 0 y no se puede desactivar
#   accion -> False = solo aviso: no hay que hacer nada (nunca queda "vencida")
# ---------------------------------------------------------------------------
ACTIVIDADES_BASE = [
    {"id": "traslarve", "titulo": "Traslarve", "dias": 0, "corto": "Traslarve", "icono": "🥚",
     "guia": GUIA_TRASLARVE, "accion": True, "fija": True},
    {"id": "nucleos", "titulo": "Preparar núcleos", "dias": 8, "corto": "Núcleos", "icono": "📦",
     "guia": GUIA_NUCLEOS, "accion": True, "fija": False},
    {"id": "celdas", "titulo": "Insertar celdas", "dias": 10, "corto": "Celdas", "icono": "🧬",
     "guia": GUIA_CELDAS, "accion": True, "fija": False},
    {"id": "nacimiento", "titulo": "Nacimiento", "dias": 12, "corto": "Nacim.", "icono": "👑",
     "guia": GUIA_NACIMIENTO, "accion": False, "fija": False},
    {"id": "postura", "titulo": "Primera revisión de postura", "dias": 24, "corto": "Postura", "icono": "🔍",
     "guia": GUIA_POSTURA, "accion": True, "fija": False},
]
BASE_POR_ID = {b["id"]: b for b in ACTIVIDADES_BASE}
ORDEN_BASE = [b["id"] for b in ACTIVIDADES_BASE]

# Código internacional de colores para marcar reinas (según el año)
COLOR_MARCA = {1: ("blanco", "⚪"), 2: ("amarillo", "🟡"), 3: ("rojo", "🔴"), 4: ("verde", "🟢"), 0: ("azul", "🔵")}


def color_marca(anio):
    return COLOR_MARCA[anio % 5]


# ---------------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------------
def nuevo_id():
    return uuid.uuid4().hex[:8]


def entero(v, defecto=0, minimo=0):
    try:
        return max(minimo, int(v))
    except (TypeError, ValueError):
        return defecto


def color_valido(c):
    return bool(re.fullmatch(r"#[0-9a-fA-F]{6}", str(c)))


def esc_md(texto):
    """Escapa caracteres de Markdown (para etiquetas con texto del usuario)."""
    return re.sub(r"([\\`*_\[\]~$<>])", r"\\\1", str(texto))


def limpiar_id(v):
    return re.sub(r"[^0-9A-Za-z]", "", str(v or ""))


def pct(num, den):
    """Porcentaje; None si falta el dato (sin registrar) o el divisor es 0."""
    return None if (num is None or not den) else num / den * 100


def fmt_pct(p):
    return "—" if p is None else f"{p:.1f}%"


def fmt_n(v):
    return "—" if v is None else str(v)


def cifra(d, campo):
    """Valor numérico de una etapa (0 si todavía no se registró)."""
    return d.get(campo) or 0


def plural(n, singular, plural_):
    return f"{n} {singular if n == 1 else plural_}"


# ---------------------------------------------------------------------------
# ACTIVIDADES: normalización y consultas
# ---------------------------------------------------------------------------
def dia_valido(v, defecto, minimo):
    return min(DIA_MAX, entero(v, defecto, minimo))


def normalizar_actividad(a):
    """Devuelve una actividad limpia: {id, titulo, dias, activa, accion, nota}."""
    aid = limpiar_id(a.get("id")) or ("x" + nuevo_id())
    base = BASE_POR_ID.get(aid)
    if base:   # las predefinidas conservan nombre y tipo; solo cambian día y estado
        return {"id": aid, "titulo": base["titulo"],
                "dias": 0 if base["fija"] else dia_valido(a.get("dias"), base["dias"], 1),
                "activa": True if base["fija"] else bool(a.get("activa", True)),
                "accion": base["accion"], "nota": ""}
    titulo = str(a.get("titulo") or "").strip()[:60] or "Actividad"
    return {"id": aid, "titulo": titulo, "dias": dia_valido(a.get("dias"), 1, DIA_MIN),
            "activa": bool(a.get("activa", True)), "accion": bool(a.get("accion", True)),
            "nota": str(a.get("nota") or "").strip()[:500]}


def _normalizar_lista(lista):
    vistos, out = set(), []
    for a in lista or []:
        if not isinstance(a, dict):
            continue
        n = normalizar_actividad(a)
        if n["id"] not in vistos:
            vistos.add(n["id"])
            out.append(n)
    return out, vistos


def normalizar_catalogo(lista):
    """Catálogo de Ajustes: siempre incluye las 5 actividades predefinidas."""
    out, vistos = _normalizar_lista(lista)
    for b in ACTIVIDADES_BASE:
        if b["id"] not in vistos:
            out.append(normalizar_actividad(dict(b)))
    return out


def normalizar_actividades_lote(lista):
    """Actividades de un lote: el traslarve (día 0) nunca falta."""
    out, vistos = _normalizar_lista(lista)
    if "traslarve" not in vistos:
        out.insert(0, normalizar_actividad(dict(BASE_POR_ID["traslarve"])))
    return out


def config_por_defecto():
    return {"actividades": normalizar_catalogo(None)}


def firma_config(config):
    """Cambia cuando cambian las actividades de Ajustes (renueva los campos del formulario de lote nuevo)."""
    datos = [(a["id"], a["titulo"], a["dias"], a["activa"], a["accion"]) for a in config["actividades"]]
    return hashlib.md5(json.dumps(datos, sort_keys=True).encode("utf-8")).hexdigest()[:6]


def acts_ordenadas(lote):
    return sorted(lote["actividades"], key=lambda a: (a["dias"], a["titulo"]))


def acts_activas(lote):
    return [a for a in acts_ordenadas(lote) if a["activa"]]


def buscar_act(lote, act_id):
    return next((a for a in lote["actividades"] if a["id"] == act_id), None)


def info_act(act):
    """Icono, nombre corto y guía de una actividad (las propias usan su descripción)."""
    base = BASE_POR_ID.get(act["id"])
    if base:
        return {"icono": base["icono"], "corto": base["corto"], "guia": base["guia"]}
    return {"icono": "📌" if act["accion"] else "ℹ️", "corto": act["titulo"][:9],
            "guia": act["nota"] or "_Esta actividad no tiene descripción._"}


def fecha_act(lote, act):
    return lote["traslarve_fecha"] + timedelta(days=act["dias"])


def nombre_act(act):
    return f"{act['titulo']} (Día {act['dias']})"


def estado_tarea(lote, act, hoy):
    """info / pendiente / completada / no_realizada / vencida (esta última se calcula sola)."""
    if not act["accion"]:
        return "info"
    manual = lote["tareas"].get(act["id"])
    if manual in ("completada", "no_realizada"):
        return manual
    return "vencida" if fecha_act(lote, act) < hoy else "pendiente"


def validar_actividades(acts):
    """Devuelve un mensaje de error o None. Las predefinidas activas deben ir en orden creciente."""
    for a in acts:
        if not str(a["titulo"]).strip():
            return "Todas las actividades necesitan un nombre."
    base = sorted((a for a in acts if a["id"] in BASE_POR_ID and a["activa"]),
                  key=lambda a: ORDEN_BASE.index(a["id"]))
    for ant, act in zip(base, base[1:]):
        if act["dias"] <= ant["dias"]:
            return (f"'{act['titulo']}' (día {act['dias']}) debe ser posterior a "
                    f"'{ant['titulo']}' (día {ant['dias']}).")
    return None


# ---------------------------------------------------------------------------
# ALIMENTACIÓN
# ---------------------------------------------------------------------------
def normalizar_alimentacion(a):
    """con=None -> sin registrar (lotes antiguos); False -> sin alimentación; True -> con alimentación."""
    if not isinstance(a, dict) or a.get("con") is None:
        return {"con": None, "energetica": "", "proteica": ""}
    con = bool(a.get("con"))
    en = str(a.get("energetica") or "").strip()[:60] if con else ""
    pr = str(a.get("proteica") or "").strip()[:60] if con else ""
    if con and not en and not pr:
        con = False
    return {"con": con, "energetica": en, "proteica": pr}


def texto_alimentacion(al):
    if al.get("con") is None:
        return "Alimentación sin registrar"
    if not al["con"]:
        return "Sin alimentación"
    partes = []
    if al["energetica"]:
        partes.append(f"energética: {al['energetica']}")
    if al["proteica"]:
        partes.append(f"proteica: {al['proteica']}")
    return "Alimentación " + " + ".join(partes)


# ---------------------------------------------------------------------------
# LOTES: modelo de datos
# ---------------------------------------------------------------------------
def valor_etapa(v, tope):
    """None = todavía no registrado (no es lo mismo que 0)."""
    if v is None or v == "":
        return None
    return min(entero(v), tope)


def lote_desde_dict(d, indice=0, legacy=False):
    """Crea un lote a partir de un diccionario (acepta formatos antiguos).

    legacy=True: datos guardados antes de distinguir «sin registrar» de 0; los ceros del final
    (etapas posteriores a la última con datos) pasan a «sin registrar».
    """
    cant = entero(d.get("cant_traslarve"), 1, 1)
    if d.get("actividades"):
        acts = normalizar_actividades_lote(d["actividades"])
    else:   # formato antiguo: solo había 5 etapas con sus días
        viejos = d.get("dias") or {}
        acts = []
        for b in ACTIVIDADES_BASE:
            a = dict(b)
            if not b["fija"] and b["id"] in viejos:
                a["dias"] = viejos[b["id"]]
            acts.append(normalizar_actividad(a))
    ids = {a["id"] for a in acts}
    tareas = {k: v for k, v in (d.get("tareas") or {}).items()
              if k in ids and v in ("completada", "no_realizada")}
    manual = d.get("calidad_manual")
    lote = {
        "id": limpiar_id(d.get("id")) or nuevo_id(),
        "nombre": str(d["nombre"]),
        "traslarve_fecha": datetime.fromisoformat(str(d["traslarve_fecha"])).date(),
        "cant_traslarve": cant,
        "actividades": acts,
        "tareas": tareas,
        "color": d.get("color") if color_valido(d.get("color")) else COLORES[indice % len(COLORES)],
        "tipo_crianza": str(d.get("tipo_crianza") or TIPOS_CRIANZA[0]),
        "apiario": str(d.get("apiario") or ""),
        "colmena_madre": str(d.get("colmena_madre") or ""),
        "observaciones": str(d.get("observaciones") or ""),
        "archivado": bool(d.get("archivado", False)),
        "alimentacion": normalizar_alimentacion(d.get("alimentacion")),
        "calidad_manual": manual if manual in CALIDADES else None,
    }
    # "cant_celdas" es el nombre antiguo de las celdas aceptadas
    lote["celdas_aceptadas"] = valor_etapa(d.get("celdas_aceptadas", d.get("cant_celdas")), cant)
    for campo, _ in ETAPAS[2:]:
        lote[campo] = valor_etapa(d.get(campo), cant)
    if legacy:
        campos = [c for c, _ in ETAPAS[1:]]
        ultimo = max((i for i, c in enumerate(campos) if lote[c]), default=-1)
        for c in campos[ultimo + 1:]:
            lote[c] = None
    return lote


def serializar_lote(lote):
    d = {k: copy.deepcopy(v) for k, v in lote.items() if k != "traslarve_fecha"}
    d["traslarve_fecha"] = lote["traslarve_fecha"].isoformat()
    return d


def datos_para_guardar(config, lotes):
    return {"version": VERSION_DATOS,
            "config": {"actividades": copy.deepcopy(config["actividades"])},
            "lotes": [serializar_lote(l) for l in lotes]}


def estado_desde_datos(datos):
    """(config, lotes) desde datos JSON. Lanza excepción si el formato no es válido."""
    legacy, cfg = True, {}
    if isinstance(datos, list):          # formato antiguo: solo la lista de lotes
        lista = datos
    elif isinstance(datos, dict):
        lista = datos["lotes"]
        cfg = datos.get("config") or {}
        legacy = entero(datos.get("version"), 1) < VERSION_DATOS
    else:
        raise ValueError("formato no reconocido")
    # Los días por defecto del formato antiguo (cfg["dias"]) se reemplazan por los nuevos valores de fábrica
    catalogo = normalizar_catalogo(None if legacy else cfg.get("actividades"))
    return {"actividades": catalogo}, [lote_desde_dict(d, i, legacy) for i, d in enumerate(lista)]


# ---------------------------------------------------------------------------
# CALIDAD DE LOS DATOS Y PORCENTAJES
# ---------------------------------------------------------------------------
def incoherencias(d):
    """Etapas que superan a la etapa registrada anterior (ej.: más operculadas que aceptadas)."""
    avisos, previo = [], None
    for campo, _ in ETAPAS:
        v = d[campo]
        if v is None:
            continue
        if previo is not None and v > d[previo]:
            avisos.append(f"{ETIQUETA[campo]} ({v}) supera a {ETIQUETA[previo].lower()} ({d[previo]}).")
        previo = campo
    return avisos


def calidad_auto(d):
    if incoherencias(d):
        return "incoherentes"
    if any(d[c] is None for c, _ in ETAPAS[1:]):
        return "incompletos"
    return "validos"


def calidad(d):
    """Calidad elegida por el usuario o, si no eligió, la calculada automáticamente."""
    return d.get("calidad_manual") or calidad_auto(d)


def lineas_porcentajes(d):
    out = []
    for nombre, num, den in RATIOS:
        p = pct(d[num], d[den])
        detalle = f" ({d[num]}/{d[den]})" if p is not None else ""
        out.append(f"- **{nombre}:** {fmt_pct(p)}{detalle}")
    return "\n".join(out)


def calcular_recordatorios(lotes, hoy):
    hoy_l, manana_l, vencidas, pendientes, avisos = [], [], {}, 0, []
    for l in lotes:
        if l["archivado"]:
            continue
        for act in acts_activas(l):
            est = estado_tarea(l, act, hoy)
            f = fecha_act(l, act)
            texto = f"{act['titulo']} · {l['nombre']}"
            if est == "pendiente":
                pendientes += 1
                if f == hoy:
                    hoy_l.append(texto)
                elif f == hoy + timedelta(days=1):
                    manana_l.append(texto)
            elif est == "vencida":
                vencidas.setdefault(l["nombre"], []).append(act["titulo"])
            elif est == "info":
                if f == hoy:
                    avisos.append(f"{texto} (hoy)")
                elif f == hoy + timedelta(days=1):
                    avisos.append(f"{texto} (mañana)")
    return hoy_l, manana_l, vencidas, pendientes, avisos


# ---------------------------------------------------------------------------
# EXPORTAR A CALENDARIO (.ics, compatible con Google Calendar / iPhone)
# ---------------------------------------------------------------------------
def ics_texto(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def plegar(linea):
    """Las líneas de un .ics no pueden pasar de 75 bytes."""
    b = linea.encode("utf-8")
    partes, limite = [], 75
    while len(b) > limite:
        corte = limite
        while (b[corte] & 0xC0) == 0x80:
            corte -= 1
        partes.append(b[:corte].decode("utf-8"))
        b, limite = b[corte:], 74
    partes.append(b.decode("utf-8"))
    return "\r\n ".join(partes)


def generar_ics(lotes, hoy):
    """Eventos de día completo con aviso a las 8:00 para las tareas pendientes."""
    ahora = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Gestor Apicola de Reinas//ES",
         "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Crianza de reinas"]
    for lote in lotes:
        for act in acts_activas(lote):
            if estado_tarea(lote, act, hoy) != "pendiente":
                continue
            f = fecha_act(lote, act)
            detalle = [f"Lote: {lote['nombre']}", nombre_act(act)]
            if lote["apiario"]:
                detalle.append(f"Apiario: {lote['apiario']}")
            L += ["BEGIN:VEVENT",
                  f"UID:{lote['id']}-{act['id']}@gestor-reinas",
                  f"DTSTAMP:{ahora}",
                  f"DTSTART;VALUE=DATE:{f:%Y%m%d}",
                  f"DTEND;VALUE=DATE:{f + timedelta(days=1):%Y%m%d}",
                  "SUMMARY:" + ics_texto(f"🐝 {lote['nombre']}: {act['titulo']}"),
                  "DESCRIPTION:" + ics_texto("\n".join(detalle)),
                  "TRANSP:TRANSPARENT",
                  "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Recordatorio", "TRIGGER:PT8H", "END:VALARM",
                  "END:VEVENT"]
    L.append("END:VCALENDAR")
    return "\r\n".join(plegar(x) for x in L) + "\r\n"


# ---------------------------------------------------------------------------
# ALMACENAMIENTO: Supabase (permanente) o archivo local (se pierde al reiniciar)
# ---------------------------------------------------------------------------
def problema_simple(titulo, detalle, tecnico=""):
    return {"configurado": True, "titulo": titulo, "detalle": detalle, "tecnico": tecnico}


NO_CONFIGURADO = {
    "configurado": False,
    "titulo": "Supabase todavía no está configurado",
    "detalle": ("No encontré la sección `[supabase]` en Secrets, así que los datos se guardan solo en un "
                "archivo temporal del servidor. Sigue los pasos de «Cómo activar el almacenamiento permanente»."),
    "tecnico": "",
}


def explicar_error_supabase(e, accion="conectar"):
    """Traduce un error de Supabase a una explicación con pasos concretos."""
    tecnico = f"{type(e).__name__}: {e}"
    b = tecnico.lower()
    codigo = str(getattr(e, "code", "") or "")
    titulo = {"conectar": "No se pudo conectar con Supabase",
              "leer": "No se pudieron leer los datos de Supabase",
              "guardar": "No se pudieron guardar los datos en Supabase"}[accion]

    if isinstance(e, ImportError) or "no module named" in b:
        causa = ("Falta la librería `supabase` en el servidor. Agrega una línea `supabase` a tu "
                 "`requirements.txt` y reinicia la app (Reboot).")
    elif codigo in ("PGRST205", "42P01") or "could not find the table" in b or \
            ("relation" in b and "does not exist" in b):
        causa = (f"La conexión funciona, pero **la tabla `{TABLA}` no existe** en tu proyecto. "
                 "Entra a Supabase → **SQL Editor**, ejecuta el código SQL que aparece en Ajustes "
                 "(«Cómo activar el almacenamiento permanente») y vuelve a probar.")
    elif codigo == "42501" or "row-level security" in b or "permission denied" in b:
        causa = ("Supabase **rechazó el permiso** para escribir en la tabla. Casi siempre pasa porque en Secrets "
                 "pusiste la clave pública (`anon`). Usa la clave secreta **service_role** (o la que empieza "
                 "con `sb_secret_`): Supabase → Project Settings → API.")
    elif "invalid api key" in b or "jwt" in b or "unauthorized" in b or codigo.startswith("PGRST30"):
        causa = ("Supabase **no aceptó la clave** (`key`). Revisa que sea la clave completa de tu proyecto "
                 "(service_role), sin espacios ni comillas de más, y que la `url` sea del mismo proyecto.")
    elif any(x in b for x in ("getaddrinfo", "name or service not known", "nodename nor servname",
                              "temporary failure in name resolution", "connecterror", "connection refused",
                              "all connection attempts failed", "timed out", "timeout",
                              "network is unreachable", "ssl", "certificate")):
        causa = ("**No se pudo llegar al servidor de Supabase.** Las causas más comunes son: "
                 "(1) la `url` en Secrets está mal escrita; (2) tu proyecto gratuito está **pausado** por "
                 "inactividad (entra a supabase.com → tu proyecto → *Restore project*); "
                 "(3) hubo un corte de internet en el servidor o en tu red.")
    elif any(x in b for x in ("502", "503", "504", "bad gateway", "service unavailable")):
        causa = ("Supabase no está respondiendo (servicio caído, en mantenimiento o proyecto pausado). "
                 "Espera unos minutos y reintenta; si el proyecto está pausado, restáuralo en supabase.com.")
    elif "invalid url" in b or "invalid_url" in b:
        causa = "La `url` en Secrets no es válida. Debe verse como `https://TU-PROYECTO.supabase.co`."
    else:
        causa = ("Ocurrió un error que no reconozco. Revisa el detalle técnico de abajo; "
                 "si no entiendes el mensaje, cópialo y consúltalo.")
    return {"configurado": True, "titulo": titulo, "detalle": causa, "tecnico": tecnico}


def revisar_credenciales(url, key):
    """Detecta errores evidentes al escribir los Secrets. Devuelve un problema o None."""
    if "TU-PROYECTO" in url or "TU_CLAVE" in key:
        return problema_simple(
            "Todavía tienes el texto de ejemplo en Secrets",
            "Reemplaza `TU-PROYECTO` y `TU_CLAVE_SERVICE_ROLE` por tus datos reales "
            "(Supabase → Project Settings → API).")
    if not url.startswith("https://") or url.rstrip("/").count("/") > 2:
        return problema_simple(
            "La `url` de Supabase no tiene el formato correcto",
            "Debe ser solo la dirección del proyecto, por ejemplo `https://abcdefgh.supabase.co`: "
            "empieza con https:// y no lleva nada después (ni `/rest/v1`).", f"url = {url}")
    if len(key) < 20 or any(c.isspace() for c in key):
        return problema_simple(
            "La clave (`key`) de Supabase parece incompleta",
            "Copia la clave completa desde Supabase → Project Settings → API, sin espacios ni saltos de línea.")
    return None


@st.cache_resource
def _crear_cliente(url, key):
    """Si falla lanza una excepción: Streamlit no guarda los fallos en caché."""
    from supabase import create_client
    return create_client(url, key)


def _secreto(seccion, nombre):
    try:
        return str(seccion[nombre]).strip()
    except Exception:
        return ""


def conectar_supabase():
    """Devuelve (cliente, problema). Sin cliente y con problema['configurado'] False = no se intentó configurar."""
    try:
        sec = st.secrets["supabase"]
    except Exception:
        return None, NO_CONFIGURADO
    url, key = _secreto(sec, "url"), _secreto(sec, "key")
    if not url or not key:
        faltan = " y ".join(n for n, v in (("url", url), ("key", key)) if not v)
        return None, problema_simple(
            "Faltan datos en Secrets",
            f"La sección `[supabase]` existe, pero falta: **{faltan}**. Debe tener las dos líneas "
            "`url = \"...\"` y `key = \"...\"`.")
    problema = revisar_credenciales(url, key)
    if problema:
        return None, problema
    try:
        return _crear_cliente(url, key), None
    except Exception as e:
        return None, explicar_error_supabase(e, "conectar")


def probar_supabase():
    """Prueba leer y escribir en la tabla. Devuelve un problema o None si todo funciona."""
    cli, problema = conectar_supabase()
    if cli is None:
        return problema
    try:
        cli.table(TABLA).select("id").limit(1).execute()
    except Exception as e:
        return explicar_error_supabase(e, "leer")
    try:   # fila de prueba: comprueba también el permiso de escritura
        cli.table(TABLA).upsert({"id": "_prueba", "datos": {"ok": True}}).execute()
        cli.table(TABLA).delete().eq("id", "_prueba").execute()
    except Exception as e:
        return explicar_error_supabase(e, "guardar")
    return None


def mostrar_problema(p):
    if p.get("configurado", True):
        st.error(f"⚠️ **{p['titulo']}**\n\n{p['detalle']}")
    else:
        st.warning(f"⚠️ **{p['titulo']}**\n\n{p['detalle']}")
    if p.get("tecnico"):
        with st.expander("Ver el detalle técnico del error"):
            st.code(p["tecnico"], language=None)


def leer_local():
    if not os.path.exists(ARCHIVO_DATOS):
        return None
    with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
        return json.load(f)


def escribir(config, lotes):
    """Guarda los datos. Devuelve un problema (dict) o None si todo salió bien."""
    datos = datos_para_guardar(config, lotes)
    cli, _ = conectar_supabase()
    error = None
    if cli:
        try:
            cli.table(TABLA).upsert({"id": CLAVE_ESTADO, "datos": datos}).execute()
        except Exception as e:
            error = explicar_error_supabase(e, "guardar")
    local_ok, err_local = True, None
    try:
        with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
    except OSError as e:
        local_ok, err_local = False, e
    if cli is None and not local_ok:
        error = problema_simple("No se pudo guardar el archivo", "El servidor no permitió escribir el archivo "
                                "temporal con tus datos. Descarga un respaldo en Ajustes.", str(err_local))
    elif error and local_ok:
        error["detalle"] += ("\n\nMientras tanto tus datos quedaron en un archivo temporal del servidor "
                             "(se puede perder al reiniciar la app). Descarga un respaldo en Ajustes.")
    return error


def cargar_todo():
    """Devuelve (config, lotes, error_carga, modo, error_guardado). Nunca sobrescribe datos si hay error."""
    cli, _ = conectar_supabase()
    modo = "nube" if cli else "local"
    vacia = config_por_defecto()
    datos, migrar = None, False
    if cli:
        try:
            r = cli.table(TABLA).select("datos").eq("id", CLAVE_ESTADO).execute()
            if r.data:
                datos = r.data[0]["datos"]
        except Exception as e:
            return vacia, [], explicar_error_supabase(e, "leer"), modo, None
    if datos is None:
        try:
            datos = leer_local()
        except Exception as e:
            return vacia, [], problema_simple(
                "No se pudo leer el archivo temporal de datos",
                "El archivo existe pero no se pudo leer. Restaura un respaldo en Ajustes.",
                f"{type(e).__name__}: {e}"), modo, None
        migrar = cli is not None and datos is not None
    if datos is None:
        return vacia, [], None, modo, None
    try:
        config, lotes = estado_desde_datos(datos)
    except Exception as e:
        return vacia, [], problema_simple(
            "Los datos guardados no tienen un formato válido",
            "La app no pudo interpretar los datos. No se guardará nada para no perder información: "
            "restaura un respaldo en Ajustes.", f"{type(e).__name__}: {e}"), modo, None
    error_guardado = None
    if migrar:  # primera vez con Supabase: sube lo que había en el archivo local
        error_guardado = escribir(config, lotes)
    return config, lotes, None, modo, error_guardado


def recargar_datos():
    """Vuelve a intentar la conexión y a leer todos los datos desde cero."""
    _crear_cliente.clear()
    for k in ("lotes", "config", "error_carga", "error_guardado", "modo"):
        st.session_state.pop(k, None)
    st.rerun()


def guardar():
    """Guarda el estado de la sesión. No guarda si hubo un error al cargar (evita perder datos)."""
    if st.session_state.error_carga:
        st.session_state.error_guardado = problema_simple(
            "No se guardó nada",
            "Hubo un error al cargar los datos y, para no perder información, no se guarda hasta resolverlo. "
            "Reintenta la conexión o restaura un respaldo.")
        return
    st.session_state.error_guardado = escribir(st.session_state.config, st.session_state.lotes)


def buscar_lote(lote_id):
    return next((l for l in st.session_state.lotes if l["id"] == lote_id), None)


def marcar(lote, act_id, estado):
    if estado == "pendiente":
        lote["tareas"].pop(act_id, None)
    else:
        lote["tareas"][act_id] = estado
    guardar()


# ---------------------------------------------------------------------------
# VENTANAS (diálogos)
# ---------------------------------------------------------------------------
@st.dialog("🐝 Guía de la tarea")
def mostrar_guia(lote_id, act_id):
    lote = buscar_lote(lote_id)
    act = buscar_act(lote, act_id) if lote else None
    if lote is None or act is None:
        st.warning("No se encontró la actividad.")
        return
    info = info_act(act)
    est = estado_tarea(lote, act, hoy_peru())
    icono, nombre_est, _ = ESTADOS[est]
    st.markdown(f"### {info['icono']} {esc_md(nombre_act(act))}")
    st.caption(f"Lote: {esc_md(lote['nombre'])} · {fecha_act(lote, act):%d/%m/%Y} · {icono} {nombre_est}")
    if act["accion"]:
        c1, c2, c3 = st.columns(3)
        if c1.button("✅ Completada", key="dlg_comp"):
            marcar(lote, act_id, "completada")
            st.rerun()
        if c2.button("⏭️ No realizada", key="dlg_nore"):
            marcar(lote, act_id, "no_realizada")
            st.rerun()
        if c3.button("↩️ Pendiente", key="dlg_pend"):
            marcar(lote, act_id, "pendiente")
            st.rerun()
    else:
        st.info("Esta actividad es solo un aviso: no hay nada que hacer ni que marcar.")
    st.markdown("---")
    st.markdown(info["guia"])
    if act_id == "postura":
        nombre_color, emoji = color_marca(lote["traslarve_fecha"].year)
        st.info(f"Color para marcar las reinas de este lote: {emoji} **{nombre_color}** "
                f"(código internacional para el año {lote['traslarve_fecha'].year}).")


@st.dialog("🗑️ Eliminar lote")
def confirmar_eliminar(lote_id):
    lote = buscar_lote(lote_id)
    if lote is None:
        st.rerun()
        return
    st.warning(f"¿Seguro que quieres eliminar **{esc_md(lote['nombre'])}**? Se perderán sus tareas, "
               "cantidades y observaciones. Esta acción no se puede deshacer.")
    c1, c2 = st.columns(2)
    if c1.button("Sí, eliminar", type="primary", key="dlg_del_si"):
        st.session_state.lotes[:] = [l for l in st.session_state.lotes if l["id"] != lote_id]
        guardar()
        st.session_state.mensaje = "Lote eliminado."
        st.rerun()
    if c2.button("Cancelar", key="dlg_del_no"):
        st.rerun()


# ---------------------------------------------------------------------------
# COMPONENTES DE INTERFAZ
# ---------------------------------------------------------------------------
def boton_tarea(ctx, lote, act, etiqueta, hoy):
    """Botón de una tarea: abre su guía. La clave lleva lote y estado para poder colorearlo con CSS."""
    est = estado_tarea(lote, act, hoy)
    icono, _, sufijo = ESTADOS[est]
    if st.button(f"{icono} {etiqueta}", key=f"t_{ctx}_{lote['id']}_{act['id']}_{sufijo}"):
        mostrar_guia(lote["id"], act["id"])


def inyectar_css(lotes):
    css = """
    <style>
    /* Calendario y navegación: mantienen 7 / 3 columnas también en el celular */
    .st-key-calendario, .st-key-calendario [data-testid="stVerticalBlock"] { gap: 2px !important; }
    .st-key-calendario [data-testid="stHorizontalBlock"], .st-key-nav [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important; gap: 2px !important; }
    .st-key-calendario [data-testid="stColumn"], .st-key-calendario [data-testid="column"],
    .st-key-nav [data-testid="stColumn"], .st-key-nav [data-testid="column"] {
        min-width: 0 !important; flex: 1 1 0 !important; width: auto !important; }
    .st-key-calendario [data-testid="stColumn"], .st-key-calendario [data-testid="column"] {
        border: 1px solid rgba(128,128,128,.35); border-radius: 4px; padding: 2px; min-height: 72px; }
    /* Botones de tarea */
    [class*="st-key-t_"], [class*="st-key-t_"] [data-testid="stButton"] { width: 100% !important; }
    [class*="st-key-t_"] button {
        width: 100% !important; min-height: 0 !important; line-height: 1.15 !important;
        padding: 4px 8px !important; color: #000 !important; border: none !important;
        border-left: 3px solid #333 !important; justify-content: flex-start !important; }
    [class*="st-key-t_"] button p { font-size: 14px !important; text-align: left; white-space: normal !important; }
    .st-key-calendario [class*="st-key-t_"] button { padding: 2px 3px !important; }
    .st-key-calendario [class*="st-key-t_"] button p { font-size: 10px !important; overflow-wrap: anywhere; }
    [class*="st-key-t_"] button:hover { filter: brightness(.93); }
    """
    # Cada lote conserva su color en todas sus tareas
    for l in lotes:
        css += f'[class*="st-key-t_"][class*="_{l["id"]}_"] button {{ background-color: {l["color"]} !important; }}\n'
    # Estados: completada (tachada y atenuada), no realizada (gris), vencida (borde rojo), solo aviso (punteado)
    css += """
    [class*="st-key-t_"][class*="_comp"] button { opacity: .6; }
    [class*="st-key-t_"][class*="_comp"] button p { text-decoration: line-through; }
    [class*="st-key-t_"][class*="_nore"] button { background-color: #d9d9d9 !important; color: #555 !important; }
    [class*="st-key-t_"][class*="_nore"] button p { text-decoration: line-through; }
    [class*="st-key-t_"][class*="_venc"] button { box-shadow: inset 0 0 0 2px #d62828; font-weight: 700; }
    [class*="st-key-t_"][class*="_info"] button { opacity: .75; border-left-style: dashed !important; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def mostrar_recordatorios(lotes, hoy):
    hoy_l, manana_l, vencidas, pendientes, avisos = calcular_recordatorios(lotes, hoy)
    for nombre, tareas in vencidas.items():
        n = len(tareas)
        st.error(f"⚠️ **{esc_md(nombre)}** tiene {plural(n, 'tarea vencida', 'tareas vencidas')}: "
                 f"{', '.join(esc_md(t) for t in tareas)}.")
    if hoy_l:
        st.warning("🔔 **Hoy corresponde:**\n" + "\n".join(f"- {esc_md(x)}" for x in hoy_l))
    if manana_l:
        st.info("📅 **Mañana corresponde:**\n" + "\n".join(f"- {esc_md(x)}" for x in manana_l))
    if avisos:
        st.info("ℹ️ **Solo aviso (no hay que hacer nada):**\n" + "\n".join(f"- {esc_md(x)}" for x in avisos))
    if pendientes:
        st.caption(f"Hay {plural(pendientes, 'actividad pendiente', 'actividades pendientes')}.")
    elif not vencidas:
        st.caption("✅ No tienes actividades pendientes.")


def eventos_por_fecha(lotes):
    ev = {}
    for l in lotes:
        if l["archivado"]:
            continue
        for act in acts_activas(l):
            ev.setdefault(fecha_act(l, act), []).append((l, act))
    return ev


def mover_calendario(delta):
    a = st.session_state.cal_ancla
    if st.session_state.cal_vista == "Semana":
        a = a + timedelta(days=7 * delta)
    else:
        m = a.month - 1 + delta
        a = date(a.year + m // 12, m % 12 + 1, 1)
    st.session_state.cal_ancla = a


def ir_a_hoy():
    st.session_state.cal_ancla = hoy_peru()


def vista_mes(anio, mes, eventos, hoy):
    st.markdown(f"<h4 style='text-align:center; margin:8px 0 4px;'>{MESES_ES[mes]} {anio}</h4>", unsafe_allow_html=True)
    st.markdown(
        "<div style='display:flex; gap:2px; text-align:center; font-weight:bold; font-size:12px;'>"
        + "".join(f"<div style='flex:1 1 0; min-width:0;'>{d}</div>" for d in DIAS_SEMANA) + "</div>",
        unsafe_allow_html=True,
    )
    with st.container(key="calendario"):
        for semana in calendar.monthcalendar(anio, mes):
            columnas = st.columns(7)
            for col, dia in zip(columnas, semana):
                if dia == 0:
                    continue
                f = date(anio, mes, dia)
                with col:
                    numero = str(dia)
                    if f == hoy:
                        numero = f"<span style='background:#f5b301; color:#000; border-radius:10px; padding:0 6px;'>{dia}</span>"
                    st.markdown(f"<div style='font-weight:bold; font-size:12px;'>{numero}</div>", unsafe_allow_html=True)
                    for lote, act in eventos.get(f, []):
                        nombre = lote["nombre"]
                        corto = nombre if len(nombre) <= 10 else nombre[:9] + "…"
                        boton_tarea("cal", lote, act, f"{esc_md(corto)} · {esc_md(info_act(act)['corto'])}", hoy)


def vista_semana(ancla, eventos, hoy):
    lunes = ancla - timedelta(days=ancla.weekday())
    st.markdown(f"<h4 style='text-align:center; margin:8px 0 4px;'>Semana del {lunes:%d/%m} al {lunes + timedelta(days=6):%d/%m/%Y}</h4>",
                unsafe_allow_html=True)
    for k in range(7):
        f = lunes + timedelta(days=k)
        marca = "  ·  🟡 **Hoy**" if f == hoy else ""
        st.markdown(f"**{DIAS_SEMANA_LARGO[k]} {f:%d/%m}**{marca}")
        evs = eventos.get(f, [])
        if not evs:
            st.caption("Sin actividades")
        for lote, act in evs:
            boton_tarea("sem", lote, act, f"{esc_md(lote['nombre'])} · {esc_md(nombre_act(act))}", hoy)


def cabecera_lote(lote, hoy):
    conteo = {}
    for act in acts_activas(lote):
        e = estado_tarea(lote, act, hoy)
        conteo[e] = conteo.get(e, 0) + 1
    chips = " · ".join(f"{ESTADOS[e][0]} {conteo[e]}" for e in ("vencida", "pendiente", "completada", "no_realizada") if conteo.get(e))
    exito = pct(lote["reinas_fecundadas"], lote["cant_traslarve"])
    extra = f" | Éxito final: <b>{exito:.1f}%</b>" if exito is not None else ""
    tipo = lote["tipo_crianza"] if lote["tipo_crianza"] != TIPOS_CRIANZA[0] else ""
    ic_cal, tx_cal = CALIDADES[calidad(lote)]
    alim = texto_alimentacion(lote["alimentacion"]) if lote["alimentacion"]["con"] is not None else ""
    detalle = " · ".join(x for x in (tipo, lote["apiario"], alim, chips, f"{ic_cal} {tx_cal}") if x)
    return (
        f"<div style='background-color:{lote['color']}; padding:10px 12px; border-radius:8px; color:#000; margin-top:12px;'>"
        f"<b>{html.escape(lote['nombre'])}</b> | Traslarve: {lote['traslarve_fecha']:%d/%m/%Y} | "
        f"Larvas: <b>{lote['cant_traslarve']}</b>{extra}"
        f"<br><span style='font-size:12px;'>{html.escape(detalle)}</span></div>"
    )


# ---------------------------------------------------------------------------
# ACTIVIDADES Y ALIMENTACIÓN: editores reutilizables (Ajustes, lote nuevo, cada lote)
# ---------------------------------------------------------------------------
def editor_actividades(prefijo, acts):
    """Una fila por actividad: activar/desactivar, cambiar el día y quitar las propias.
    Devuelve (lista_editada, id_a_quitar_o_None). No guarda nada por sí solo."""
    st.caption("☑️ Marca las que quieres usar. «Día» = días después del traslarve (día 0).")
    nuevas, quitar = [], None
    for a in sorted(acts, key=lambda x: (x["dias"], x["titulo"])):
        base = BASE_POR_ID.get(a["id"])
        fija = bool(base and base["fija"])
        sufijo = "" if a["accion"] else " · _solo aviso_"
        c1, c2, c3 = st.columns([6, 3, 1], vertical_alignment="center")
        activa = c1.checkbox(f"{info_act(a)['icono']} {esc_md(a['titulo'])}{sufijo}", value=a["activa"],
                             key=f"{prefijo}_{a['id']}_on", disabled=fija)
        if fija:
            dias = 0
            c2.caption("Día 0")
        else:
            dias = c2.number_input(f"Día de {a['titulo']}", min_value=1 if base else DIA_MIN, max_value=DIA_MAX,
                                   step=1, value=int(a["dias"]), key=f"{prefijo}_{a['id']}_dia",
                                   label_visibility="collapsed")
        if not base and c3.button("🗑️", key=f"{prefijo}_{a['id']}_del", help="Quitar esta actividad"):
            quitar = a["id"]
        nuevas.append({**a, "activa": bool(activa), "dias": int(dias)})
    return nuevas, quitar


def formulario_nueva_actividad(clave):
    """Formulario para crear una actividad propia. Devuelve la actividad o None."""
    with st.form(clave, clear_on_submit=True):
        titulo = st.text_input("Nombre de la actividad", placeholder="Ej: Dar jarabe a la iniciadora")
        dias = st.number_input("Día (0 = día del traslarve; negativo = antes)", min_value=DIA_MIN,
                               max_value=DIA_MAX, value=1, step=1)
        solo_aviso = st.checkbox("Es solo un aviso (no hay que hacer nada, nunca queda «vencida»)")
        nota = st.text_area("Descripción o instrucciones (opcional)")
        enviado = st.form_submit_button("➕ Agregar actividad")
    if not enviado:
        return None
    if not titulo.strip():
        st.warning("Escribe un nombre para la actividad.")
        return None
    return normalizar_actividad({"id": "x" + nuevo_id(), "titulo": titulo, "dias": dias, "activa": True,
                                 "accion": not solo_aviso, "nota": nota})


def elegir_alimento(prefijo, etiqueta, opciones, actual, defecto):
    """Lista con el alimento por defecto; la última opción permite escribir uno propio.
    Devuelve (texto, error_o_None)."""
    lista = opciones + [OTRO_ALIMENTO]
    actual = actual or defecto
    idx = lista.index(actual) if actual in opciones else len(lista) - 1
    eleccion = st.selectbox(etiqueta, lista, index=idx, key=f"{prefijo}_sel")
    if eleccion != OTRO_ALIMENTO:
        return eleccion, None
    texto = st.text_input("Escribe el alimento", value="" if actual in opciones else actual,
                          max_chars=60, key=f"{prefijo}_txt").strip()
    return texto, (None if texto else f"Escribe el nombre del alimento ({etiqueta.lower()}).")


def selector_alimentacion(prefijo, actual):
    """Sin alimentación / con alimentación (energética, proteica o ambas). Devuelve (dict, error_o_None).
    Los lotes antiguos (alimentación sin registrar) tienen además la opción «Sin registrar».
    No usar dentro de un st.form: los campos cambian según lo que se elija."""
    actual = normalizar_alimentacion(actual)
    opciones = ["Sin alimentación", "Con alimentación"]
    if actual["con"] is None and prefijo.startswith("e_"):   # solo al editar un lote ya existente
        opciones = ["Sin registrar"] + opciones
    st.markdown("**🍯 Alimentación**")
    modo = st.radio("Alimentación", opciones, index=opciones.index("Con alimentación") if actual["con"] else 0, horizontal=True,
                    key=f"{prefijo}_modo", label_visibility="collapsed")
    if modo == "Sin registrar":
        return {"con": None, "energetica": "", "proteica": ""}, None
    if modo == "Sin alimentación":
        return {"con": False, "energetica": "", "proteica": ""}, None
    en0, pr0 = actual["energetica"], actual["proteica"]
    i = 2 if (en0 and pr0) else (1 if pr0 else 0)
    clase = st.radio("Tipo de alimentación", CLASES_ALIM, index=i, horizontal=True, key=f"{prefijo}_clase")
    en = pr = ""
    errores = []
    if clase in (CLASES_ALIM[0], CLASES_ALIM[2]):
        en, e = elegir_alimento(f"{prefijo}_en", "Alimento energético", OPCIONES_ENERGETICA, en0, ENERGETICA_DEF)
        if e:
            errores.append(e)
    if clase in (CLASES_ALIM[1], CLASES_ALIM[2]):
        pr, e = elegir_alimento(f"{prefijo}_pr", "Alimento proteico", OPCIONES_PROTEICA, pr0, PROTEICA_DEF)
        if e:
            errores.append(e)
    return {"con": True, "energetica": en, "proteica": pr}, (" ".join(errores) or None)


def tarjeta_lote(lote, hoy):
    lid = lote["id"]
    st.markdown(cabecera_lote(lote, hoy), unsafe_allow_html=True)
    with st.expander("Abrir / editar lote"):
        tab_t, tab_a, tab_c, tab_d = st.tabs(["Tareas", "Actividades", "Cantidades", "Datos"])

        with tab_t:
            for act in acts_activas(lote):
                f = fecha_act(lote, act)
                etiqueta = f"{nombre_act(act)} · {DIAS_SEMANA_LARGO[f.weekday()][:3]} {f:%d/%m/%Y}"
                boton_tarea("lot", lote, act, esc_md(etiqueta), hoy)
            apagadas = [a["titulo"] for a in acts_ordenadas(lote) if not a["activa"]]
            if apagadas:
                st.caption("Desactivadas en este lote: " + ", ".join(apagadas) +
                           ". Se reactivan en la pestaña «Actividades».")
            st.caption("Toca una tarea para ver cómo se hace y cambiar su estado.")

        with tab_a:
            st.caption("Activa o desactiva actividades, cambia sus días o agrega otras. "
                       "Esto solo afecta a este lote.")
            nuevas, quitar = editor_actividades(f"la_{lid}", lote["actividades"])
            if quitar:
                lote["actividades"] = [a for a in lote["actividades"] if a["id"] != quitar]
                lote["tareas"].pop(quitar, None)
                guardar()
                st.session_state.mensaje = "Actividad quitada del lote."
                st.rerun()
            if st.button("💾 Guardar actividades", type="primary", key=f"la_ok_{lid}"):
                error = validar_actividades(nuevas)
                if error:
                    st.warning(error)
                else:
                    lote["actividades"] = nuevas
                    guardar()
                    st.session_state.mensaje = "Actividades del lote guardadas."
                    st.rerun()
            st.markdown("---")
            st.markdown("**➕ Agregar otra actividad a este lote**")
            nueva = formulario_nueva_actividad(f"la_add_{lid}")
            if nueva:
                lote["actividades"].append(nueva)
                guardar()
                st.session_state.mensaje = f"Actividad «{nueva['titulo']}» agregada al lote."
                st.rerun()

        with tab_c:
            with st.form(f"cant_{lid}"):
                st.caption("Deja vacío lo que todavía no sepas: «sin registrar» no es lo mismo que 0.")
                nuevos = {}
                for campo, etiqueta in ETAPAS[1:]:
                    nuevos[campo] = st.number_input(
                        etiqueta, min_value=0, max_value=lote["cant_traslarve"], step=1,
                        value=lote[campo], key=f"q_{lid}_{campo}")
                opciones_c = [None] + list(CALIDADES)
                manual = st.selectbox(
                    "Clasificación de los datos", opciones_c, index=opciones_c.index(lote["calidad_manual"]),
                    format_func=lambda k: "Automática (según los datos)" if k is None
                    else f"{CALIDADES[k][0]} {CALIDADES[k][1]}", key=f"q_{lid}_calidad")
                if st.form_submit_button("Guardar cantidades"):
                    lote.update(nuevos)
                    lote["calidad_manual"] = manual
                    guardar()
                    st.session_state.mensaje = "Cantidades guardadas."
                    st.rerun()
            st.markdown(f"**Rendimiento** (sobre {lote['cant_traslarve']} larvas)")
            st.markdown(lineas_porcentajes(lote))
            for aviso in incoherencias(lote):
                st.warning("⚠️ " + aviso)
            ic_cal, tx_cal = CALIDADES[calidad(lote)]
            origen = "elegida por ti" if lote["calidad_manual"] else "automática"
            st.caption(f"Clasificación {origen}: {ic_cal} {tx_cal}. Los lotes que no son «válidos» se pueden "
                       "excluir de las estadísticas del Historial sin borrarlos.")

        with tab_d:
            nombre = st.text_input("Nombre del lote", value=lote["nombre"], key=f"e_nom_{lid}")
            fecha = st.date_input("Fecha de traslarve", value=lote["traslarve_fecha"], key=f"e_fec_{lid}")
            cant = st.number_input("Larvas traslarvadas", min_value=1, step=1,
                                   value=int(lote["cant_traslarve"]), key=f"e_can_{lid}")
            opciones = TIPOS_CRIANZA if lote["tipo_crianza"] in TIPOS_CRIANZA else TIPOS_CRIANZA + [lote["tipo_crianza"]]
            tipo = st.selectbox("Tipo de crianza", opciones, index=opciones.index(lote["tipo_crianza"]), key=f"e_tip_{lid}")
            apiario = st.text_input("Apiario", value=lote["apiario"], key=f"e_api_{lid}")
            madre = st.text_input("Colmena madre", value=lote["colmena_madre"], key=f"e_mad_{lid}")
            obs = st.text_area("Observaciones", value=lote["observaciones"], key=f"e_obs_{lid}")
            color = st.color_picker("Color del lote", value=lote["color"], key=f"e_col_{lid}")
            alim, err_alim = selector_alimentacion(f"e_al_{lid}", lote["alimentacion"])
            if st.button("Guardar cambios", type="primary", key=f"e_ok_{lid}"):
                if not nombre.strip():
                    st.warning("El nombre no puede estar vacío.")
                elif err_alim:
                    st.warning(err_alim)
                else:
                    lote.update({
                        "nombre": nombre.strip(), "traslarve_fecha": fecha, "cant_traslarve": int(cant),
                        "tipo_crianza": tipo, "apiario": apiario.strip(), "colmena_madre": madre.strip(),
                        "observaciones": obs, "color": color, "alimentacion": normalizar_alimentacion(alim),
                    })
                    for campo, _ in ETAPAS[1:]:   # las cantidades no pueden superar las larvas
                        if lote[campo] is not None:
                            lote[campo] = min(lote[campo], lote["cant_traslarve"])
                    guardar()
                    st.session_state.mensaje = "Lote actualizado."
                    st.rerun()
            c1, c2 = st.columns(2)
            if c1.button("↩️ Reactivar lote" if lote["archivado"] else "📦 Archivar lote", key=f"arch_{lid}"):
                lote["archivado"] = not lote["archivado"]
                guardar()
                st.rerun()
            if c2.button("🗑️ Eliminar lote", key=f"del_{lid}"):
                confirmar_eliminar(lid)


def tabla_comparacion(lotes_sel, clave, columna):
    """Suma las etapas de los lotes agrupados por `clave(lote)` y muestra los porcentajes."""
    grupos = {}
    for l in lotes_sel:
        g = grupos.setdefault(clave(l), {c: 0 for c, _ in ETAPAS})
        g["lotes"] = g.get("lotes", 0) + 1
        for c, _ in ETAPAS:
            g[c] += cifra(l, c)
    filas = [{
        columna: nombre, "Lotes": g["lotes"], "Larvas": g["cant_traslarve"],
        "% Aceptación": fmt_pct(pct(g["celdas_aceptadas"], g["cant_traslarve"])),
        "% Nacimiento": fmt_pct(pct(g["reinas_nacidas"], g["celdas_insertadas"])),
        "% Fecundación": fmt_pct(pct(g["reinas_fecundadas"], g["reinas_nacidas"])),
        "% Éxito final": fmt_pct(pct(g["reinas_fecundadas"], g["cant_traslarve"])),
    } for nombre, g in grupos.items()]
    st.dataframe(pd.DataFrame(filas), hide_index=True)


# ---------------------------------------------------------------------------
# PÁGINA
# ---------------------------------------------------------------------------
HOY = hoy_peru()

if "lotes" not in st.session_state:
    (st.session_state.config, st.session_state.lotes, st.session_state.error_carga,
     st.session_state.modo, st.session_state.error_guardado) = cargar_todo()
    st.session_state.cal_ancla = HOY
st.session_state.setdefault("cal_vista", "Mes")
st.session_state.setdefault("nl_gen", 0)

lotes = st.session_state.lotes
config = st.session_state.config

# Actividades del formulario de lote nuevo: salen de Ajustes y se renuevan cuando Ajustes cambia
firma = firma_config(config)
if st.session_state.get("nl_firma") != firma or "nl_acts" not in st.session_state:
    st.session_state.nl_firma = firma
    st.session_state.nl_acts = copy.deepcopy(config["actividades"])

inyectar_css(lotes)

st.title("🐝 Gestor de Crianza de Reinas")
st.caption(f"Hoy: {DIAS_SEMANA_LARGO[HOY.weekday()]} {HOY:%d/%m/%Y} (hora de Perú)")

if "mensaje" in st.session_state:
    st.success(st.session_state.pop("mensaje"))

_, problema_conexion = conectar_supabase()
if problema_conexion and problema_conexion.get("configurado", True):
    mostrar_problema(problema_conexion)
    st.caption("Mientras no se arregle, tus datos se guardan solo en un archivo temporal del servidor "
               "(se puede perder al reiniciar la app). Descarga respaldos en Ajustes.")
if st.session_state.error_carga:
    mostrar_problema(st.session_state.error_carga)
    st.caption("No se guardará nada hasta resolverlo, para no perder información. "
               "También puedes restaurar un respaldo en Ajustes.")
    if st.button("🔄 Reintentar la conexión", key="btn_reintentar"):
        recargar_datos()
if st.session_state.get("error_guardado"):
    mostrar_problema(st.session_state.error_guardado)

mostrar_recordatorios(lotes, HOY)

tab_cal, tab_lotes, tab_hist, tab_ajustes = st.tabs(["📅 Calendario", "📋 Lotes", "📊 Historial", "⚙️ Ajustes"])

# ----------------------------- CALENDARIO ---------------------------------
with tab_cal:
    eventos = eventos_por_fecha(lotes)

    proximas = sorted(
        ((f, l, act) for f, evs in eventos.items() for l, act in evs
         if f >= HOY and estado_tarea(l, act, HOY) == "pendiente"),
        key=lambda x: (x[0], x[1]["nombre"], x[2]["dias"]),
    )[:6]
    if proximas:
        st.subheader("⏰ Próximas actividades")
        with st.container(key="proximas"):
            for f, l, act in proximas:
                d = (f - HOY).days
                cuando = "¡Hoy!" if d == 0 else ("Mañana" if d == 1 else f"en {d} días")
                boton_tarea("prox", l, act, f"{f:%d/%m} · {esc_md(l['nombre'])} · {esc_md(act['titulo'])} ({cuando})", HOY)

    st.subheader("📅 Calendario Apícola")
    st.radio("Vista", ["Mes", "Semana"], horizontal=True, key="cal_vista", label_visibility="collapsed")
    with st.container(key="nav"):
        n1, n2, n3 = st.columns(3)
        n1.button("◀", key="nav_ant", on_click=mover_calendario, args=(-1,))
        n2.button("Hoy", key="nav_hoy", on_click=ir_a_hoy)
        n3.button("▶", key="nav_sig", on_click=mover_calendario, args=(1,))

    ancla = st.session_state.cal_ancla
    if st.session_state.cal_vista == "Semana":
        vista_semana(ancla, eventos, HOY)
    else:
        vista_mes(ancla.year, ancla.month, eventos, HOY)
    st.caption("⏳ Pendiente · ✅ Completada · ⏭️ No realizada · ⚠️ Vencida (se marca sola al pasar el día) · "
               "ℹ️ Solo aviso (no hay que hacer nada). Cada lote tiene su propio color.")

    with st.expander("📲 Exportar al calendario del teléfono (.ics)"):
        st.caption("Descarga el archivo y ábrelo en tu teléfono: se agregan las tareas pendientes como eventos de día "
                   "completo con aviso a las 8:00 (Google Calendar, iPhone y otros). Si lo importas de nuevo, "
                   "los eventos se actualizan en vez de duplicarse. Los avisos sin acción no se exportan.")
        activos = [l for l in lotes if not l["archivado"]]
        if activos:
            opciones = ["__todos__"] + [l["id"] for l in activos]
            nombres = {l["id"]: l["nombre"] for l in activos}
            sel = st.selectbox("Lote", opciones, key="ics_lote",
                               format_func=lambda x: "Todos los lotes activos" if x == "__todos__" else nombres[x])
            elegidos = activos if sel == "__todos__" else [l for l in activos if l["id"] == sel]
            st.download_button("⬇️ Descargar calendario (.ics)", data=generar_ics(elegidos, HOY).encode("utf-8"),
                               file_name="crianza_reinas.ics", mime="text/calendar")
        else:
            st.info("Aún no hay lotes activos.")

# ------------------------------- LOTES ------------------------------------
with tab_lotes:
    with st.expander("➕ Registrar nuevo lote", expanded=not lotes):
        ks = f"nl{st.session_state.nl_gen}"
        nombre_n = st.text_input("Nombre del lote", placeholder="Ej: Lote A", key=f"{ks}_nom")
        fecha_n = st.date_input("Fecha de traslarve", value=HOY, key=f"{ks}_fec")
        cant_n = st.number_input("Larvas traslarvadas (Día 0)", min_value=1, value=20, step=1, key=f"{ks}_can")
        tipo_n = st.selectbox("Tipo de crianza", TIPOS_CRIANZA, key=f"{ks}_tip")
        apiario_n = st.text_input("Apiario", key=f"{ks}_api")
        madre_n = st.text_input("Colmena madre", key=f"{ks}_mad")
        obs_n = st.text_area("Observaciones", key=f"{ks}_obs")

        st.markdown("---")
        alim_n, err_alim_n = selector_alimentacion(f"{ks}_al", None)

        st.markdown("---")
        st.markdown("**📋 Actividades de este lote**")
        st.caption("Salen de los valores de «Ajustes». Aquí puedes cambiar el día, desactivar o agregar "
                   "actividades solo para este lote.")
        acts_n, quitar_n = editor_actividades(f"{ks}{firma}_ac", st.session_state.nl_acts)
        if quitar_n:
            st.session_state.nl_acts = [a for a in st.session_state.nl_acts if a["id"] != quitar_n]
            st.rerun()
        st.markdown("**➕ Agregar otra actividad a este lote**")
        nueva_n = formulario_nueva_actividad(f"{ks}_add")
        if nueva_n:
            st.session_state.nl_acts.append(nueva_n)
            st.rerun()

        st.markdown("---")
        if st.button("Registrar lote y guardar", type="primary", key=f"{ks}_ok"):
            error = validar_actividades(acts_n)
            if not nombre_n.strip():
                st.warning("⚠️ Escribe un nombre para el lote.")
            elif err_alim_n:
                st.warning(err_alim_n)
            elif error:
                st.warning(error)
            elif st.session_state.error_carga:
                st.error("No se puede guardar mientras haya un error de carga. Restaura un respaldo.")
            else:
                usados = {l["color"] for l in lotes}
                color = next((c for c in COLORES if c not in usados), COLORES[len(lotes) % len(COLORES)])
                lotes.append(lote_desde_dict({
                    "id": nuevo_id(), "nombre": nombre_n.strip(), "traslarve_fecha": fecha_n.isoformat(),
                    "cant_traslarve": int(cant_n), "tipo_crianza": tipo_n, "apiario": apiario_n.strip(),
                    "colmena_madre": madre_n.strip(), "observaciones": obs_n, "actividades": acts_n,
                    "alimentacion": alim_n, "color": color,
                }))
                guardar()
                st.session_state.nl_gen += 1      # campos nuevos y vacíos para el siguiente lote
                st.session_state.nl_acts = copy.deepcopy(config["actividades"])
                st.session_state.mensaje = f"¡Lote '{nombre_n.strip()}' guardado!"
                st.rerun()

    activos = [l for l in lotes if not l["archivado"]]
    archivados = [l for l in lotes if l["archivado"]]
    if not lotes:
        st.info("Todavía no hay lotes. Registra el primero arriba.")
    for l in sorted(activos, key=lambda x: x["traslarve_fecha"], reverse=True):
        tarjeta_lote(l, HOY)
    if archivados:
        st.markdown("---")
        if st.toggle(f"Mostrar lotes archivados ({len(archivados)})", key="ver_archivados"):
            for l in sorted(archivados, key=lambda x: x["traslarve_fecha"], reverse=True):
                tarjeta_lote(l, HOY)

# ------------------------------ HISTORIAL ---------------------------------
with tab_hist:
    if not lotes:
        st.info("Cuando registres lotes verás aquí sus resultados y estadísticas.")
    else:
        filtro = st.radio("Mostrar", ["Todos", "Activos", "Archivados"], horizontal=True, key="hist_filtro")
        sel = [l for l in lotes if filtro == "Todos" or (l["archivado"] == (filtro == "Archivados"))]
        if not sel:
            st.info("No hay lotes en este filtro.")
        else:
            cuenta = {k: sum(1 for l in sel if calidad(l) == k) for k in CALIDADES}
            st.markdown(" · ".join(f"{CALIDADES[k][0]} {CALIDADES[k][1]}: **{cuenta[k]}**" for k in CALIDADES))
            incluir = st.multiselect(
                "Lotes que cuentan en las estadísticas", list(CALIDADES), default=["validos"], key="hist_calidad",
                format_func=lambda k: f"{CALIDADES[k][0]} {CALIDADES[k][1]}")
            st.caption("Los lotes que dejes fuera no se borran: siguen en la tabla «Resultados por lote», "
                       "solo no entran en los totales, el gráfico ni las comparaciones. "
                       "La clasificación se hace sola (o la eliges tú en la pestaña «Cantidades» de cada lote).")
            sel_e = [l for l in sel if calidad(l) in incluir]

            st.subheader("Totales")
            if not sel_e:
                st.info("Ningún lote cumple el filtro de calidad elegido. Agrega más tipos de datos arriba "
                        "para incluirlos en las estadísticas.")
            else:
                tot = {campo: sum(cifra(l, campo) for l in sel_e) for campo, _ in ETAPAS}
                st.markdown(f"Lotes incluidos: **{len(sel_e)}** de {len(sel)}")
                st.dataframe(pd.DataFrame([
                    {"Etapa": et, "Total": tot[c], "% de las larvas": fmt_pct(pct(tot[c], tot["cant_traslarve"]))}
                    for c, et in ETAPAS
                ]), hide_index=True)
                st.markdown("**Porcentajes entre etapas**")
                st.markdown(lineas_porcentajes(tot))
                st.caption("Aparece «—» cuando falta registrar la etapa anterior.")

            st.subheader("Resultados por lote")
            filas, numericos = [], []
            for l in sorted(sel, key=lambda x: x["traslarve_fecha"], reverse=True):
                r = {n: pct(l[a], l[b]) for n, a, b in RATIOS}
                ic_cal, tx_cal = CALIDADES[calidad(l)]
                dentro = calidad(l) in incluir
                filas.append({
                    "Lote": l["nombre"], "Fecha": f"{l['traslarve_fecha']:%d/%m/%Y}", "Tipo": l["tipo_crianza"],
                    "Apiario": l["apiario"], "Alimentación": texto_alimentacion(l["alimentacion"]),
                    "Larvas": l["cant_traslarve"], "Aceptadas": fmt_n(l["celdas_aceptadas"]),
                    "Nacidas": fmt_n(l["reinas_nacidas"]), "Con postura": fmt_n(l["reinas_fecundadas"]),
                    "% Aceptación": fmt_pct(r["Aceptación"]), "% Nacimiento": fmt_pct(r["Nacimiento"]),
                    "% Fecundación": fmt_pct(r["Fecundación"]), "% Éxito final": fmt_pct(r["Éxito final"]),
                    "Datos": f"{ic_cal} {tx_cal}", "En estadísticas": "Sí" if dentro else "No",
                    "Estado": "Archivado" if l["archivado"] else "Activo",
                })
                if dentro:
                    numericos.append({"Lote": l["nombre"], "% Éxito final": r["Éxito final"]})
            st.dataframe(pd.DataFrame(filas), hide_index=True)
            if numericos:
                df_num = pd.DataFrame(numericos)
                if df_num["% Éxito final"].notna().any():
                    st.markdown("**Comparación del éxito final entre lotes (%)**")
                    st.bar_chart(df_num.set_index("Lote")["% Éxito final"])

            if sel_e:
                st.subheader("Comparación por tipo de crianza")
                tabla_comparacion(sel_e, lambda l: l["tipo_crianza"], "Tipo de crianza")
                st.subheader("Comparación por alimentación")
                tabla_comparacion(sel_e, lambda l: texto_alimentacion(l["alimentacion"]), "Alimentación")

# ------------------------------- AJUSTES ----------------------------------
with tab_ajustes:
    st.subheader("⏱️ Actividades predefinidas")
    st.caption("Son las actividades (y sus días) que aparecen automáticamente al registrar un lote nuevo. "
               "Cambia el día de cualquiera, desactiva las que no uses o agrega otras. "
               "No modifican los lotes que ya existen: cada lote se edita en su pestaña «Actividades».")
    acts_cfg, quitar_cfg = editor_actividades("cfg", config["actividades"])
    if quitar_cfg:
        config["actividades"] = [a for a in config["actividades"] if a["id"] != quitar_cfg]
        guardar()
        st.session_state.mensaje = "Actividad quitada de las predefinidas."
        st.rerun()
    if st.button("💾 Guardar actividades predefinidas", type="primary", key="btn_guardar_cfg"):
        error = validar_actividades(acts_cfg)
        if error:
            st.warning(error)
        else:
            config["actividades"] = normalizar_catalogo(acts_cfg)
            guardar()
            st.session_state.mensaje = "Actividades predefinidas guardadas. Se usarán en los lotes nuevos."
            st.rerun()
    st.markdown("**➕ Agregar una actividad nueva a las predefinidas**")
    nueva_cfg = formulario_nueva_actividad("cfg_add")
    if nueva_cfg:
        config["actividades"].append(nueva_cfg)
        guardar()
        st.session_state.mensaje = f"Actividad «{nueva_cfg['titulo']}» agregada. Saldrá en los lotes nuevos."
        st.rerun()

    st.subheader("💾 Almacenamiento")
    cliente, problema = conectar_supabase()
    if cliente:
        st.success("☁️ Los datos se guardan en Supabase: no se pierden al reiniciar la app.")
    elif problema and problema.get("configurado", True):
        mostrar_problema(problema)
    else:
        st.warning("⚠️ Los datos se guardan en un archivo del servidor, que se puede borrar cuando la app se reinicia. "
                   "Activa Supabase (gratis) o descarga respaldos con frecuencia.")
    if st.button("🔌 Probar la conexión con Supabase", key="btn_probar"):
        resultado = probar_supabase()
        if resultado:
            mostrar_problema(resultado)
        else:
            st.success("✅ La conexión funciona: se puede leer y escribir en Supabase.")
            if st.session_state.get("error_guardado") and not st.session_state.error_carga:
                guardar()
                if st.session_state.error_guardado:
                    mostrar_problema(st.session_state.error_guardado)
                else:
                    st.success("Tus datos se volvieron a guardar en Supabase.")
    with st.expander("Cómo activar el almacenamiento permanente (Supabase)"):
        st.markdown(
            "1. Crea una cuenta y un proyecto en **supabase.com**.\n"
            "2. En **SQL Editor**, ejecuta este código:"
        )
        st.code(
            "create table if not exists estado_app (\n"
            "  id text primary key,\n"
            "  datos jsonb not null\n"
            ");\n"
            "alter table estado_app enable row level security;",
            language="sql",
        )
        st.markdown(
            "3. En **Project Settings → API**, copia la *Project URL* y la clave secreta (*service_role*; "
            "no uses la clave `anon`).\n"
            "4. En Streamlit Cloud: **Settings → Secrets**, pega:"
        )
        st.code('[supabase]\nurl = "https://TU-PROYECTO.supabase.co"\nkey = "TU_CLAVE_SERVICE_ROLE"', language="toml")
        st.markdown("5. Agrega `supabase` a tu `requirements.txt` y reinicia la app. "
                    "Tus datos actuales se suben solos la primera vez.\n"
                    "6. Vuelve aquí y pulsa **Probar la conexión**: si algo falla, te explicará qué es.")
        st.caption("Nunca pongas la clave dentro del código: solo en Secrets.")

    st.subheader("🛟 Copia de seguridad")
    st.download_button(
        "⬇️ Descargar respaldo (.json)",
        data=json.dumps(datos_para_guardar(config, lotes), ensure_ascii=False, indent=2),
        file_name=f"respaldo_reinas_{HOY:%Y%m%d}.json", mime="application/json")
    archivo = st.file_uploader("⬆️ Restaurar desde un respaldo (.json)", type=["json"], key="uploader")
    if archivo is not None:
        try:
            cfg_nueva, lotes_nuevos = estado_desde_datos(json.loads(archivo.getvalue().decode("utf-8")))
        except Exception as e:
            st.error(f"El archivo no es un respaldo válido: {e}")
        else:
            st.info(f"El respaldo contiene {plural(len(lotes_nuevos), 'lote', 'lotes')}. "
                    "Al restaurar se reemplazan TODOS los datos actuales.")
            if st.button("Confirmar restauración", type="primary", key="btn_restaurar"):
                st.session_state.config = cfg_nueva
                st.session_state.lotes = lotes_nuevos
                st.session_state.error_carga = None
                guardar()
                st.session_state.mensaje = "✅ Datos restaurados correctamente."
                st.rerun()
