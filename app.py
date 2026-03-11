import streamlit as st
from atleta_core import calcular_fase_ciclo, ajustar_consejo_nutricional, insertar_usuario, crear_tabla_fuerza, importar_csv_garmin

# Título de la aplicación
st.title("Athlete Performance Tracker")

# Barra lateral para seleccionar el usuario
usuario = st.sidebar.selectbox("Selecciona un usuario", ["Malena", "Dani"])

if usuario == "Malena":
    st.subheader("Objetivo de Malena: Maratón")
    fecha_ultima_regla = st.date_input("Fecha de tu última regla:")
    if st.button("Calcular predicción de Ciclo"):
        if fecha_ultima_regla:
            duracion_ciclo = 28  # Puedes permitir al usuario cambiar esto si es necesario
            fase_ciclo = calcular_fase_ciclo(fecha_ultima_regla, duracion_ciclo)
            st.write(f"Fase del ciclo calculada para Malena: {fase_ciclo}")
            
            # Mostrar consejo nutricional basado en los últimos KM
            st.write("Obteniendo consejo nutricional...")
            importar_csv_garmin("actividad.csv")  # Asegúrate de que el archivo exista
        else:
            st.write("Por favor, selecciona una fecha válida.")
elif usuario == "Dani":
    st.subheader("Objetivo de Dani: 100km")
    levantamientos = st.text_input("Anota tus levantamientos de pesas:")
    if levantamientos:
        if st.button("Guardar levantamientos"):
            st.write(f"Levantamientos registrados: {levantamientos}")
            
            # Conectar con la tabla de fuerza
            crear_tabla_fuerza()
            insertar_usuario("Dani", "Hombre", "Ultra 100km")
