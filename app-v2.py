import streamlit as st
from datetime import datetime, timedelta, date
import calendar
import json
import os
import re
import html

# Requiere Streamlit >= 1.39 (st.dialog y st.container(key=...))
st.set_page_config(page_title="Gestor Apícola de Reinas", page_icon="🐝", layout="wide")

ARCHIVO_DATOS = "lotes_reinas.json"
COLORES = ["#ff9999", "#66b3ff", "#99ff99", "#ffcc99", "#c299ff", "#ff99ff", "#ffe666"]
DIAS_SEMANA = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]
MESES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

# ---------------------------------------------------------------------------
# GUÍAS DE CADA TAREA (se muestran al tocar la tarea en el calendario)
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
6. **Al día siguiente** revisa cuántas copas aceptaron las abejas y anótalo en "Celdas aceptadas".
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
Es el momento de introducir las celdas reales (ya operculadas) en los núcleos o colmenas huérfanas que preparaste en "Hacer núcleos".

**Cómo se hace**
1. **Revisa el núcleo o la colmena antes:** confirma que no tiene reina y destruye cualquier celda de emergencia.
2. **Saca las celdas de la iniciadora con cuidado.** Sujétalas por la parte ancha (la base), nunca por la punta, y no las golpees ni las sacudas.
3. **Protégelas del frío y del sol:** llévalas en un recipiente tibio y con tapa, y colócalas cuanto antes.
4. **Colócala entre dos cuadros de cría**, con la punta hacia abajo: con un protector de celda o presionando suavemente la base contra el panal, sin aplastarla.
5. **Cierra y déjalo tranquilo.** La reina nace alrededor del día 12; evita abrir más de lo necesario.
"""

GUIA_NACIMIENTO = """
**¿Qué pasa?**
Las reinas nacen de sus celdas (aprox. 12 días después del traslarve).

**Qué hacer**
- Casi nada: déjalas tranquilas.
- La reina virgen sale a aparearse a partir de los 5-6 días de vida y empieza a poner 2 o 3 días después.
- Evita abrir el núcleo estos días: podrías perjudicar a la reina durante los vuelos de fecundación.
"""

GUIA_POSTURA = """
**¿Qué es?**
Es la inspección para confirmar que la reina nació, se apareó y ya está poniendo huevos.

**Cómo se hace**
1. **Elige un día cálido y soleado**, en las horas centrales, con las pecoreadoras activas.
2. **Busca huevos:** uno por celda, en el fondo, y larvas pequeñas. Un patrón de cría compacto indica una buena reina.
3. **Si hay huevos, la reina está lista.** Anota el resultado.
4. **Si todavía no hay huevos**, espera unos días y revisa de nuevo (hasta cerca del día 28). Si sigue sin poner, es posible que se perdiera en el vuelo de fecundación: une el núcleo a otro o dale otra celda.

