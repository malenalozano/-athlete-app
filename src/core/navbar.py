"""
src/core/navbar.py — Navbar horizontal con dot de color por item activo.
"""

import streamlit as st
from datetime import datetime
from src.core.styles import ACCENT, BORDER, TXT2, TXT3, CARD
from src.db.db_manager import obtener_credenciales_garmin

PAGES = [
    ("pages/01_dashboard.py",  "Dashboard",    "dashboard"),
    ("pages/02_plan.py",       "Plan semanal", "plan"),
    ("pages/03_diario.py",     "Diario",       "diario"),
    ("pages/04_garmin.py",     "Garmin",       "garmin"),
    ("pages/05_ejercicios.py", "Ejercicios",   "ejercicios"),
    ("pages/06_entrenador.py", "Entrenador",   "entrenador"),
]

_NAV = ".main .block-container > div > [data-testid='stVerticalBlock'] > [data-testid='stHorizontalBlock']:first-child"

_CSS = f"""<style>
/* ── Topbar container ── */
{_NAV} {{
    background: {CARD} !important;
    border-bottom: 1px solid {BORDER} !important;
    padding: 0 16px !important;
    margin: 0 -2rem 1.5rem -2rem !important;
    align-items: center !important;
    min-height: 52px !important;
}}
/* Page-link style: no wrapping, consistent height */
{_NAV} [data-testid="stPageLink"] {{
    display: flex !important;
    align-items: center !important;
    height: 52px !important;
}}
{_NAV} [data-testid="stPageLink"] p {{
    font-size: 13px !important;
    color: {TXT2} !important;
    padding: 0 4px !important;
    margin: 0 !important;
    white-space: nowrap !important;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.15s !important;
}}
{_NAV} [data-testid="stPageLink"] p::before {{
    content: '' !important;
    display: inline-block !important;
    width: 6px !important;
    height: 6px !important;
    border-radius: 50% !important;
    background: {TXT3} !important;
    flex-shrink: 0 !important;
}}
{_NAV} [data-testid="stPageLink"]:hover p {{
    color: #c9d1d9 !important;
}}
{_NAV} [data-testid="stPageLink"]:hover p::before {{
    background: #c9d1d9 !important;
}}
</style>"""


def _dot(active: bool) -> str:
    color = ACCENT if active else TXT3
    return (f"<span style='display:inline-block;width:6px;height:6px;border-radius:50%;"
            f"background:{color};margin-right:8px;flex-shrink:0;vertical-align:middle;'></span>")


