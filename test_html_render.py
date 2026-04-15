import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Test HTML", layout="wide")

# Test the HTML rendering
fase_nombre = "Preparación General"
dias_left = 157

html_content = f"""
<div style="
  position:relative;
  border-radius:16px;
  padding:2rem;
  overflow:hidden;
  background:linear-gradient(135deg,rgba(201,255,0,0.08) 0%,rgba(0,212,255,0.06) 40%,rgba(168,85,247,0.08) 100%);
  border:1px solid rgba(201,255,0,0.2);
  box-shadow:0 0 60px rgba(201,255,0,0.05),0 0 100px rgba(0,212,255,0.04);
  margin-bottom:0.75rem;
">
  <div style="position:relative;display:flex;align-items:flex-start;justify-content:space-between;gap:1.5rem;flex-wrap:wrap;">
    <div>
      <h1 style="font-size:2.25rem;font-weight:800;color:white;margin:0 0 0.5rem;line-height:1.2;">
        Buenos días, <span style="background:linear-gradient(90deg,#C9FF00,#00D4FF);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">Dani</span> 👋
      </h1>
      <p style="color:#8B949E;font-size:0.875rem;margin:0 0 1rem;">Miércoles 15 de abril de 2026</p>
      <div style="display:flex;flex-wrap:wrap;gap:0.5rem;align-items:center;">
        <span style="background:rgba(59,130,246,0.2);color:#93c5fd;border:1px solid rgba(59,130,246,0.3);border-radius:9999px;padding:4px 12px;font-size:0.75rem;font-weight:600;">🗓 Fase: {fase_nombre}</span>
      </div>
    </div>
    <div style="border-radius:16px;padding:1.25rem 2rem;text-align:center;flex-shrink:0;background:linear-gradient(135deg,rgba(0,212,255,0.12),rgba(59,130,246,0.1));border:1px solid rgba(0,212,255,0.3);box-shadow:0 0 24px rgba(0,212,255,0.15);">
      <p style="font-size:0.65rem;color:#8B949E;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 0.25rem;">Objetivo principal</p>
      <p style="font-size:1rem;font-weight:800;color:white;margin:0 0 0.25rem;">Valencia Marathon</p>
      <p style="font-size:1.875rem;font-weight:900;margin:0.25rem 0 0;background:linear-gradient(90deg,#00D4FF,#C9FF00);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">{dias_left} días</p>
      <p style="font-size:0.65rem;color:#8B949E;margin:0.25rem 0 0;">19 Sep 2026 · 22 semanas</p>
    </div>
  </div>
</div>
"""

st.markdown("### Test HTML Rendering")
st.markdown(html_content, unsafe_allow_html=True)

st.markdown("### Test Alternative (without gradient)")
alt_html = """
<div style="background:blue;padding:20px;color:white;">
<h2>Simple Test</h2>
<p>Fase: Preparación General</p>
</div>
"""
st.markdown(alt_html, unsafe_allow_html=True)
