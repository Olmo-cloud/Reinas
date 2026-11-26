impimport streamlit as st
from datetime import datetime, timedelta
import calendar
import json
import os

# Configuración de la página web
st.set_page_config(page_title="Gestor Apícola de Reinas", page_icon="🐝", layout="centered")

ARCHIVO_DATOS = "lotes_reinas.json"
colores_disponibles = ["#ff9999", "#66b3ff", "#99ff99", "#ffcc99", "#c299ff", "#ff99ff", "#ffe666"]

def cargar_lotes():
    """Carga los lotes guardados desde el archivo local."""
    if os.path.exists(ARCHIVO_DATOS):
        try:
            with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
                datos = json.load(f)
                for lote in datos:
                    lote["traslarve_fecha"] = datetime.fromisoformat(lote["traslarve_fecha"])
                    lote["cronograma"] = {
                        k: datetime.fromisoformat(v) for k, v in lote["cronograma"].items()
                    }
                return datos
        except Exception:
            return []
    return []

def guardar_lotes(lotes):
    """Guarda los lotes en un archivo JSON para mantener la persistencia."""
    datos_serializables = []
    for lote in lotes:
        datos_serializables.append({
            "nombre": lote["nombre"],
            "traslarve_fecha": lote["traslarve_fecha"].isoformat(),
            "cant_traslarve": lote["cant_traslarve"],
            "cant_celdas": lote["cant_celdas"],
            "cronograma": {k: v.isoformat() for k, v in lote["cronograma"].items()},
            "color": lote["color"]
        })
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
        json.dump(datos_serializables, f, ensure_ascii=False, indent=2)

# Inicializar sesión cargando lo que ya estaba guardado
if "lotes" not in st.session_state:
    st.session_state.lotes = cargar_lotes()

st.title("🐝 Gestor de Crianza de Reinas")
st.write("Controla tus lotes, calcula fechas clave, registra celdas logradas y visualízalo todo en el calendario.")

# Formulario para ingresar un nuevo lote
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
    else:
        t = datetime.combine(fecha_traslarve, datetime.min.time())
        cronograma = {
            "Traslarve (Día 0)": t,
            "Hacer núcleos (Día 7)": t + timedelta(days=7),
            "Insertar celdas (Día 9)": t + timedelta(days=9),
            "Revisar postura (Día 21)": t + timedelta(days=21)
        }
        
        color = colores_disponibles[len(st.session_state.lotes) % len(colores_disponibles)]
        
        st.session_state.lotes.append({
            "nombre": nombre_lote.strip(),
            "traslarve_fecha": t,
            "cant_traslarve": int(cant_traslarve),
            "cant_celdas": 0,
            "cronograma": cronograma,
            "color": color
        })
        guardar_lotes(st.session_state.lotes)
        st.success(f"¡Lote '{nombre_lote}' guardado correctamente!")
        st.rerun()

# Sección de Gestión de Lotes (si hay lotes registrados)
if st.session_state.lotes:
    st.markdown("---")
    st.subheader("📋 Gestión y Seguimiento de Lotes")
    
    for idx, lote in enumerate(st.session_state.lotes):
        with st.container():
            st.markdown(
                f"<div style='background-color: {lote['color']}; padding: 10px 12px; border-radius: 8px 8px 0 0; color: #000;'>"
                f"<b>Lote: {lote['nombre']}</b> | Traslarve: {lote['traslarve_fecha'].strftime('%d/%m/%Y')} | Larvas: <b>{lote['cant_traslarve']}</b>"
                f"</div>", 
                unsafe_allow_html=True
            )
            
            cols = st.columns([2, 2, 1])
            with cols[0]:
                valor_actual = lote['cant_celdas'] if lote['cant_celdas'] is not None else 0
                nueva_celdas = st.number_input(
                    "Celdas aceptadas/logradas", 
                    min_value=0, 
                    max_value=lote['cant_traslarve'], 
                    value=int(valor_actual), 
                    key=f"celdas_{idx}"
                )
                if nueva_celdas != valor_actual:
                    lote['cant_celdas'] = int(nueva_celdas)
                    guardar_lotes(st.session_state.lotes)
                    st.rerun()
            
            with cols[1]:
                if lote['cant_celdas'] and lote['cant_celdas'] > 0:
                    porcentaje = (lote['cant_celdas'] / lote['cant_traslarve']) * 100
                    st.markdown(f"<p style='padding-top: 25px; margin:0;'><b>Éxito:</b> {porcentaje:.1f}% ({lote['cant_celdas']}/{lote['cant_traslarve']})</p>", unsafe_allow_html=True)
                else:
                    st.markdown("<p style='padding-top: 25px; margin:0; color: #666;'><i>Sin celdas registradas</i></p>", unsafe_allow_html=True)
                    
            with cols[2]:
                st.markdown("<p style='margin:0; font-size:10px;'>&nbsp;</p>", unsafe_allow_html=True)
                if st.button("🗑️ Eliminar", key=f"del_{idx}", help="Eliminar este lote"):
                    st.session_state.lotes.pop(idx)
                    guardar_lotes(st.session_state.lotes)
                    st.rerun()
                    
            st.markdown("<br>", unsafe_allow_html=True)

