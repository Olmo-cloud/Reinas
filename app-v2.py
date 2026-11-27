# -*- coding: utf-8 -*-
"""Gestor de Crianza de Reinas (Streamlit). Requiere Streamlit >= 1.39. Para guardar los datos de forma permanente configura Supabase (ver la pestaña "Ajustes" dentro de la app). """
import calendar
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

COLORES = ["#ff9999", "#66b3ff", "#99ff99", "#ffcc99", "#c299ff", "#ff99ff", "#ffe666",
           "#8fd9c7", "#f2a65a", "#b5e48c"]
DIAS_SEMANA = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]
DIAS_SEMANA_LARGO = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES_ES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
TIPOS_CRIANZA = ["Sin especificar", "Traslarve (Doolittle)", "Sistema Jenter / Nicot",
                 "Cupularve", "Celdas de emergencia", "Otro"]

# Estados de las tareas: clave -> (icono, nombre, sufijo para CSS)
ESTADOS = {
    "pendiente": ("⏳", "Pendiente", "pend"),
    "completada": ("✅", "Completada", "comp"),
    "no_realizada": ("⏭️", "No realizada", "nore"),
    "vencida": ("⚠️", "Vencida", "venc"),
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

# ---------------------------------------------------------------------------
# GUÍAS DE CADA TAREA
# ---------------------------------------------------------------------------
GUIA_TRASLARVE = """ **¿Qué es?** Es pasar larvas recién nacidas (de menos de 24 horas) desde las celdas de obrera de tu mejor colmena hacia copas artificiales de cera o plástico. Una colmena iniciadora las alimenta con mucha jalea real y las convierte en reinas. **Cómo se hace** 1. **Prepara la iniciadora:** una colmena fuerte, bien alimentada (jarabe), con muchas abejas nodrizas y sin reina o con la reina aislada. 2. **Consigue larvas de la edad justa:** deja que la reina madre ponga en un panal limpio. Los huevos eclosionan a los 3 días, así que el traslarve se hace cuando las larvas tienen menos de 24 h de nacidas (alrededor del día 4 de la postura). 3. **Trabaja en un lugar cálido, húmedo y sin viento** (cubre con un paño húmedo): las larvas se secan y mueren muy rápido. 4. **Con la aguja de traslarve**, levanta cada larva por debajo, sin tocarla ni voltearla, y deposítala en el fondo de la copa (si quieres, sobre una gota de jalea real diluida). 5. **Coloca enseguida el marco con las copas** en la iniciadora. 6. **Al día siguiente** revisa cuántas copas aceptaron las abejas y anótalo en "Cantidades". """

GUIA_NUCLEOS = """ **¿Qué es?** Un núcleo es una colmena pequeña (2 a 5 cuadros) donde la reina va a nacer, salir a aparearse y empezar a poner. ⚠️ **El núcleo NO debe tener reina.** Si tiene una, atacará la celda real o a la reina virgen que nazca. **Opción 1: armar un núcleo nuevo** 1. Toma 2 o 3 cuadros: uno o dos con cría operculada y naciente, y uno con miel y polen, con muchas abejas jóvenes encima. 2. **Revisa cuadro por cuadro que no pase la reina** a la caja. 3. Colócalos en la caja de núcleo y completa con un cuadro con cera si hace falta. 4. Reduce la piquera y dales jarabe. Las pecoreadoras vuelven a su colmena de origen, así que añade abejas jóvenes extra (sacude un cuadro más) o lleva el núcleo a un apiario a 3 km o más. **Opción 2: usar una colmena o núcleo que ya existe** No hace falta armar uno nuevo: puedes sacarle la reina a una colmena o núcleo existente (guárdala en una jaula para usarla en otro lado). Así queda huérfano y listo para recibir la celda. 💡 Con 1 o 2 días sin reina aceptan mejor la celda. Pero pueden empezar a criar celdas de emergencia: **destrúyelas** antes de introducir la celda real. """

GUIA_CELDAS = """ **¿Qué es?** Es el momento de introducir las celdas reales (ya operculadas) en los núcleos o colmenas huérfanas que preparaste en "Hacer núcleos". **Cómo se hace** 1. **Revisa el núcleo o la colmena antes:** confirma que no tiene reina y destruye cualquier celda de emergencia. 2. **Saca las celdas de la iniciadora con cuidado.** Sujétalas por la parte ancha (la base), nunca por la punta, y no las golpees ni las sacudas. 3. **Protégelas del frío y del sol:** llévalas en un recipiente tibio y con tapa, y colócalas cuanto antes. 4. **Colócala entre dos cuadros de cría**, con la punta hacia abajo: con un protector de celda o presionando suavemente la base contra el panal, sin aplastarla. 5. **Cierra y déjalo tranquilo.** La reina nace unos 12 días después del traslarve; evita abrir más de lo necesario. """

GUIA_NACIMIENTO = """ **¿Qué pasa?** Las reinas nacen de sus celdas (aprox. 12 días después del traslarve). **Qué hacer** - Casi nada: déjalas tranquilas. - Anota cuántas nacieron en "Cantidades". - La reina virgen sale a aparearse a partir de los 5-6 días de vida y empieza a poner 2 o 3 días después. - Evita abrir el núcleo estos días: podrías perjudicar a la reina durante los vuelos de fecundación. """

GUIA_POSTURA = """ **¿Qué es?** Es la inspección para confirmar que la reina nació, se apareó y ya está poniendo huevos. **Cómo se hace** 1. **Elige un día cálido y soleado**, en las horas centrales, con las pecoreadoras activas. 2. **Busca huevos:** uno por celda, en el fondo, y larvas pequeñas. Un patrón de cría compacto indica una buena reina. 3. **Si hay huevos, la reina está lista.** Anótala en "Cantidades" (reinas fecundadas con postura). 4. **Si todavía no hay huevos**, espera unos días y revisa de nuevo (hasta cerca del día 28). Si sigue sin poner, es posible que se perdiera en el vuelo de fecundación: une el núcleo a otro o dale otra celda. **🎨 Pinta (marca) la reina** Es muy recomendable hacerlo cuando ya está poniendo: - Atrápala con suavidad por el tórax o con un tubo/jaula de marcaje. - Pon un punto pequeño de pintura no tóxica para reinas sobre el tórax, sin tocar cabeza, alas ni abdomen. - Deja secar unos segundos antes de soltarla sobre el panal. - Así la encuentras más fácil y sabes su edad por el color del año. """

FASES = [
    {"id": "traslarve", "titulo": "Traslarve", "dias": 0, "corto": "Traslarve", "icono": "🥚", "guia": GUIA_TRASLARVE},
    {"id": "nucleos", "titulo": "Hacer núcleos", "dias": 7, "corto": "Núcleos", "icono": "📦", "guia": GUIA_NUCLEOS},
    {"id": "celdas", "titulo": "Insertar celdas", "dias": 9, "corto": "Celdas", "icono": "🧬", "guia": GUIA_CELDAS},
    {"id": "nacimiento", "titulo": "Nacimiento de reinas", "dias": 12, "corto": "Nacim.", "icono": "👑", "guia": GUIA_NACIMIENTO},
    {"id": "postura", "titulo": "Revisar postura", "dias": 21, "corto": "Postura", "icono": "🔍", "guia": GUIA_POSTURA},
]
FASE_POR_ID = {f["id"]: f for f in FASES}
DIAS_DEFECTO = {f["id"]: f["dias"] for f in FASES}

# Código internacional de colores para marcar reinas (según el año)
COLOR_MARCA = {1: ("blanco", "⚪"), 2: ("amarillo", "🟡"), 3: ("rojo", "🔴"), 4: ("verde", "🟢"), 0: ("azul", "🔵")}


def color_marca(anio):
    return COLOR_MARCA[anio % 5]


# ---------------------------------------------------------------------------
# UTILIDADES Y MODELO DE DATOS
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


def pct(num, den):
    return None if not den else num / den * 100


def fmt_pct(p):
    return "—" if p is None else f"{p:.1f}%"


def lote_desde_dict(d, indice=0):
    """Crea un lote a partir de un diccionario (acepta el formato antiguo)."""
    cant = entero(d.get("cant_traslarve"), 1, 1)
    dias = dict(DIAS_DEFECTO)
    for k, v in (d.get("dias") or {}).items():
        if k in dias and k != "traslarve":
            dias[k] = entero(v, dias[k], 1)
    tareas = {k: v for k, v in (d.get("tareas") or {}).items()
              if k in FASE_POR_ID and v in ("completada", "no_realizada")}
    lote = {
        "id": re.sub(r"\W", "", str(d.get("id") or "")) or nuevo_id(),
        "nombre": str(d["nombre"]),
        "traslarve_fecha": datetime.fromisoformat(str(d["traslarve_fecha"])).date(),
        "cant_traslarve": cant,
        "dias": dias,
        "tareas": tareas,
        "color": d.get("color") if color_valido(d.get("color")) else COLORES[indice % len(COLORES)],
        "tipo_crianza": str(d.get("tipo_crianza") or TIPOS_CRIANZA[0]),
        "apiario": str(d.get("apiario") or ""),
        "colmena_madre": str(d.get("colmena_madre") or ""),
        "observaciones": str(d.get("observaciones") or ""),
        "archivado": bool(d.get("archivado", False)),
    }
    # "cant_celdas" es el nombre antiguo de las celdas aceptadas
    lote["celdas_aceptadas"] = min(entero(d.get("celdas_aceptadas", d.get("cant_celdas", 0))), cant)
    for campo, _ in ETAPAS[2:]:
        lote[campo] = min(entero(d.get(campo, 0)), cant)
    return lote


def serializar_lote(lote):
    d = {k: v for k, v in lote.items() if k != "traslarve_fecha"}
    d["traslarve_fecha"] = lote["traslarve_fecha"].isoformat()
    d["dias"] = dict(lote["dias"])
    d["tareas"] = dict(lote["tareas"])
    return d


def datos_para_guardar(config, lotes):
    return {"version": 2, "config": {"dias": dict(config["dias"])},
            "lotes": [serializar_lote(l) for l in lotes]}


def estado_desde_datos(datos):
    """(config, lotes) desde datos JSON. Lanza excepción si el formato no es válido."""
    dias = dict(DIAS_DEFECTO)
    if isinstance(datos, list):          # formato antiguo: solo la lista de lotes
        lista = datos
    elif isinstance(datos, dict):
        lista = datos["lotes"]
        for k, v in ((datos.get("config") or {}).get("dias") or {}).items():
            if k in dias and k != "traslarve":
                dias[k] = entero(v, dias[k], 1)
    else:
        raise ValueError("formato no reconocido")
    return {"dias": dias}, [lote_desde_dict(d, i) for i, d in enumerate(lista)]


def validar_dias(dias):
    """Los días deben ir en orden creciente. Devuelve un mensaje de error o None."""
    for ant, act in zip(FASES, FASES[1:]):
        if dias[act["id"]] <= dias[ant["id"]]:
            return (f"'{act['titulo']}' (día {dias[act['id']]}) debe ser posterior a "
                    f"'{ant['titulo']}' (día {dias[ant['id']]}).")
    return None


def fecha_fase(lote, fase_id):
    return lote["traslarve_fecha"] + timedelta(days=lote["dias"][fase_id])


def nombre_fase(lote, fase):
    return f"{fase['titulo']} (Día {lote['dias'][fase['id']]})"


def estado_tarea(lote, fase_id, hoy):
    """pendiente / completada / no_realizada / vencida (esta última se calcula sola)."""
    manual = lote["tareas"].get(fase_id)
    if manual in ("completada", "no_realizada"):
        return manual
    return "vencida" if fecha_fase(lote, fase_id) < hoy else "pendiente"


def incoherencias(d):
    avisos = []
    for (c_ant, _), (c_act, _) in zip(ETAPAS, ETAPAS[1:]):
        if d[c_act] > d[c_ant]:
            avisos.append(f"{ETIQUETA[c_act]} ({d[c_act]}) supera a {ETIQUETA[c_ant].lower()} ({d[c_ant]}).")
    return avisos


def lineas_porcentajes(d):
    out = []
    for nombre, num, den in RATIOS:
        p = pct(d[num], d[den])
        detalle = f" ({d[num]}/{d[den]})" if p is not None else ""
        out.append(f"- **{nombre}:** {fmt_pct(p)}{detalle}")
    return "\n".join(out)


def plural(n, singular, plural_):
    return f"{n} {singular if n == 1 else plural_}"


def calcular_recordatorios(lotes, hoy):
    hoy_l, manana_l, vencidas, pendientes = [], [], {}, 0
    for l in lotes:
        if l["archivado"]:
            continue
        for fase in FASES:
            est = estado_tarea(l, fase["id"], hoy)
            f = fecha_fase(l, fase["id"])
            texto = f"{fase['titulo']} · {l['nombre']}"
            if est == "pendiente":
                pendientes += 1
                if f == hoy:
                    hoy_l.append(texto)
                elif f == hoy + timedelta(days=1):
                    manana_l.append(texto)
            elif est == "vencida":
                vencidas.setdefault(l["nombre"], []).append(fase["titulo"])
    return hoy_l, manana_l, vencidas, pendientes


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
        for fase in FASES:
            if estado_tarea(lote, fase["id"], hoy) != "pendiente":
                continue
            f = fecha_fase(lote, fase["id"])
            detalle = [f"Lote: {lote['nombre']}", nombre_fase(lote, fase)]
            if lote["apiario"]:
                detalle.append(f"Apiario: {lote['apiario']}")
            L += ["BEGIN:VEVENT",
                  f"UID:{lote['id']}-{fase['id']}@gestor-reinas",
                  f"DTSTAMP:{ahora}",
                  f"DTSTART;VALUE=DATE:{f:%Y%m%d}",
                  f"DTEND;VALUE=DATE:{f + timedelta(days=1):%Y%m%d}",
                  "SUMMARY:" + ics_texto(f"🐝 {lote['nombre']}: {fase['titulo']}"),
                  "DESCRIPTION:" + ics_texto("\n".join(detalle)),
                  "TRANSP:TRANSPARENT",
                  "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Recordatorio", "TRIGGER:PT8H", "END:VALARM",
                  "END:VEVENT"]
    L.append("END:VCALENDAR")
    return "\r\n".join(plegar(x) for x in L) + "\r\n"


# ---------------------------------------------------------------------------
# ALMACENAMIENTO: Supabase (permanente) o archivo local (se pierde al reiniciar)
# ---------------------------------------------------------------------------
@st.cache_resource
def conectar_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
    except Exception:
        return None, "Sin credenciales en Secrets"
    try:
        from supabase import create_client
        return create_client(url, key), None
    except Exception as e:
        return None, f"No se pudo conectar: {e}"


def leer_local():
    if not os.path.exists(ARCHIVO_DATOS):
        return None
    with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
        return json.load(f)


def escribir(config, lotes):
    """Guarda los datos. Devuelve un mensaje de error o None."""
    datos = datos_para_guardar(config, lotes)
    cli, _ = conectar_supabase()
    error = None
    if cli:
        try:
            cli.table(TABLA).upsert({"id": CLAVE_ESTADO, "datos": datos}).execute()
        except Exception as e:
            error = f"No se pudo guardar en Supabase: {e}"
    try:
        with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
    except OSError as e:
        if not cli:
            error = f"No se pudo guardar el archivo: {e}"
    return error


def cargar_todo():
    """Devuelve (config, lotes, error, modo). Nunca sobrescribe datos si hay error."""
    cli, _ = conectar_supabase()
    modo = "nube" if cli else "local"
    config_vacia = {"dias": dict(DIAS_DEFECTO)}
    try:
        datos, migrar = None, False
        if cli:
            r = cli.table(TABLA).select("datos").eq("id", CLAVE_ESTADO).execute()
            if r.data:
                datos = r.data[0]["datos"]
        if datos is None:
            datos = leer_local()
            migrar = cli is not None and datos is not None
        if datos is None:
            return config_vacia, [], None, modo
        config, lotes = estado_desde_datos(datos)
        if migrar:  # primera vez con Supabase: sube lo que había en el archivo local
            escribir(config, lotes)
        return config, lotes, None, modo
    except Exception as e:
        return config_vacia, [], f"{type(e).__name__}: {e}", modo


def guardar():
    """Guarda el estado de la sesión. No guarda si hubo un error al cargar (evita perder datos)."""
    if st.session_state.error_carga:
        st.session_state.error_guardado = "No se guardó: hubo un error al cargar los datos. Restaura un respaldo."
        return
    st.session_state.error_guardado = escribir(st.session_state.config, st.session_state.lotes)


def buscar_lote(lote_id):
    return next((l for l in st.session_state.lotes if l["id"] == lote_id), None)


def marcar(lote, fase_id, estado):
    if estado == "pendiente":
        lote["tareas"].pop(fase_id, None)
    else:
        lote["tareas"][fase_id] = estado
    guardar()


# ---------------------------------------------------------------------------
# VENTANAS (diálogos)
# ---------------------------------------------------------------------------
@st.dialog("🐝 Guía de la tarea")
def mostrar_guia(lote_id, fase_id):
    lote = buscar_lote(lote_id)
    if lote is None:
        st.warning("No se encontró el lote.")
        return
    fase = FASE_POR_ID[fase_id]
    est = estado_tarea(lote, fase_id, hoy_peru())
    icono, nombre_est, _ = ESTADOS[est]
    st.markdown(f"### {fase['icono']} {nombre_fase(lote, fase)}")
    st.caption(f"Lote: {lote['nombre']} · {fecha_fase(lote, fase_id):%d/%m/%Y} · {icono} {nombre_est}")
    c1, c2, c3 = st.columns(3)
    if c1.button("✅ Completada", key="dlg_comp"):
        marcar(lote, fase_id, "completada")
        st.rerun()
    if c2.button("⏭️ No realizada", key="dlg_nore"):
        marcar(lote, fase_id, "no_realizada")
        st.rerun()
    if c3.button("↩️ Pendiente", key="dlg_pend"):
        marcar(lote, fase_id, "pendiente")
        st.rerun()
    st.markdown("---")
    st.markdown(fase["guia"])
    if fase_id == "postura":
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
def boton_tarea(ctx, lote, fase, etiqueta, hoy):
    """Botón de una tarea: abre su guía. La clave lleva lote y estado para poder colorearlo con CSS."""
    est = estado_tarea(lote, fase["id"], hoy)
    icono, _, sufijo = ESTADOS[est]
    if st.button(f"{icono} {etiqueta}", key=f"t_{ctx}_{lote['id']}_{fase['id']}_{sufijo}"):
        mostrar_guia(lote["id"], fase["id"])


def inyectar_css(lotes):
    css = """ <style> /* Calendario y navegación: mantienen 7 / 3 columnas también en el celular */ .st-key-calendario, .st-key-calendario [data-testid="stVerticalBlock"] { gap: 2px !important; } .st-key-calendario [data-testid="stHorizontalBlock"], .st-key-nav [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 2px !important; } .st-key-calendario [data-testid="stColumn"], .st-key-calendario [data-testid="column"], .st-key-nav [data-testid="stColumn"], .st-key-nav [data-testid="column"] { min-width: 0 !important; flex: 1 1 0 !important; width: auto !important; } .st-key-calendario [data-testid="stColumn"], .st-key-calendario [data-testid="column"] { border: 1px solid rgba(128,128,128,.35); border-radius: 4px; padding: 2px; min-height: 72px; } /* Botones de tarea */ [class*="st-key-t_"], [class*="st-key-t_"] [data-testid="stButton"] { width: 100% !important; } [class*="st-key-t_"] button { width: 100% !important; min-height: 0 !important; line-height: 1.15 !important; padding: 4px 8px !important; color: #000 !important; border: none !important; border-left: 3px solid #333 !important; justify-content: flex-start !important; } [class*="st-key-t_"] button p { font-size: 14px !important; text-align: left; white-space: normal !important; } .st-key-calendario [class*="st-key-t_"] button { padding: 2px 3px !important; } .st-key-calendario [class*="st-key-t_"] button p { font-size: 10px !important; overflow-wrap: anywhere; } [class*="st-key-t_"] button:hover { filter: brightness(.93); } """
    # Cada lote conserva su color en todas sus tareas
    for l in lotes:
        css += f'[class*="st-key-t_"][class*="_{l["id"]}_"] button {{ background-color: {l["color"]} !important; }}\n'
    # Estados: completada (tachada y atenuada), no realizada (gris), vencida (borde rojo)
    css += """ [class*="st-key-t_"][class*="_comp"] button { opacity: .6; } [class*="st-key-t_"][class*="_comp"] button p { text-decoration: line-through; } [class*="st-key-t_"][class*="_nore"] button { background-color: #d9d9d9 !important; color: #555 !important; } [class*="st-key-t_"][class*="_nore"] button p { text-decoration: line-through; } [class*="st-key-t_"][class*="_venc"] button { box-shadow: inset 0 0 0 2px #d62828; font-weight: 700; } </style> """
    st.markdown(css, unsafe_allow_html=True)


def mostrar_recordatorios(lotes, hoy):
    hoy_l, manana_l, vencidas, pendientes = calcular_recordatorios(lotes, hoy)
    for nombre, tareas in vencidas.items():
        n = len(tareas)
        st.error(f"⚠️ **{esc_md(nombre)}** tiene {plural(n, 'tarea vencida', 'tareas vencidas')}: {', '.join(tareas)}.")
    if hoy_l:
        st.warning("🔔 **Hoy corresponde:**\n" + "\n".join(f"- {esc_md(x)}" for x in hoy_l))
    if manana_l:
        st.info("📅 **Mañana corresponde:**\n" + "\n".join(f"- {esc_md(x)}" for x in manana_l))
    if pendientes:
        st.caption(f"Hay {plural(pendientes, 'actividad pendiente', 'actividades pendientes')}.")
    elif not vencidas:
        st.caption("✅ No tienes actividades pendientes.")


def eventos_por_fecha(lotes):
    ev = {}
    for l in lotes:
        if l["archivado"]:
            continue
        for fase in FASES:
            ev.setdefault(fecha_fase(l, fase["id"]), []).append((l, fase))
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
                    for lote, fase in eventos.get(f, []):
                        nombre = lote["nombre"]
                        corto = nombre if len(nombre) <= 10 else nombre[:9] + "…"
                        boton_tarea("cal", lote, fase, f"{esc_md(corto)} · {fase['corto']}", hoy)


def vista_semana(ancla, eventos, hoy):
    lunes = ancla - timedelta(days=ancla.weekday())
    st.markdown(f"<h4 style='text-align:center; margin:8px 0 4px;'>Semana del {lunes:%d/%m} al {lunes + timedelta(days=6):%d/%m/%Y}</h4>",
                unsafe_allow_html=True)
    for k in range(7):
        f = lunes + timedelta(days=k)
        marca = " · 🟡 **Hoy**" if f == hoy else ""
        st.markdown(f"**{DIAS_SEMANA_LARGO[k]} {f:%d/%m}**{marca}")
        evs = eventos.get(f, [])
        if not evs:
            st.caption("Sin actividades")
        for lote, fase in evs:
            boton_tarea("sem", lote, fase, f"{esc_md(lote['nombre'])} · {nombre_fase(lote, fase)}", hoy)


def cabecera_lote(lote, hoy):
    conteo = {}
    for fase in FASES:
        e = estado_tarea(lote, fase["id"], hoy)
        conteo[e] = conteo.get(e, 0) + 1
    chips = " · ".join(f"{ESTADOS[e][0]} {conteo[e]}" for e in ("vencida", "pendiente", "completada", "no_realizada") if conteo.get(e))
    exito = pct(lote["reinas_fecundadas"], lote["cant_traslarve"])
    extra = f" | Éxito final: <b>{exito:.1f}%</b>" if exito is not None else ""
    tipo = lote["tipo_crianza"] if lote["tipo_crianza"] != TIPOS_CRIANZA[0] else ""
    detalle = " · ".join(x for x in (tipo, lote["apiario"], chips) if x)
    return (
        f"<div style='background-color:{lote['color']}; padding:10px 12px; border-radius:8px; color:#000; margin-top:12px;'>"
        f"<b>{html.escape(lote['nombre'])}</b> | Traslarve: {lote['traslarve_fecha']:%d/%m/%Y} | "
        f"Larvas: <b>{lote['cant_traslarve']}</b>{extra}"
        f"<br><span style='font-size:12px;'>{html.escape(detalle)}</span></div>"
    )


def entradas_dias(prefijo, valores):
    """Un campo numérico por etapa (el traslarve siempre es el día 0)."""
    dias = {"traslarve": 0}
    for fase in FASES[1:]:
        dias[fase["id"]] = st.number_input(
            f"{fase['titulo']} (días desde el traslarve)", min_value=1, step=1,
            value=int(valores[fase["id"]]), key=f"{prefijo}_{fase['id']}")
    return dias


def tarjeta_lote(lote, hoy):
    lid = lote["id"]
    st.markdown(cabecera_lote(lote, hoy), unsafe_allow_html=True)
    with st.expander("Abrir / editar lote"):
        tab_t, tab_c, tab_d = st.tabs(["Tareas", "Cantidades", "Datos"])

        with tab_t:
            for fase in FASES:
                f = fecha_fase(lote, fase["id"])
                etiqueta = f"{nombre_fase(lote, fase)} · {DIAS_SEMANA_LARGO[f.weekday()][:3]} {f:%d/%m/%Y}"
                boton_tarea("lot", lote, fase, esc_md(etiqueta), hoy)
            st.caption("Toca una tarea para ver cómo se hace y cambiar su estado.")

        with tab_c:
            with st.form(f"cant_{lid}"):
                nuevos = {}
                for campo, etiqueta in ETAPAS[1:]:
                    nuevos[campo] = st.number_input(
                        etiqueta, min_value=0, max_value=lote["cant_traslarve"], step=1,
                        value=int(lote[campo]), key=f"q_{lid}_{campo}")
                if st.form_submit_button("Guardar cantidades"):
                    lote.update(nuevos)
                    guardar()
                    st.session_state.mensaje = "Cantidades guardadas."
                    st.rerun()
            st.markdown(f"**Rendimiento** (sobre {lote['cant_traslarve']} larvas)")
            st.markdown(lineas_porcentajes(lote))
            for aviso in incoherencias(lote):
                st.warning("⚠️ " + aviso)

        with tab_d:
            with st.form(f"edit_{lid}"):
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
                st.markdown("**Días de cada etapa (solo para este lote)**")
                dias = entradas_dias(f"e_dia_{lid}", lote["dias"])
                if st.form_submit_button("Guardar cambios"):
                    error = validar_dias(dias)
                    if not nombre.strip():
                        st.warning("El nombre no puede estar vacío.")
                    elif error:
                        st.warning(error)
                    else:
                        lote.update({
                            "nombre": nombre.strip(), "traslarve_fecha": fecha, "cant_traslarve": int(cant),
                            "tipo_crianza": tipo, "apiario": apiario.strip(), "colmena_madre": madre.strip(),
                            "observaciones": obs, "color": color, "dias": dias,
                        })
                        for campo, _ in ETAPAS[1:]:   # las cantidades no pueden superar las larvas
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


# ---------------------------------------------------------------------------
# PÁGINA
# ---------------------------------------------------------------------------
HOY = hoy_peru()

if "lotes" not in st.session_state:
    (st.session_state.config, st.session_state.lotes,
     st.session_state.error_carga, st.session_state.modo) = cargar_todo()
    st.session_state.setdefault("error_guardado", None)
    st.session_state.cal_ancla = HOY
st.session_state.setdefault("cal_vista", "Mes")

lotes = st.session_state.lotes
config = st.session_state.config
inyectar_css(lotes)

st.title("🐝 Gestor de Crianza de Reinas")
st.caption(f"Hoy: {DIAS_SEMANA_LARGO[HOY.weekday()]} {HOY:%d/%m/%Y} (hora de Perú)")

if "mensaje" in st.session_state:
    st.success(st.session_state.pop("mensaje"))
if st.session_state.error_carga:
    st.error(f"⚠️ No se pudieron leer los datos ({st.session_state.error_carga}). "
             "No se guardará nada para no perder información. Restaura un respaldo en Ajustes.")
if st.session_state.get("error_guardado"):
    st.error(f"⚠️ {st.session_state.error_guardado}")

mostrar_recordatorios(lotes, HOY)

tab_cal, tab_lotes, tab_hist, tab_ajustes = st.tabs(["📅 Calendario", "📋 Lotes", "📊 Historial", "⚙️ Ajustes"])

# ----------------------------- CALENDARIO ---------------------------------
with tab_cal:
    eventos = eventos_por_fecha(lotes)

    proximas = sorted(
        ((f, l, fase) for f, evs in eventos.items() for l, fase in evs
         if f >= HOY and estado_tarea(l, fase["id"], HOY) == "pendiente"),
        key=lambda x: (x[0], x[1]["nombre"], x[2]["dias"]),
    )[:6]
    if proximas:
        st.subheader("⏰ Próximas actividades")
        with st.container(key="proximas"):
            for f, l, fase in proximas:
                d = (f - HOY).days
                cuando = "¡Hoy!" if d == 0 else ("Mañana" if d == 1 else f"en {d} días")
                boton_tarea("prox", l, fase, f"{f:%d/%m} · {esc_md(l['nombre'])} · {fase['titulo']} ({cuando})", HOY)

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
    st.caption("⏳ Pendiente · ✅ Completada · ⏭️ No realizada · ⚠️ Vencida (se marca sola al pasar el día). "
               "Cada lote tiene su propio color.")

    with st.expander("📲 Exportar al calendario del teléfono (.ics)"):
        st.caption("Descarga el archivo y ábrelo en tu teléfono: se agregan las tareas pendientes como eventos de día "
                   "completo con aviso a las 8:00 (Google Calendar, iPhone y otros). Si lo importas de nuevo, "
                   "los eventos se actualizan en vez de duplicarse.")
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
        with st.form("form_lote", clear_on_submit=True):
            nombre_n = st.text_input("Nombre del lote", placeholder="Ej: Lote A")
            fecha_n = st.date_input("Fecha de traslarve", value=HOY)
            cant_n = st.number_input("Larvas traslarvadas (Día 0)", min_value=1, value=20, step=1)
            tipo_n = st.selectbox("Tipo de crianza", TIPOS_CRIANZA)
            apiario_n = st.text_input("Apiario")
            madre_n = st.text_input("Colmena madre")
            obs_n = st.text_area("Observaciones")
            st.markdown("**Días de cada etapa** (por defecto los de Ajustes; solo afectan a este lote)")
            dias_n = entradas_dias("nd", config["dias"])
            enviado = st.form_submit_button("Registrar lote y guardar")
        if enviado:
            error = validar_dias(dias_n)
            if not nombre_n.strip():
                st.warning("⚠️ Escribe un nombre para el lote.")
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
                    "colmena_madre": madre_n.strip(), "observaciones": obs_n, "dias": dias_n, "color": color,
                }))
                guardar()
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
            tot = {campo: sum(l[campo] for l in sel) for campo, _ in ETAPAS}
            st.subheader("Totales")
            st.markdown(f"Lotes incluidos: **{len(sel)}**")
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
                filas.append({
                    "Lote": l["nombre"], "Fecha": f"{l['traslarve_fecha']:%d/%m/%Y}", "Tipo": l["tipo_crianza"],
                    "Apiario": l["apiario"], "Larvas": l["cant_traslarve"], "Aceptadas": l["celdas_aceptadas"],
                    "Nacidas": l["reinas_nacidas"], "Con postura": l["reinas_fecundadas"],
                    "% Aceptación": fmt_pct(r["Aceptación"]), "% Nacimiento": fmt_pct(r["Nacimiento"]),
                    "% Fecundación": fmt_pct(r["Fecundación"]), "% Éxito final": fmt_pct(r["Éxito final"]),
                    "Estado": "Archivado" if l["archivado"] else "Activo",
                })
                numericos.append({"Lote": l["nombre"], "% Éxito final": r["Éxito final"]})
            st.dataframe(pd.DataFrame(filas), hide_index=True)
            df_num = pd.DataFrame(numericos)
            if df_num["% Éxito final"].notna().any():
                st.markdown("**Comparación del éxito final entre lotes (%)**")
                st.bar_chart(df_num.set_index("Lote")["% Éxito final"])

            st.subheader("Comparación por tipo de crianza")
            por_tipo = {}
            for l in sel:
                g = por_tipo.setdefault(l["tipo_crianza"], {c: 0 for c, _ in ETAPAS})
                g["lotes"] = g.get("lotes", 0) + 1
                for c, _ in ETAPAS:
                    g[c] += l[c]
            filas_t = [{
                "Tipo de crianza": t, "Lotes": g["lotes"], "Larvas": g["cant_traslarve"],
                "% Aceptación": fmt_pct(pct(g["celdas_aceptadas"], g["cant_traslarve"])),
                "% Nacimiento": fmt_pct(pct(g["reinas_nacidas"], g["celdas_insertadas"])),
                "% Fecundación": fmt_pct(pct(g["reinas_fecundadas"], g["reinas_nacidas"])),
                "% Éxito final": fmt_pct(pct(g["reinas_fecundadas"], g["cant_traslarve"])),
            } for t, g in por_tipo.items()]
            st.dataframe(pd.DataFrame(filas_t), hide_index=True)

