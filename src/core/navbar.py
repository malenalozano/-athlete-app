"""
src/core/navbar.py — Navbar inspirada en el diseño Figma (glassmorphism, íconos, glow).
"""

import streamlit as st
from datetime import datetime
from src.core.styles import BORDER
from src.db.db_manager import obtener_credenciales_garmin

# ── Configuración de páginas ──────────────────────────────────────────────────
# (path, label, key, icono, color, bg_active, border_active, glow)
PAGES = [
    ("pages/01_dashboard.py",  "Inicio",     "dashboard",  "🏠", "#C9FF00", "rgba(201,255,0,0.15)",  "rgba(201,255,0,0.7)",  "0 0 16px rgba(201,255,0,0.35)"),
    ("pages/02_plan.py",       "Plan",       "plan",       "📋", "#00D4FF", "rgba(0,212,255,0.15)",  "rgba(0,212,255,0.7)",  "0 0 16px rgba(0,212,255,0.35)"),
    ("pages/03_diario.py",     "Diario",     "diario",     "✏️", "#A855F7", "rgba(168,85,247,0.15)", "rgba(168,85,247,0.7)", "0 0 16px rgba(168,85,247,0.35)"),
    ("pages/04_garmin.py",     "Garmin",     "garmin",     "⌚", "#3B82F6", "rgba(59,130,246,0.15)", "rgba(59,130,246,0.7)", "0 0 16px rgba(59,130,246,0.35)"),
    ("pages/05_ejercicios.py", "Ejercicios", "ejercicios", "💪", "#F97316", "rgba(249,115,22,0.15)", "rgba(249,115,22,0.7)", "0 0 16px rgba(249,115,22,0.35)"),
    ("pages/06_entrenador.py", "Entrenador", "entrenador", "🤖", "#6366F1", "rgba(99,102,241,0.15)", "rgba(99,102,241,0.7)", "0 0 16px rgba(99,102,241,0.35)"),
]

_NAV = (
    ".main .block-container > div > "
    "[data-testid='stVerticalBlock'] > "
    "[data-testid='stHorizontalBlock']:first-child"
)

_CSS = f"""<style>
/* ── Quitar header nativo y ajustar padding ── */
[data-testid="stToolbar"] {{ display: none !important; }}
header {{ display: none !important; }}
.main .block-container {{ padding-top: 0 !important; }}

/* ── Navbar container ── */
{_NAV} {{
    position: sticky !important;
    top: 0 !important;
    z-index: 999 !important;
    background: linear-gradient(180deg, rgba(14,17,23,0.98) 0%, rgba(22,27,34,0.95) 100%) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-bottom: none !important;
    padding: 0 24px !important;
    margin: 0 -4rem 0 -4rem !important;
    align-items: center !important;
    min-height: 64px !important;
    gap: 4px !important;
}}

/* ── Page-link reset ── */
{_NAV} [data-testid="stPageLink"] {{
    display: flex !important;
    align-items: center !important;
    height: 64px !important;
}}
{_NAV} [data-testid="stPageLink"] p {{
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #8B949E !important;
    padding: 7px 10px !important;
    margin: 0 !important;
    border-radius: 10px !important;
    border: 1px solid transparent !important;
    white-space: nowrap !important;
    display: flex !important;
    align-items: center !important;
    gap: 5px !important;
    transition: color 0.2s, background 0.2s !important;
}}
{_NAV} [data-testid="stPageLink"]:hover p {{
    color: #e6edf3 !important;
    background: rgba(255,255,255,0.05) !important;
}}

/* ── Sync + avatar buttons ── */
{_NAV} button[kind="secondary"] {{
    width: 32px !important;
    height: 32px !important;
    padding: 0 !important;
    border-radius: 50% !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    background: transparent !important;
    color: #8b949e !important;
    font-size: 14px !important;
    min-height: 0 !important;
    line-height: 1 !important;
    margin-top: 16px !important;
}}
{_NAV} button[kind="secondary"]:hover {{
    background: rgba(255,255,255,0.06) !important;
    color: white !important;
}}
</style>"""