# CALENDARIO SIEMPRE VISIBLE
st.markdown("---")
st.subheader("📅 Calendario Apícola")

# Siempre incluir al menos el mes actual para que el calendario nunca esté oculto
hoy = datetime.today()
meses_anios = {(hoy.year, hoy.month)}

for lote in st.session_state.lotes:
    for fecha in lote["cronograma"].values():
        meses_anios.add((fecha.year, fecha.month))

meses_ordenados = sorted(list(meses_anios))
nombres_meses_es = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

for anio_actual, mes_actual in meses_ordenados:
    cal = calendar.monthcalendar(anio_actual, mes_actual)
    nombre_mes = nombres_meses_es[mes_actual]
    
    html_table = f"<h4 style='text-align: center; margin-top: 20px;'>{nombre_mes} {anio_actual}</h4>"
    html_table += "<table style='width:100%; border-collapse: collapse; text-align: center; font-size: 11px; background-color: #ffffff;'>"
    html_table += "<tr style='background-color: #262730; color: #ffffff;'><th style='padding:8px;'>Lu</th><th style='padding:8px;'>Ma</th><th style='padding:8px;'>Mi</th><th style='padding:8px;'>Ju</th><th style='padding:8px;'>Vi</th><th style='padding:8px;'>Sá</th><th style='padding:8px;'>Do</th></tr>"
    
    for semana in cal:
        html_table += "<tr>"
        for dia in semana:
            if dia == 0:
                html_table += "<td style='padding: 8px; border: 1px solid #e0e0e0; background-color: #f9f9f9;'></td>"
            else:
                eventos_celda = []
                for lote in st.session_state.lotes:
                    for tarea, fecha in lote['cronograma'].items():
                        if fecha.day == dia and fecha.month == mes_actual and fecha.year == anio_actual:
                            tipo_corto = tarea.split(" ")[0]
                            if tipo_corto == "Hacer":
                                tipo_corto = "Núcleos"
                            elif tipo_corto == "Insertar":
                                tipo_corto = "Celdas"
                            elif tipo_corto == "Revisar":
                                tipo_corto = "Postura"
                            eventos_celda.append(f"<div style='background-color: {lote['color']}; padding: 3px 4px; margin: 2px 0; border-radius: 4px; color: #000; text-align: left; font-size: 10px; border-left: 3px solid #333;'><b>{lote['nombre']}</b>: {tipo_corto}</div>")
                
                contenido_dia = f"<div style='font-weight: bold; margin-bottom: 4px; color: #333;'>{dia}</div>"
                if eventos_celda:
                    contenido_dia += "".join(eventos_celda)
                    
                html_table += f"<td style='padding: 6px; border: 1px solid #dcdcdc; vertical-align: top; height: 85px; width: 14.28%;'>{contenido_dia}</td>"
        html_table += "</tr>"
    html_table += "</table>"
    
    st.markdown(html_table, unsafe_allow_html=True)

# Opción de respaldo de seguridad (por si Streamlit reinicia el contenedor tras inactividad)
st.markdown("---")
with st.expander("💾 Copia de Seguridad (Exportar / Importar datos)"):
    st.caption("Guarda una copia en tu celular si vas a dejar de usar la app por varios días, ya que el servidor gratuito puede reiniciarse.")
    if st.session_state.lotes:
        with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
            st.download_button(
                label="⬇️ Descargar respaldo (.json)",
                data=f.read(),
                file_name="respaldo_reinas.json",
                mime="application/json"
            )
    archivo_subido = st.file_uploader("⬆️ Restaurar desde archivo (.json)", type=["json"])
    if archivo_subido is not None:
        contenido = archivo_subido.read().decode("utf-8")
        with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
            f.write(contenido)
        st.session_state.lotes = cargar_lotes()
        st.success("✅ ¡Datos restaurados correctamente!")
        st.rerun()

