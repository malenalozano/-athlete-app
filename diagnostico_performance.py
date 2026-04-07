#!/usr/bin/env python3
"""
Diagnóstico de performance - Streamlit Cloud
Script para identificar cuellos de botella
"""

import streamlit as st
import time
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(page_title="Diagnóstico Performance", page_icon="⚙️", layout="wide")

st.title("⚙️ Diagnóstico de Performance")

col1, col2 = st.columns(2)

# Test 1: Tiempo de importación
with col1:
    st.subheader("1️⃣ Importaciones")
    if st.button("Test importaciones"):
        with st.spinner("Cargando..."):
            times = {}
            
            # Test: db_manager
            s = time.time()
            from src.db.db_manager import get_db_connection
            times["db_manager"] = time.time() - s
            
            # Test: dashboard_data
            s = time.time()
            from src.core.dashboard_data import resumen_semana_con_delta
            times["dashboard_data"] = time.time() - s
            
            # Test: garmin_sync
            s = time.time()
            from src.garmin.garmin_sync import sincronizar_todo_con_sesion
            times["garmin_sync"] = time.time() - s
            
            # Test: plan.motor
            s = time.time()
            from src.plan.motor import generar_plan_semana
            times["plan.motor"] = time.time() - s
            
        for mod, t in sorted(times.items(), key=lambda x: -x[1]):
            col = st.columns([3, 1])[1]
            col.metric(mod, f"{t:.2f}s")

# Test 2: Queries SQL
with col2:
    st.subheader("2️⃣ Queries SQL")
    if st.button("Test queries (usuario_id=1)"):
        with st.spinner("Ejecutando queries..."):
            times = {}
            
            # Test: actividades_garmin
            s = time.time()
            from src.db.db_manager import get_db_connection
            import pandas as pd
            conn = get_db_connection()
            df = pd.read_sql_query(
                "SELECT * FROM actividades_garmin WHERE usuario_id=1 ORDER BY fecha DESC LIMIT 200",
                conn
            )
            times["actividades_garmin (200 rows)"] = time.time() - s
            
            # Test: datos_sueno
            s = time.time()
            df = pd.read_sql_query(
                "SELECT * FROM datos_sueno WHERE usuario_id=1 ORDER BY fecha DESC LIMIT 30",
                conn
            )
            times["datos_sueno (30 rows)"] = time.time() - s
            
            # Test: sesiones_fuerza + ejercicios
            s = time.time()
            df = pd.read_sql_query(
                """SELECT s.*, e.* FROM sesiones_fuerza s 
                   LEFT JOIN ejercicios_fuerza e ON e.sesion_id=s.id
                   WHERE s.usuario_id=1 ORDER BY s.fecha DESC LIMIT 50""",
                conn
            )
            times["sesiones_fuerza+ejercicios (50 join)"] = time.time() - s
            
            conn.close()
        
        for query, t in sorted(times.items(), key=lambda x: -x[1]):
            col = st.columns([3, 1])[1]
            col.metric(query, f"{t:.2f}s")

st.divider()

st.subheader("3️⃣ Cache Status")
col_cache1, col_cache2 = st.columns(2)

with col_cache1:
    if st.button("Limpiar caché"):
        st.cache_data.clear()
        st.success("✅ Caché limpiado")

with col_cache2:
    if st.button("Info de caché"):
        st.info(f"Cache decorator summary info will appear here once cache is used")

st.divider()

st.subheader("4️⃣ Memory & Environment")
try:
    import psutil
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    st.metric("Memoria usada (app)", f"{memory_mb:.1f} MB")
except:
    st.warning("psutil no disponible")

st.metric("Python version", sys.version.split()[0])
st.metric("Streamlit version", st.__version__)

st.divider()

st.subheader("5️⃣ Database Indices Check")
if st.button("Verificar índices"):
    with st.spinner("Leyendo..."):
        conn = get_db_connection()
        indices = conn.execute(
            "SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY tbl_name"
        ).fetchall()
        
        st.write(f"Total índices: {len(indices)}")
        
        df_indices = pd.DataFrame(indices, columns=["Índice", "Tabla"])
        st.dataframe(df_indices, use_container_width=True)
        conn.close()

st.divider()

st.subheader("6️⃣ Network Test (Garmin)")
if st.button("Test conexión Garmin"):
    with st.spinner("Conectando con Garmin..."):
        try:
            from garminconnect import Garmin
            s = time.time()
            # Solo creamos el objeto, no hacemos login
            gc = Garmin()
            t = time.time() - s
            st.success(f"✅ Garmin client creado en {t:.2f}s")
        except Exception as e:
            st.error(f"❌ Error: {e}")
