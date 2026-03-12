import streamlit as st
import sqlite3
import pandas as pd
from garmin_sync import sincronizar_actividades
from db_manager import DB_PATH

# Configuración de la página
st.set_page_config(page_title="Proyecto Athlete", page_icon="🏃")

# Menú de navegación en la barra lateral
menu = st.sidebar.radio("Navegación", ["Dashboard", "Sincronizar Garmin", "Diario Fisiológico"])

# Pestaña "Sincronizar Garmin"
if menu == "Sincronizar Garmin":
    st.title("Sincronizar Garmin")
    st.write("Introduce tus credenciales de Garmin para sincronizar tus actividades.")

    with st.form("form_sincronizar"):
        email = st.text_input("Email de Garmin")
        password = st.text_input("Contraseña de Garmin", type="password")
        usuario_id = st.number_input("ID de Usuario", min_value=1, step=1)
        submit = st.form_submit_button("Sincronizar Ahora")

        if submit:
            with st.spinner("Sincronizando con Garmin..."):
                resultado = sincronizar_actividades(email, password, usuario_id)
            if "Error" in resultado:
                st.error(resultado)
            else:
                st.success(resultado)

# Pestaña "Diario Fisiológico"
elif menu == "Diario Fisiológico":
    st.title("Diario Fisiológico")
    st.write("Registra tu estado fisiológico diario.")

    with st.form("form_diario"):
        fase_ciclo = st.selectbox("Fase del Ciclo", ["Folicular", "Lútea", "Ovulatoria", "No Aplica"])
        fatiga = st.slider("Nivel de Fatiga (1-10)", min_value=1, max_value=10, step=1)
        notas = st.text_area("Notas / Molestias / Dolor")
        submit = st.form_submit_button("Guardar")

        if submit:
            try:
                conexion = sqlite3.connect(DB_PATH)
                cursor = conexion.cursor()
                cursor.execute('''
                    INSERT INTO diario_fisiologia (usuario_id, fecha, fase_ciclo, fatiga_subjetiva, dolor_notas)
                    VALUES (?, DATE('now'), ?, ?, ?)
                ''', (1, fase_ciclo, fatiga, notas))  # Cambiar usuario_id según sea necesario
                conexion.commit()
                conexion.close()
                st.success("Registro guardado exitosamente.")
            except sqlite3.Error as e:
                st.error(f"Error al guardar en la base de datos: {e}")

# Pestaña "Dashboard"
elif menu == "Dashboard":
    st.title("Dashboard")
    st.write("Próximamente: Gráficas de Rendimiento e IA.")

    try:
        conexion = sqlite3.connect(DB_PATH)
        query = "SELECT * FROM actividades_garmin"
        df = pd.read_sql_query(query, conexion)
        conexion.close()

        if not df.empty:
            st.dataframe(df)
        else:
            st.warning("No hay datos disponibles en la base de datos.")
    except sqlite3.Error as e:
        st.error(f"Error al conectar con la base de datos: {e}")
