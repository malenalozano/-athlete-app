import streamlit as st
import pandas as pd
import plotly.express as px
import os
from db_manager import get_db_connection
from garmin_sync import sincronizar_actividades

# Intentamos importar la IA, si falla no rompe el programa entero
try:
    from ai_coach import obtener_consejo
except ImportError:
    obtener_consejo = None

# Configuración de la página
st.set_page_config(page_title="Proyecto Athlete", page_icon="🏃‍♀️", layout="wide")

# Menú lateral
st.sidebar.title("Navegación")
menu = st.sidebar.radio("Ir a:", ["Dashboard", "Sincronizar Garmin", "Diario Fisiológico", "Consultorio Virtual", "🏋️‍♀️ Diario de Fuerza"])

# ==========================================
# PESTAÑA 1: DASHBOARD
# ==========================================
if menu == "Dashboard":
    st.title("📊 Dashboard de Rendimiento")
    conn = get_db_connection()
    try:
        df_actividades = pd.read_sql_query("SELECT * FROM actividades_garmin", conn)
        df_fisio = pd.read_sql_query("SELECT * FROM diario_fisiologia", conn)
    except:
        df_actividades = pd.DataFrame()
        df_fisio = pd.DataFrame()
    conn.close()

    if df_actividades.empty:
        st.warning("No hay actividades sincronizadas. Ve a la pestaña 'Sincronizar Garmin'.")
    else:
        # Preparar datos
        df_actividades['fecha_dt'] = pd.to_datetime(df_actividades['fecha']).dt.tz_localize(None)
        df_actividades = df_actividades.sort_values('fecha_dt')
        df_actividades['distancia_km'] = df_actividades['distancia_m'] / 1000

        # KPIs (Métricas principales)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Actividades", len(df_actividades))
        col2.metric("Distancia Total (km)", f"{df_actividades['distancia_km'].sum():.2f}")
        col3.metric("FC Media Histórica", f"{df_actividades['fc_media'].mean():.0f}" if pd.notnull(df_actividades['fc_media'].mean()) else "N/A")

        # Gráficas
        st.plotly_chart(px.line(df_actividades, x='fecha_dt', y='fc_media', markers=True, title="Evolución de Frecuencia Cardíaca"), use_container_width=True)
        st.plotly_chart(px.bar(df_actividades, x='fecha_dt', y='distancia_km', title="Evolución de Distancia (km)"), use_container_width=True)

        # Insights Científicos
        st.subheader("🧬 Fisiología y Rendimiento")
        if not df_fisio.empty:
            ultima_fase = df_fisio.iloc[-1]['fase_ciclo']
            if ultima_fase == "Fase Lútea":
                st.info("💡 **Insight Científico (Dra. Stacy Sims):** Estás en Fase Lútea. Tu temperatura basal y progesterona están elevadas, lo que puede aumentar tus pulsaciones medias y la sensación de fatiga. Prioriza carbohidratos.")
            elif ultima_fase == "Fase Folicular":
                st.success("💡 **Insight Científico:** Fase Folicular. Tu cuerpo está en estado óptimo para alta intensidad. ¡Aprovecha para entrenos clave hacia tu Sub 5:00!")
        else:
            st.info("Añade datos en el 'Diario Fisiológico' para ver correlaciones con tus pulsaciones.")

# ==========================================
# PESTAÑA 2: SINCRONIZAR GARMIN
# ==========================================
elif menu == "Sincronizar Garmin":
    st.title("🔄 Sincronizar Garmin")
    with st.form("garmin_form"):
        email = st.text_input("Email de Garmin")
        password = st.text_input("Contraseña", type="password")
        user_id = st.number_input("ID de Usuario", min_value=1, value=1)
        num_actividades = st.number_input("¿Cuántas actividades quieres recuperar?", min_value=1, max_value=100, value=20)
        submit = st.form_submit_button("Sincronizar Ahora")
        
    if submit:
        with st.spinner("Sincronizando con Garmin..."):
            resultado = sincronizar_actividades(email, password, int(user_id), int(num_actividades))
            if "Error" in resultado:
                st.error(resultado)
            else:
                st.success(resultado)

