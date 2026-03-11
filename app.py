import streamlit as st

# Título de la aplicación
st.title("Athlete Performance Tracker")

# Barra lateral para seleccionar el usuario
usuario = st.sidebar.selectbox("Selecciona un usuario", ["Malena", "Dani"])

if usuario == "Malena":
    st.subheader("Objetivo de Malena: Maratón")
    if st.button("Calcular predicción de Ciclo"):
        st.write("Predicción de ciclo calculada para Malena.")
elif usuario == "Dani":
    st.subheader("Objetivo de Dani: 100km")
    levantamientos = st.text_input("Anota tus levantamientos de pesas:")
    if levantamientos:
        st.write(f"Levantamientos registrados: {levantamientos}")