**🎨 Pinta (marca) la reina**
Es muy recomendable hacerlo cuando ya está poniendo:
- Atrápala con suavidad por el tórax o con un tubo/jaula de marcaje.
- Pon un punto pequeño de pintura no tóxica para reinas sobre el tórax, sin tocar cabeza, alas ni abdomen.
- Deja secar unos segundos antes de soltarla sobre el panal.
- Así la encuentras más fácil y sabes su edad por el color del año.
"""

FASES = [
    {"id": "traslarve", "dias": 0, "nombre": "Traslarve (Día 0)", "corto": "Traslarve", "icono": "🥚", "guia": GUIA_TRASLARVE},
    {"id": "nucleos", "dias": 7, "nombre": "Hacer núcleos (Día 7)", "corto": "Núcleos", "icono": "📦", "guia": GUIA_NUCLEOS},
    {"id": "celdas", "dias": 9, "nombre": "Insertar celdas (Día 9)", "corto": "Celdas", "icono": "🧬", "guia": GUIA_CELDAS},
    {"id": "nacimiento", "dias": 12, "nombre": "Nacimiento de reinas (Día 12)", "corto": "Nacim.", "icono": "👑", "guia": GUIA_NACIMIENTO},
    {"id": "postura", "dias": 21, "nombre": "Revisar postura (Día 21)", "corto": "Postura", "icono": "🔍", "guia": GUIA_POSTURA},
]
FASE_POR_ID = {f["id"]: f for f in FASES}

# Código internacional de colores para marcar reinas según el último dígito del año
COLOR_MARCA = {1: ("blanco", "⚪"), 2: ("amarillo", "🟡"), 3: ("rojo", "🔴"), 4: ("verde", "🟢"), 0: ("azul", "🔵")}


def color_marca(anio):
    return COLOR_MARCA[anio % 5]


# ---------------------------------------------------------------------------
# DATOS
# ---------------------------------------------------------------------------
def serializar(lotes):
    return [
        {
            "nombre": l["nombre"],
            "traslarve_fecha": l["traslarve_fecha"].isoformat(),
            "cant_traslarve": l["cant_traslarve"],
            "cant_celdas": l["cant_celdas"],
            "color": l["color"],
        }
        for l in lotes
    ]


def deserializar(datos):
    lotes = []
    for d in datos:
        cant = int(d["cant_traslarve"])
        color = str(d.get("color", ""))
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            color = COLORES[len(lotes) % len(COLORES)]
        lotes.append({
            "nombre": str(d["nombre"]),
            "traslarve_fecha": datetime.fromisoformat(d["traslarve_fecha"]),
            "cant_traslarve": cant,
            "cant_celdas": min(int(d.get("cant_celdas", 0)), cant),
            "color": color,
        })
    return lotes


def guardar_lotes(lotes):
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
        json.dump(serializar(lotes), f, ensure_ascii=False, indent=2)


def cargar_lotes():
    """Devuelve (lotes, error). Si el archivo está dañado no lo sobrescribe en silencio."""
    if not os.path.exists(ARCHIVO_DATOS):
        return [], None
    try:
        with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
            return deserializar(json.load(f)), None
    except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        return [], str(e)


def fecha_fase(lote, fase):
    return (lote["traslarve_fecha"] + timedelta(days=fase["dias"])).date()


def esc_md(texto):
    """Escapa caracteres de Markdown para usar texto del usuario en etiquetas de botones."""
    return re.sub(r"([\\`*_\[\]~$<>])", r"\\\1", texto)


# ---------------------------------------------------------------------------
# VENTANA DE AYUDA (se abre al tocar una tarea)
# ---------------------------------------------------------------------------
@st.dialog("🐝 Guía de la tarea")
def mostrar_guia(fase_id, nombre_lote, anio_lote, fecha):
    fase = FASE_POR_ID[fase_id]
    st.markdown(f"### {fase['icono']} {fase['nombre']}")
    st.caption(f"Lote: {nombre_lote} · {fecha:%d/%m/%Y}")
    st.markdown(fase["guia"])
    if fase_id == "postura":
        nombre_color, emoji = color_marca(anio_lote)
        st.info(f"Color para marcar las reinas de este lote: {emoji} **{nombre_color}** (código internacional para el año {anio_lote}).")


def boton_tarea(prefijo, i, lote, fase, etiqueta):
    """Botón que abre la guía de la tarea. La clave incluye el lote y la fase."""
    if st.button(etiqueta, key=f"{prefijo}_{i}_{fase['id']}"):
        mostrar_guia(fase["id"], lote["nombre"], lote["traslarve_fecha"].year, fecha_fase(lote, fase))


def inyectar_css(lotes):
    css = """
    <style>
    /* Calendario: mantiene 7 columnas también en el celular */
    .st-key-calendario, .st-key-calendario [data-testid="stVerticalBlock"] { gap: 2px !important; }
    .st-key-calendario [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 2px !important; }
    .st-key-calendario [data-testid="stColumn"], .st-key-calendario [data-testid="column"] {
        min-width: 0 !important; flex: 1 1 0 !important; width: auto !important;
        border: 1px solid rgba(128,128,128,.35); border-radius: 4px; padding: 2px; min-height: 72px;
    }
    /* Botones de tarea (calendario y próximas actividades) */
    .st-key-calendario [data-testid="stButton"], .st-key-proximas [data-testid="stButton"] { width: 100% !important; }
    .st-key-calendario button, .st-key-proximas button {
        width: 100% !important; min-height: 0 !important; line-height: 1.15 !important;
        padding: 2px 4px !important; color: #000 !important; border: none !important;
        border-left: 3px solid #333 !important; justify-content: flex-start !important;
    }
    .st-key-calendario button p { font-size: 10px !important; white-space: normal !important; overflow-wrap: anywhere; text-align: left; }
    .st-key-proximas button p { font-size: 14px !important; text-align: left; }
    .st-key-calendario button:hover, .st-key-proximas button:hover { filter: brightness(.93); }
    """
    for i, lote in enumerate(lotes):
        css += (
            f'.st-key-calendario [class*="st-key-cal_{i}_"] button, '
            f'.st-key-proximas [class*="st-key-prox_{i}_"] button '
            f'{{ background-color: {lote["color"]} !important; }}\n'
        )
    css += "</style>"
    st.markdown(css, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# PÁGINA
# ---------------------------------------------------------------------------
if "lotes" not in st.session_state:
    st.session_state.lotes, st.session_state.error_carga = cargar_lotes()

lotes = st.session_state.lotes
inyectar_css(lotes)

st.title("🐝 Gestor de Crianza de Reinas")
st.write("Controla tus lotes, calcula fechas clave, registra celdas logradas y visualízalo todo en el calendario. Toca una tarea del calendario para ver cómo se hace.")

if st.session_state.error_carga:
    st.error(
        f"⚠️ No se pudo leer '{ARCHIVO_DATOS}' ({st.session_state.error_carga}). "
        "Restaura un respaldo para no perder datos."
    )

# Formulario de nuevo lote
with st.form("form_lote", clear_on_submit=True):
    st.subheader("➕ Registrar Nuevo Lote")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        nombre_lote = st.text_input("Nombre del Lote", placeholder="Ej: Lote A")
        fecha_traslarve = st.date_input("Fecha de Traslarve", value=datetime.today())
    with col_f2:
        cant_traslarve = st.number_input("Cantidad de Traslarves (Día 0)", min_value=1, value=20, step=1)
    submitted = st.form_submit_button("Registrar Lote y Guardar")

if submitted:
    if not nombre_lote.strip():
        st.warning("⚠️ Por favor escribe un nombre para el lote.")
    elif st.session_state.error_carga:
        st.error("No puedo guardar mientras el archivo esté dañado: se perderían datos. Restaura un respaldo primero.")
    else:
        usados = {l["color"] for l in lotes}
        color = next((c for c in COLORES if c not in usados), COLORES[len(lotes) % len(COLORES)])
        lotes.append({
            "nombre": nombre_lote.strip(),
            "traslarve_fecha": datetime.combine(fecha_traslarve, datetime.min.time()),
            "cant_traslarve": int(cant_traslarve),
            "cant_celdas": 0,
            "color": color,
        })
        guardar_lotes(lotes)
        st.session_state.mensaje = f"¡Lote '{nombre_lote.strip()}' guardado correctamente!"
        st.rerun()

if "mensaje" in st.session_state:
    st.success(st.session_state.pop("mensaje"))

# Gestión de lotes
if lotes:
    st.markdown("---")
    st.subheader("📋 Gestión y Seguimiento de Lotes")
    for idx, lote in enumerate(lotes):
        st.markdown(
            f"<div style='background-color: {lote['color']}; padding: 10px 12px; border-radius: 8px 8px 0 0; color: #000;'>"
            f"<b>Lote: {html.escape(lote['nombre'])}</b> | Traslarve: {lote['traslarve_fecha']:%d/%m/%Y} | "
            f"Larvas: <b>{lote['cant_traslarve']}</b></div>",
            unsafe_allow_html=True,
        )
        cols = st.columns([2, 2, 1])
        with cols[0]:
            nueva = st.number_input(
                "Celdas aceptadas/logradas",
                min_value=0, max_value=lote["cant_traslarve"],
                value=int(lote["cant_celdas"]), key=f"celdas_{idx}",
            )
            if nueva != lote["cant_celdas"]:
                lote["cant_celdas"] = int(nueva)
                guardar_lotes(lotes)
                st.rerun()
        with cols[1]:
            if lote["cant_celdas"] > 0:
                pct = lote["cant_celdas"] / lote["cant_traslarve"] * 100
                st.markdown(
                    f"<p style='padding-top: 25px; margin:0;'><b>Éxito:</b> {pct:.1f}% "
                    f"({lote['cant_celdas']}/{lote['cant_traslarve']})</p>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<p style='padding-top: 25px; margin:0; color: #666;'><i>Sin celdas registradas</i></p>",
                    unsafe_allow_html=True,
                )
        with cols[2]:
            st.markdown("<p style='margin:0; font-size:10px;'>&nbsp;</p>", unsafe_allow_html=True)
            if st.button("🗑️ Eliminar", key=f"del_{idx}", help="Eliminar este lote"):
                lotes.pop(idx)
                guardar_lotes(lotes)
                st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

# Eventos de todos los lotes, indexados por fecha
hoy = date.today()
eventos_por_fecha = {}
for i, lote in enumerate(lotes):
    for fase in FASES:
        eventos_por_fecha.setdefault(fecha_fase(lote, fase), []).append((i, fase))

# Próximas actividades (también se pueden tocar)
proximas = sorted(
    ((f, i, fase) for f, evs in eventos_por_fecha.items() for i, fase in evs if f >= hoy),
    key=lambda x: (x[0], x[1], x[2]["dias"]),
)[:8]
if proximas:
    st.markdown("---")
    st.subheader("⏰ Próximas actividades")
    with st.container(key="proximas"):
        for f, i, fase in proximas:
            dias = (f - hoy).days
            cuando = "¡Hoy!" if dias == 0 else ("Mañana" if dias == 1 else f"en {dias} días")
            etiqueta = f"{f:%d/%m} · {esc_md(lotes[i]['nombre'])} · {fase['nombre']} ({cuando})"
            boton_tarea("prox", i, lotes[i], fase, etiqueta)

# Calendario
st.markdown("---")
st.subheader("📅 Calendario Apícola")

meses = {(hoy.year, hoy.month)} | {(f.year, f.month) for f in eventos_por_fecha}

with st.container(key="calendario"):
    for anio, mes in sorted(meses):
        st.markdown(f"<h4 style='text-align: center; margin: 16px 0 4px;'>{MESES_ES[mes]} {anio}</h4>", unsafe_allow_html=True)
        st.markdown(
            "<div style='display:flex; gap:2px; text-align:center; font-weight:bold; font-size:12px;'>"
            + "".join(f"<div style='flex:1 1 0; min-width:0;'>{d}</div>" for d in DIAS_SEMANA)
            + "</div>",
            unsafe_allow_html=True,
        )
        for semana in calendar.monthcalendar(anio, mes):
            columnas = st.columns(7)
            for col, dia in zip(columnas, semana):
                if dia == 0:
                    continue
                f = date(anio, mes, dia)
                with col:
                    numero = f"{dia}"
                    if f == hoy:
                        numero = f"<span style='background:#f5b301; color:#000; border-radius:10px; padding:0 6px;'>{dia}</span>"
                    st.markdown(f"<div style='font-weight:bold; font-size:12px;'>{numero}</div>", unsafe_allow_html=True)
                    for i, fase in eventos_por_fecha.get(f, []):
                        nombre = lotes[i]["nombre"]
                        corto = nombre if len(nombre) <= 10 else nombre[:9] + "…"
                        boton_tarea("cal", i, lotes[i], fase, f"{esc_md(corto)} · {fase['corto']}")

# Copia de seguridad
st.markdown("---")
with st.expander("💾 Copia de Seguridad (Exportar / Importar datos)"):
    st.caption("Guarda una copia en tu celular si vas a dejar de usar la app por varios días, ya que el servidor gratuito puede reiniciarse.")
    if lotes:
        st.download_button(
            label="⬇️ Descargar respaldo (.json)",
            data=json.dumps(serializar(lotes), ensure_ascii=False, indent=2),
            file_name="respaldo_reinas.json",
            mime="application/json",
        )
    archivo_subido = st.file_uploader("⬆️ Restaurar desde archivo (.json)", type=["json"], key="uploader")
    if archivo_subido is not None and st.session_state.get("ultimo_import") != archivo_subido.file_id:
        st.session_state.ultimo_import = archivo_subido.file_id
        try:
            datos = json.loads(archivo_subido.read().decode("utf-8"))
            nuevos = deserializar(datos)
            with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
            st.session_state.lotes = nuevos
            st.session_state.error_carga = None
            st.session_state.mensaje = "✅ ¡Datos restaurados correctamente!"
            st.rerun()
        except Exception as e:
            st.error(f"El archivo no es un respaldo válido: {e}")