def _logo_html(auth_user: str) -> str:
    sub = f"{auth_user} &nbsp;·&nbsp; Maratón 2027" if auth_user else "Maratón 2027"
    return (
        "<div style='display:flex;align-items:center;gap:10px;height:64px;"
        "padding-right:20px;border-right:1px solid rgba(255,255,255,0.06);'>"
        "<div style='width:36px;height:36px;border-radius:10px;flex-shrink:0;"
        "display:flex;align-items:center;justify-content:center;font-size:18px;"
        "background:linear-gradient(135deg,#C9FF00 0%,#00D4FF 50%,#A855F7 100%);"
        "box-shadow:0 0 20px rgba(201,255,0,0.4);'>⚡</div>"
        "<div style='line-height:1;'>"
        "<p style='font-size:13px;font-weight:700;margin:0;line-height:1;"
        "background:linear-gradient(90deg,#C9FF00,#00D4FF);"
        "-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>"
        "Proyecto Athlete</p>"
        f"<p style='font-size:10px;color:#8B949E;margin:2px 0 0;line-height:1;'>{sub}</p>"
        "</div></div>"
    )


def _active_item_html(label: str, icon: str, color: str, bg: str, border: str, glow: str) -> str:
    return (
        "<div style='display:flex;align-items:center;height:64px;'>"
        f"<div style='position:relative;display:flex;align-items:center;gap:5px;"
        f"padding:7px 10px;border-radius:10px;background:{bg};border:1px solid {border};"
        f"color:{color};font-size:12px;font-weight:600;white-space:nowrap;"
        f"box-shadow:{glow};'>"
        f"<span style='position:absolute;top:-3px;right:-3px;width:8px;height:8px;"
        f"border-radius:50%;background:{color};border:2px solid #0E1117;'></span>"
        f"<span>{icon}</span><span>{label}</span>"
        "</div></div>"
    )


def _gradient_line_html() -> str:
    return (
        "<div style='height:2px;margin:0 -4rem;"
        "background:linear-gradient(90deg,#C9FF00 0%,#00D4FF 25%,#A855F7 50%,#F97316 75%,#3B82F6 100%);"
        "opacity:0.5;margin-bottom:2rem;'></div>"
    )