def render_navbar(pagina_activa: str):
    st.markdown(_CSS, unsafe_allow_html=True)

    auth_user = str(st.session_state.get("auth_user", "")).strip()
    avatar_letter = (auth_user[:1] or "?").upper()

    # Columnas: logo | Dashboard | Plan semanal | Diario | Garmin | Ejercicios | Entrenador | spacer | sync | avatar
    cols = st.columns([1.8, 1.1, 1.6, 0.95, 0.95, 1.3, 1.35, 2.65, 0.5, 0.5])

    with cols[0]:
        st.markdown(
            f"<div style='padding:14px 20px 14px 0;font-size:15px;font-weight:600;"
            f"color:{ACCENT};border-right:1px solid {BORDER};letter-spacing:-0.3px;"
            f"line-height:52px;'>athlete.</div>",
            unsafe_allow_html=True)

    for i, (path, label, key) in enumerate(PAGES):
        with cols[i + 1]:
            active = key == pagina_activa
            if active:
                st.markdown(
                    f"<div style='padding:16px 12px;font-size:13px;color:{ACCENT};"
                    f"border-bottom:2px solid {ACCENT};font-weight:500;"
                    f"display:flex;align-items:center;white-space:nowrap;'>"
                    f"{_dot(True)}{label}</div>",
                    unsafe_allow_html=True)
            else:
                st.page_link(path, label=label)

    # Botón sync — llama a sincronizar_todo_con_sesion si hay sesión activa
    with cols[7]:
        st.markdown("""<style>
        .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-child
        button[kind="secondary"] {
            width:32px !important; height:32px !important; padding:0 !important;
            border-radius:50% !important; border:1px solid #30363d !important;
            background:transparent !important; color:#8b949e !important;
            font-size:15px !important; min-height:0 !important; line-height:1 !important;
            margin-top:10px !important;
        }
        </style>""", unsafe_allow_html=True)
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
                        st.session_state["garmin_last_sync"] = {
                            "ts": ts,
                            "source": "navbar",
                            "result": r,
                        }
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error sync: {e}")

    # Avatar con popover dropdown para logout
    with cols[8]:
        if st.button(
            avatar_letter,
            key="avatar_btn",
            help="Menú de usuario",
            use_container_width=False,
        ):
            st.session_state["navbar_popover_open"] = not st.session_state.get("navbar_popover_open", False)
        
        # CSS para estilizar el botón como avatar
        st.markdown(
            f"""<style>
            .main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-child button[kind="secondary"] {{
                width: 32px !important;
                height: 32px !important;
                padding: 0 !important;
                border-radius: 50% !important;
                font-size: 12px !important;
                font-weight: 700 !important;
                border: 1px solid {ACCENT}50 !important;
                color: {ACCENT} !important;
                background: linear-gradient(135deg, {ACCENT}40, {ACCENT}15) !important;
                min-height: 32px !important;
                line-height: 32px !important;
                margin-top: 10px !important;
            }}
            </style>""",
            unsafe_allow_html=True
        )
    
    # Popover del menú de usuario (rendereado abajo del navbar)
    if st.session_state.get("navbar_popover_open", False):
        # Estilos para el menú mejorado
        st.markdown(f"""<style>
        .user-menu-container {{
            background: linear-gradient(135deg, #0E1117 0%, #0A2E0A 52%, #0E1117 100%);
            border: 1px solid {ACCENT}30;
            border-radius: 12px;
            padding: 20px;
            margin-top: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }}
        .user-menu-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
        }}
        .user-menu-avatar {{
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: linear-gradient(135deg, {ACCENT}, {ACCENT}80);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 20px;
            color: #0E1117;
            box-shadow: 0 4px 12px {ACCENT}40;
        }}
        .user-menu-info {{
            flex: 1;
        }}
        .user-menu-info .nombre {{
            font-weight: 700;
            color: #C9FF00;
            font-size: 15px;
            margin-bottom: 4px;
        }}
        .user-menu-info .objetivo {{
            font-size: 12px;
            color: #8B949E;
        }}
        .perfil-selector {{
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
        }}
        .perfil-btn {{
            flex: 1;
            padding: 12px;
            border: 2px solid {ACCENT}40;
            border-radius: 8px;
            background: transparent;
            color: #8B949E;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            transition: all 0.2s;
            text-align: center;
        }}
        .perfil-btn.activo {{
            border-color: {ACCENT}!important;
            background: {ACCENT}20!important;
            color: {ACCENT}!important;
            box-shadow: 0 0 16px {ACCENT}30;
        }}
        .perfil-btn:hover {{
            border-color: {ACCENT}80;
            color: #C9D1D9;
        }}
        .menu-divider {{
            height: 1px;
            background: {BORDER};
            margin: 12px 0;
        }}
        .menu-action {{
            margin-bottom: 8px;
        }}
        .menu-action button {{
            width: 100%!important;
            font-size: 13px!important;
        }}
        </style>""", unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="user-menu-container">', unsafe_allow_html=True)
            
            # Header con avatar e info del usuario
            _perfiles_list = {"Malena": 1, "Dani": 2}
            _current_uid = st.session_state.get("usuario_id", 1)
            _nombre_actual = next((n for n, i in _perfiles_list.items() if i == _current_uid), "Usuario")
            _avatar = _nombre_actual[:1].upper()
            
            st.markdown(f"""
            <div class="user-menu-header">
                <div class="user-menu-avatar">{_avatar}</div>
                <div class="user-menu-info">
                    <div class="nombre">👤 {_nombre_actual}</div>
                    <div class="objetivo">Perfil activo: <strong>{_nombre_actual}</strong></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Selector de perfil con botones
            _auth_user_to_id = {"malena": 1, "dani": 2, "malenita88": 1, "danielito99": 2}
            _forced = _auth_user_to_id.get(str(st.session_state.get("auth_user", "")).strip().lower())
            
            if not _forced:
                # Selector de perfil mejorado con botones
                st.markdown('<div class="perfil-selector">', unsafe_allow_html=True)
                col_m, col_d = st.columns([1, 1])
                
                with col_m:
                    btn_class = "perfil-btn activo" if _current_uid == 1 else "perfil-btn"
                    if st.button("👩 Malena", key="perfil_malena", use_container_width=True):
                        if _current_uid != 1:
                            st.session_state["usuario_id"] = 1
                            st.session_state.pop("navbar_popover_open", None)
                            for key in ("plan_data", "plan_cursor", "plan_ia", "diario_data", 
                                        "ejercicios_data", "ejercicios_init_users", "gc", "gc_failed", "gc_error"):
                                st.session_state.pop(key, None)
                            st.cache_data.clear()
                            st.rerun()
                
                with col_d:
                    btn_class = "perfil-btn activo" if _current_uid == 2 else "perfil-btn"
                    if st.button("👨 Dani", key="perfil_dani", use_container_width=True):
                        if _current_uid != 2:
                            st.session_state["usuario_id"] = 2
                            st.session_state.pop("navbar_popover_open", None)
                            for key in ("plan_data", "plan_cursor", "plan_ia", "diario_data", 
                                        "ejercicios_data", "ejercicios_init_users", "gc", "gc_failed", "gc_error"):
                                st.session_state.pop(key, None)
                            st.cache_data.clear()
                            st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                # Con auth: opción de cambiar cuenta
                other_name = "Dani" if _current_uid == 1 else "Malena"
                other_uid = 2 if _current_uid == 1 else 1
                st.markdown(f'<div style="text-align:center;padding:12px;color:#8B949E;font-size:12px;">Conectado como <strong>{_nombre_actual}</strong></div>', unsafe_allow_html=True)
            
            st.markdown('<div class="menu-divider"></div>', unsafe_allow_html=True)
            
            # Botones de acción
            st.markdown('<div class="menu-action">', unsafe_allow_html=True)
            if st.button("⚙️ Configuración", use_container_width=True, key="menu_settings"):
                st.info("Configuración disponible pronto.")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="menu-action">', unsafe_allow_html=True)
            if st.button("🚪 Cerrar sesión", use_container_width=True, key="navbar_logout"):
                _cm = st.session_state.get("_cm")
                from src.core.access_control import logout
                logout(_cm)
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