# ------------------------------- AJUSTES ----------------------------------
with tab_ajustes:
    st.subheader("⏱️ Días de cada etapa (valores por defecto)")
    st.caption("Se usan al crear lotes nuevos. Cada lote guarda su propia copia, así que cambiar esto "
               "no modifica los lotes existentes (se editan dentro de cada lote, en «Datos»).")
    with st.form("form_config"):
        dias_cfg = entradas_dias("cfg", config["dias"])
        if st.form_submit_button("Guardar días por defecto"):
            error = validar_dias(dias_cfg)
            if error:
                st.warning(error)
            else:
                config["dias"] = dias_cfg
                guardar()
                st.session_state.mensaje = "Días por defecto guardados."
                st.rerun()

    st.subheader("💾 Almacenamiento")
    cliente, motivo = conectar_supabase()
    if cliente:
        st.success("☁️ Los datos se guardan en Supabase: no se pierden al reiniciar la app.")
    else:
        st.warning("⚠️ Los datos se guardan en un archivo del servidor, que se puede borrar cuando la app se reinicia. "
                   "Activa Supabase (gratis) o descarga respaldos con frecuencia.")
        with st.expander("Cómo activar el almacenamiento permanente (Supabase)"):
            st.markdown(
                "1. Crea una cuenta y un proyecto en **supabase.com**.\n"
                "2. En **SQL Editor**, ejecuta este código:"
            )
            st.code(
                "create table if not exists estado_app (\n"
                " id text primary key,\n"
                " datos jsonb not null\n"
                ");\n"
                "alter table estado_app enable row level security;",
                language="sql",
            )
            st.markdown(
                "3. En **Project Settings → API**, copia la *Project URL* y la clave secreta (*service_role*).\n"
                "4. En Streamlit Cloud: **Settings → Secrets**, pega:"
            )
            st.code('[supabase]\nurl = "https://TU-PROYECTO.supabase.co"\nkey = "TU_CLAVE_SERVICE_ROLE"', language="toml")
            st.markdown("5. Agrega `supabase` a tu `requirements.txt` y reinicia la app. "
                        "Tus datos actuales se suben solos la primera vez.")
            st.caption("Nunca pongas la clave dentro del código: solo en Secrets.")
            if motivo:
                st.caption(f"Estado actual: {motivo}")

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
