import streamlit as st
from datetime import datetime, timedelta
import calendar

# Configuración de la página web
st.set_page_config(page_title="Gestor Apícola de Reinas", page_icon="🐝", layout="centered")

st.title("🐝 Gestor de Crianza de Reinas")
st.write("Calcula automáticamente el cronograma de traslarve y visualízalo en el calendario de la app con colores únicos por lote.")

# Inicializar memoria para guardar los lotes en la sesión web
if "lotes" not in st.session_state:
    st.session_state.lotes = []

# Paleta de colores para diferenciar cada lote automáticamente
colores_disponibles = ["#ff9999", "#66b3ff", "#99ff99", "#ffcc99", "#c299ff", "#ff99ff", "#ffe666"]

# Formulario para ingresar un nuevo lote
with st.form("form_lote", clear_on_submit=True):
    st.subheader("➕ Registrar Nuevo Lote")
    nombre_lote = st.text_input("Nombre o Identificador del Lote", placeholder="Ej: Lote A")
    fecha_traslarve = st.date_input("Fecha de Traslarve", value=datetime.today())
    submitted = st.form_submit_button("Agregar y Guardar en el Calendario")

if submitted:
    if not nombre_lote.strip():
        st.warning("⚠️ Por favor escribe un nombre para el lote.")
    else:
        # Calcular fechas clave
        t = datetime.combine(fecha_traslarve, datetime.min.time())
        cronograma = {
            "Traslarve (Día 0)": t,
            "Hacer núcleos (Día 7)": t + timedelta(days=7),
            "Insertar celdas (Día 9)": t + timedelta(days=9),
            "Revisar postura (Día 21)": t + timedelta(days=21)
        }
        
        # Asignar color automático según el orden
        color = colores_disponibles[len(st.session_state.lotes) % len(colores_disponibles)]
        
        st.session_state.lotes.append({
            "nombre": nombre_lote,
            "traslarve": t,
            "cronograma": cronograma,
            "color": color
        })
        st.success(f"¡Lote '{nombre_lote}' guardado en el calendario!")

# Si hay lotes guardados, mostramos la leyenda y el calendario
if st.session_state.lotes:
    st.markdown("---")
    st.subheader("🎨 Lotes Guardados (Leyenda de Colores)")
    
    for lote in st.session_state.lotes:
        st.markdown(
            f"<div style='background-color: {lote['color']}; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; color: #000;'>"
            f"<b>Lote: {lote['nombre']}</b> (Traslarve: {lote['traslarve'].strftime('%d/%m/%Y')})"
            f"</div>", 
            unsafe_allow_html=True
        )

    if st.button("🗑️ Limpiar todos los lotes"):
        st.session_state.lotes = []
        st.rerun()

    st.markdown("---")
    st.subheader("📅 Calendario de la Aplicación")
    
    # Detectar todos los meses y años que tienen eventos para mostrarlos todos
    meses_anios = set()
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
        html_table += "<table style='width:100%; border-collapse: collapse; text-align: center; font-size: 11px;'>"
        html_table += "<tr style='background-color: #f2f2f2; color: #000;'><th>Lu</th><th>Ma</th><th>Mi</th><th>Ju</th><th>Vi</th><th>Sá</th><th>Do</th></tr>"
        
        for semana in cal:
            html_table += "<tr>"
            for dia in semana:
                if dia == 0:
                    html_table += "<td style='padding: 6px; border: 1px solid #ddd;'></td>"
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
                                eventos_celda.append(f"<div style='background-color: {lote['color']}; padding: 2px; margin: 2px; border-radius: 3px; color: black;'><b>{lote['nombre']}</b>: {tipo_corto}</div>")
                    
                    contenido_dia = f"<b>{dia}</b>"
                    if eventos_celda:
                        contenido_dia += "".join(eventos_celda)
                        
                    html_table += f"<td style='padding: 4px; border: 1px solid #ddd; vertical-align: top; height: 75px;'>{contenido_dia}</td>"
            html_table += "</tr>"
        html_table += "</table>"
        
        st.markdown(html_table, unsafe_allow_html=True)