# ==========================================
# PESTAÑA 3: DIARIO FISIOLÓGICO
# ==========================================
elif menu == "Diario Fisiológico":
    st.title("📓 Diario Fisiológico")
    with st.form("fisio_form"):
        fecha = st.date_input("Fecha")
        fase = st.selectbox("Fase del Ciclo", ["Fase Folicular", "Fase Ovulatoria", "Fase Lútea", "No Aplica"])
        fatiga = st.slider("Nivel de Fatiga (1-10)", 1, 10, 5)
        notas = st.text_area("Notas / Molestias / Dolor")
        submit_fisio = st.form_submit_button("Guardar Registro")
        
    if submit_fisio:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO diario_fisiologia (usuario_id, fecha, fase_ciclo, fatiga_subjetiva, dolor_notas) VALUES (?, ?, ?, ?, ?)",
                       (1, str(fecha), fase, fatiga, notas))
        conn.commit()
        conn.close()
        st.success("Registro guardado correctamente.")

# ==========================================
# PESTAÑA 4: CONSULTORIO VIRTUAL (IA)
# ==========================================
elif menu == "Consultorio Virtual":
    st.title("🧠 Consultorio Virtual (IA)")
    if obtener_consejo is None:
        st.error("Error: No se ha podido cargar ai_coach.py. Revisa que el archivo exista y esté correcto.")
    else:
        # Extraer contexto para la IA
        conn = get_db_connection()
        try:
            df_actividades = pd.read_sql_query("SELECT fecha, tipo_deporte, distancia_m, ritmo_medio, fc_media FROM actividades_garmin ORDER BY fecha DESC LIMIT 3", conn)
            df_fisio = pd.read_sql_query("SELECT fecha, fase_ciclo, fatiga_subjetiva, dolor_notas FROM diario_fisiologia ORDER BY fecha DESC LIMIT 1", conn)
            contexto = f"Últimas actividades: {df_actividades.to_dict('records')}. Estado fisiológico: {df_fisio.to_dict('records')}."
        except:
            contexto = "Aún no hay datos suficientes registrados."
        conn.close()

        # Interfaz de Chat
        if "mensajes" not in st.session_state:
            st.session_state.mensajes = []

        # Mostrar historial de mensajes
        for msg in st.session_state.mensajes:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Input del usuario
        duda = st.chat_input("Escribe tu duda (ej. ¿Cómo ves mi carga de entrenamiento en esta fase de mi ciclo?)...")
        if duda:
            # Mostrar lo que escribió el usuario
            with st.chat_message("user"):
                st.markdown(duda)
            st.session_state.mensajes.append({"role": "user", "content": duda})
            
            # Mostrar la respuesta de la IA
            with st.chat_message("assistant"):
                with st.spinner("Analizando tus datos biométricos..."):
                    try:
                        # Ojo: pasamos duda y contexto. Si tu ai_coach pide más parámetros, avisame.
                        respuesta = obtener_consejo(duda, contexto) 
                        st.markdown(respuesta)
                        st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
                    except Exception as e:
                        st.error(f"Error al procesar la respuesta: {e}")
elif menu == "🏋️‍♀️ Diario de Fuerza":
    st.title("🏋️‍♀️ Diario de Fuerza")

    # Sección de Entrada
    st.subheader("Registrar Entrenamiento de Fuerza")
    nota_fuerza = st.text_area("Escribe o pega tu nota de entrenamiento:")
    if st.button("Procesar con IA"):
        if not nota_fuerza.strip():
            st.error("Por favor, ingresa una nota de entrenamiento.")
        else:
            with st.spinner("Procesando con IA..."):
                try:
                    ejercicios = procesar_nota_fuerza(nota_fuerza)
                    st.success("Nota procesada correctamente. Revisa los resultados:")
                    st.write(ejercicios)

                    if st.button("Confirmar y Guardar en Nube"):
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        for ejercicio in ejercicios:
                            cursor.execute('''
                                INSERT INTO entrenamientos_fuerza (fecha, ejercicio, peso, series, repeticiones, grupo_muscular, notas)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (st.date_input("Fecha"), ejercicio['ejercicio'], ejercicio['peso'], ejercicio['series'], ejercicio['repeticiones'], ejercicio['grupo_muscular'], nota_fuerza))
                        conn.commit()
                        conn.close()
                        st.success("Entrenamiento guardado correctamente.")
                except Exception as e:
                    st.error(f"Error al procesar la nota: {e}")

    # Sección Historial
    st.subheader("Historial de Entrenamientos de Fuerza")
    conn = get_db_connection()
    try:
        df_fuerza = pd.read_sql_query("SELECT * FROM entrenamientos_fuerza ORDER BY fecha DESC", conn)
        st.dataframe(df_fuerza)
    except Exception as e:
        st.error(f"Error al cargar el historial: {e}")
    finally:
        conn.close()