def render_navbar(pagina_activa: str):
    st.markdown(_CSS, unsafe_allow_html=True)

    auth_user = str(st.session_state.get("auth_user", "")).strip()
    avatar_letter = (auth_user[:1] or "?").upper()

    # columns: logo | 6 páginas | spacer | sync | avatar
    cols = st.columns([2.4, 1.0, 0.9, 1.0, 0.95, 1.2, 1.3, 2.6, 0.5, 0.5])

    # Logo
    with cols[0]:
        st.markdown(_logo_html(auth_user), unsafe_allow_html=True)

    # Nav items
    for i, (path, label, key, icon, color, bg, border, glow) in enumerate(PAGES):
        with cols[i + 1]:
            if key == pagina_activa:
                st.markdown(_active_item_html(label, icon, color, bg, border, glow), unsafe_allow_html=True)
            else:
                st.page_link(path, label=f"{icon} {label}")

    # Sync button
    with cols[7]:
        if st.button("↻", key="navbar_sync", help="Sincronizar Garmin (últimos 7 días)"):
            gc = st.session_state.get("gc")
            if gc is None:
                from src.garmin.garmin_sync import cargar_sesion_tokens
                usuario_id = st.session_state.get("usuario_id", 1)
                cred = obtener_credenciales_garmin(usuario_id)
                email = cred[0] if cred else None
                gc = cargar_sesion_tokens(email, usuario_id=usuario_id)
                if gc is not None:
                    st.session_state["gc"] = gc
            if gc is None:
                st.warning("Conecta Garmin primero en la página Garmin.")
            else:
                usuario_id = st.session_state.get("usuario_id", 1)
                from src.garmin.garmin_sync import sincronizar_todo_con_sesion
                with st.spinner():
                    try:
                        r = sincronizar_todo_con_sesion(gc, usuario_id, dias=7)
                        ts = datetime.now().strftime("%d/%m %H:%M")
                        st.session_state["navbar_sync_ts"] = ts
                        st.session_state["navbar_sync_r"] = r
                        st.session_state["garmin_last_sync"] = {"ts": ts, "source": "navbar", "result": r}
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        err_str = str(e)
                        err_low = err_str.lower()
                        if any(k in err_low for k in ["401", "authentication", "token", "unauthorized", "expired"]):
                            st.error("🔑 Sesión Garmin expirada. Ve a la página Garmin y reconecta.")
                            from src.db.db_manager import get_db_connection as _gdc
                            try:
                                _c = _gdc()
                                _c.execute("UPDATE usuarios SET garmin_tokens=NULL WHERE id=?", (usuario_id,))
                                _c.close()
                            except Exception:
                                pass
                            st.session_state.pop("gc", None)
                        elif "429" in err_str or "rate" in err_low:
                            st.error("⏳ Garmin bloqueado temporalmente (429). Espera unas horas.")
                        elif any(k in err_low for k in ["timeout", "connection", "network", "ssl"]):
                            st.error("🌐 Error de red al contactar Garmin. Reintenta en unos minutos.")
                        else:
                            st.error(f"❌ Error sync: {err_str[:200]}")

    # Avatar
    with cols[8]:
        st.markdown(
            f"""<style>
            {_NAV} button[kind="secondary"] {{
                border: 1px solid rgba(201,255,0,0.3) !important;
                color: #C9FF00 !important;
                background: linear-gradient(135deg, rgba(201,255,0,0.25), rgba(201,255,0,0.1)) !important;
                font-weight: 700 !important;
            }}
            </style>""",
            unsafe_allow_html=True,
        )
        if st.button(avatar_letter, key="avatar_btn", help="Menú de usuario"):
            st.session_state["navbar_popover_open"] = not st.session_state.get("navbar_popover_open", False)

    # Gradient line below navbar
    st.markdown(_gradient_line_html(), unsafe_allow_html=True)

    # ── Popover menú de usuario ───────────────────────────────────────────────
    if st.session_state.get("navbar_popover_open", False):
        st.markdown(f"""<style>
        .premium-menu {{
            background: linear-gradient(135deg, #0E1117 0%, #0A2E0A 50%, #0E1117 100%);
            border: 1px solid rgba(201,255,0,0.2);
            border-radius: 16px;
            padding: 0;
            margin-top: 4px;
            box-shadow: 0 16px 48px rgba(0,0,0,0.4);
            overflow: hidden;
        }}
        .profile-header {{
            background: linear-gradient(90deg, rgba(201,255,0,0.1) 0%, transparent 100%);
            border-bottom: 1px solid {BORDER};
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .profile-avatar {{
            width: 52px; height: 52px; border-radius: 12px;
            background: linear-gradient(135deg, rgba(201,255,0,0.7), rgba(201,255,0,0.35));
            display: flex; align-items: center; justify-content: center;
            font-size: 26px; font-weight: 800; color: #0E1117;
            box-shadow: 0 4px 16px rgba(201,255,0,0.25); flex-shrink: 0;
        }}
        .profile-info .current-profile {{ font-size: 15px; font-weight: 700; color: #C9FF00; margin-bottom: 2px; }}
        .profile-info .status {{ font-size: 11px; color: #8B949E; }}
        .profiles-container {{ padding: 16px 20px; }}
        .profile-card {{
            background: rgba(19,29,43,0.6); border: 2px solid {BORDER};
            border-radius: 12px; padding: 14px;
            margin-bottom: 10px; display: flex; align-items: center; gap: 12px;
        }}
        .profile-card.active {{
            border-color: #C9FF00;
            background: linear-gradient(90deg, rgba(201,255,0,0.1) 0%, transparent 100%);
        }}
        .profile-card-badge {{
            background: #C9FF00; color: #0E1117;
            padding: 3px 8px; border-radius: 5px;
            font-size: 10px; font-weight: 700; text-transform: uppercase;
        }}
        .menu-actions {{ border-top: 1px solid {BORDER}; padding: 14px 20px; display: flex; gap: 10px; }}
        </style>""", unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="premium-menu">', unsafe_allow_html=True)

            _perfiles_list = {"Malena": 1, "Dani": 2}
            _current_uid = st.session_state.get("usuario_id", 1)
            _nombre_actual = next((n for n, i in _perfiles_list.items() if i == _current_uid), "Usuario")
            _avatar = "👩" if _nombre_actual == "Malena" else "👨"

            st.markdown(f"""
            <div class="profile-header">
                <div class="profile-avatar">{_avatar}</div>
                <div class="profile-info">
                    <div class="current-profile">{_nombre_actual}</div>
                    <div class="status">● Conectado</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="profiles-container">', unsafe_allow_html=True)
            st.markdown('<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#484F58;margin-bottom:10px;font-weight:700;">Cambiar a</div>', unsafe_allow_html=True)

            from src.db.db_manager import obtener_perfil
            col_p1, col_p2 = st.columns([1, 1])

            perfiles_info = []
            for nombre, uid in _perfiles_list.items():
                perfil = obtener_perfil(uid) or {}
                emoji = "👩" if nombre == "Malena" else "👨"
                objetivo = perfil.get("objetivo_tipo", "Maratón").title() if perfil.get("objetivo_tipo") else "Maratón"
                is_active = (uid == _current_uid)
                perfiles_info.append((nombre, uid, emoji, objetivo, is_active))

            with col_p1:
                nombre, uid, emoji, objetivo, is_active = perfiles_info[0]
                if is_active:
                    st.markdown(f"""
                    <div class="profile-card active">
                        <div style="font-size:24px;">{emoji}</div>
                        <div style="flex:1">
                            <div style="font-size:13px;font-weight:700;color:#C9FF00;">{nombre}</div>
                            <div style="font-size:11px;color:#8B949E;">{objetivo}</div>
                        </div>
                        <span class="profile-card-badge">✓ Actual</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    if st.button(f"{emoji} {nombre}", key="switch_malena", use_container_width=True):
                        st.session_state["usuario_id"] = uid
                        st.session_state.pop("navbar_popover_open", None)
                        for k in ("plan_data", "plan_cursor", "plan_ia", "diario_data",
                                  "ejercicios_data", "gc", "gc_failed", "gc_error",
                                  "dashboard_last_user", "diario_last_user"):
                            st.session_state.pop(k, None)
                        st.cache_data.clear()
                        st.rerun()

            with col_p2:
                nombre, uid, emoji, objetivo, is_active = perfiles_info[1]
                if is_active:
                    st.markdown(f"""
                    <div class="profile-card active">
                        <div style="font-size:24px;">{emoji}</div>
                        <div style="flex:1">
                            <div style="font-size:13px;font-weight:700;color:#C9FF00;">{nombre}</div>
                            <div style="font-size:11px;color:#8B949E;">{objetivo}</div>
                        </div>
                        <span class="profile-card-badge">✓ Actual</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    if st.button(f"{emoji} {nombre}", key="switch_dani", use_container_width=True):
                        st.session_state["usuario_id"] = uid
                        st.session_state.pop("navbar_popover_open", None)
                        for k in ("plan_data", "plan_cursor", "plan_ia", "diario_data",
                                  "ejercicios_data", "gc", "gc_failed", "gc_error",
                                  "dashboard_last_user", "diario_last_user"):
                            st.session_state.pop(k, None)
                        st.cache_data.clear()
                        st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="menu-actions">', unsafe_allow_html=True)
            col_s, col_l = st.columns([1, 1])
            with col_s:
                if st.button("⚙️ Config", use_container_width=True, key="menu_settings_btn"):
                    st.info("⏳ Configuración disponible pronto.")
            with col_l:
                if st.button("🚪 Salir", use_container_width=True, key="navbar_logout_btn"):
                    _cm = st.session_state.get("_cm")
                    from src.core.access_control import logout
                    logout(_cm)
            st.markdown('</div></div>', unsafe_allow_html=True)
