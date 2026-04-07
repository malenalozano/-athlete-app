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
        # Estilos mejorados para el menú
        st.markdown(f"""<style>
        .premium-menu {{
            background: linear-gradient(135deg, #0E1117 0%, #0A2E0A 50%, #0E1117 100%);
            border: 1px solid {ACCENT}25;
            border-radius: 16px;
            padding: 0;
            margin-top: 12px;
            box-shadow: 0 16px 48px rgba(0,0,0,0.4), inset 0 1px 0 {ACCENT}10;
            overflow: hidden;
        }}
        .profile-header {{
            background: linear-gradient(90deg, {ACCENT}15 0%, transparent 100%);
            border-bottom: 1px solid {BORDER};
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .profile-avatar {{
            width: 56px;
            height: 56px;
            border-radius: 12px;
            background: linear-gradient(135deg, {ACCENT}80, {ACCENT}40);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            font-weight: 800;
            color: #0E1117;
            box-shadow: 0 4px 16px {ACCENT}30;
            flex-shrink: 0;
        }}
        .profile-info {{
            flex: 1;
        }}
        .profile-info .current-profile {{
            font-size: 16px;
            font-weight: 700;
            color: {ACCENT};
            margin-bottom: 3px;
            letter-spacing: -0.3px;
        }}
        .profile-info .status {{
            font-size: 12px;
            color: #8B949E;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .profiles-container {{
            padding: 20px;
        }}
        .profile-card {{
            background: rgba(19, 29, 43, 0.6);
            border: 2px solid {BORDER};
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            cursor: pointer;
            transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        .profile-card:hover {{
            border-color: {ACCENT}80;
            background: rgba({ACCENT[1:] if ACCENT.startswith('#') else '201,255,0'}, 0.08);
            transform: translateX(4px);
        }}
        .profile-card.active {{
            border-color: {ACCENT};
            background: linear-gradient(90deg, {ACCENT}15 0%, transparent 100%);
            box-shadow: 0 0 20px {ACCENT}25;
        }}
        .profile-card-avatar {{
            width: 44px;
            height: 44px;
            border-radius: 10px;
            background: linear-gradient(135deg, {ACCENT}60, {ACCENT}30);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            font-weight: 700;
            color: white;
            flex-shrink: 0;
            box-shadow: 0 4px 12px {ACCENT}20;
        }}
        .profile-card-info {{
            flex: 1;
        }}
        .profile-card-name {{
            font-size: 14px;
            font-weight: 700;
            color: #C9FF00;
            margin-bottom: 2px;
        }}
        .profile-card-target {{
            font-size: 11px;
            color: #8B949E;
        }}
        .profile-card-badge {{
            display: inline-block;
            background: {ACCENT}20;
            border: 1px solid {ACCENT}50;
            color: {ACCENT};
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .profile-card.active .profile-card-badge {{
            background: {ACCENT};
            color: #0E1117;
            border-color: {ACCENT};
        }}
        .menu-actions {{
            border-top: 1px solid {BORDER};
            padding: 16px 20px;
            display: flex;
            gap: 12px;
        }}
        .menu-btn {{
            flex: 1;
            padding: 12px 16px;
            border-radius: 10px;
            border: 1px solid {BORDER};
            background: transparent;
            color: #8B949E;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .menu-btn:hover {{
            border-color: {ACCENT};
            color: #C9D1D9;
            background: {ACCENT}08;
        }}
        .menu-btn.logout {{
            border-color: #da3633;
            color: #da3633;
        }}
        .menu-btn.logout:hover {{
            background: rgba(218, 54, 51, 0.1);
        }}
        </style>""", unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="premium-menu">', unsafe_allow_html=True)
            
            # ── Header con perfil actual ──
            _perfiles_list = {"Malena": 1, "Dani": 2}
            _current_uid = st.session_state.get("usuario_id", 1)
            _nombre_actual = next((n for n, i in _perfiles_list.items() if i == _current_uid), "Usuario")
            _avatar = "👩" if _nombre_actual == "Malena" else "👨"
            
            st.markdown(f"""
            <div class="profile-header">
                <div class="profile-avatar">{_avatar}</div>
                <div class="profile-info">
                    <div class="current-profile">{_nombre_actual}</div>
                    <div class="status">
                        <span>●</span>
                        <span>Conectado</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # ── Selector de perfiles con tarjetas ──
            st.markdown('<div class="profiles-container">', unsafe_allow_html=True)
            st.markdown('<div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #484F58; margin-bottom: 12px; font-weight: 700;">Cambiar a</div>', unsafe_allow_html=True)
            
            # Obtener datos de ambos perfiles
            from src.db.db_manager import obtener_perfil
            
            col_p1, col_p2 = st.columns([1, 1])
            
            perfiles_info = []
            for nombre, uid in _perfiles_list.items():
                perfil = obtener_perfil(uid) or {}
                emoji = "👩" if nombre == "Malena" else "👨"
                objetivo = perfil.get("objetivo_tipo", "Maratón").title() if perfil.get("objetivo_tipo") else "Maratón"
                genero = perfil.get('genero', 'Atleta')
                is_active = (uid == _current_uid)
                perfiles_info.append((nombre, uid, emoji, objetivo, genero, is_active))
            
            # Primer perfil (Malena)
            with col_p1:
                nombre, uid, emoji, objetivo, genero, is_active = perfiles_info[0]
                if is_active:
                    st.markdown(f"""
                    <div class="profile-card active">
                        <div class="profile-card-avatar">{emoji}</div>
                        <div class="profile-card-info">
                            <div class="profile-card-name">{nombre}</div>
                            <div class="profile-card-target">{objetivo}</div>
                        </div>
                        <div class="profile-card-badge">✓ ACTUAL</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    if st.button(f"👩 {nombre}\n{objetivo}", key="switch_malena", use_container_width=True):
                        st.session_state["usuario_id"] = uid
                        st.session_state.pop("navbar_popover_open", None)
                        for key in ("plan_data", "plan_cursor", "plan_ia", "diario_data", 
                                    "ejercicios_data", "ejercicios_init_users", "gc", "gc_failed", "gc_error",
                                    "dashboard_last_user", "diario_last_user", "ejercicios_last_user", 
                                    "garmin_last_user", "entrenador_last_user"):
                            st.session_state.pop(key, None)
                        st.cache_data.clear()
                        st.rerun()
            
            # Segundo perfil (Dani)
            with col_p2:
                nombre, uid, emoji, objetivo, genero, is_active = perfiles_info[1]
                if is_active:
                    st.markdown(f"""
                    <div class="profile-card active">
                        <div class="profile-card-avatar">{emoji}</div>
                        <div class="profile-card-info">
                            <div class="profile-card-name">{nombre}</div>
                            <div class="profile-card-target">{objetivo}</div>
                        </div>
                        <div class="profile-card-badge">✓ ACTUAL</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    if st.button(f"👨 {nombre}\n{objetivo}", key="switch_dani", use_container_width=True):
                        st.session_state["usuario_id"] = uid
                        st.session_state.pop("navbar_popover_open", None)
                        for key in ("plan_data", "plan_cursor", "plan_ia", "diario_data", 
                                    "ejercicios_data", "ejercicios_init_users", "gc", "gc_failed", "gc_error",
                                    "dashboard_last_user", "diario_last_user", "ejercicios_last_user", 
                                    "garmin_last_user", "entrenador_last_user"):
                            st.session_state.pop(key, None)
                        st.cache_data.clear()
                        st.rerun()
            
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # ── Botones de acción ──
            st.markdown('<div class="menu-actions">', unsafe_allow_html=True)
            
            col_settings, col_logout = st.columns([1, 1])
            with col_settings:
                if st.button("⚙️ Config", use_container_width=True, key="menu_settings_btn"):
                    st.info("⏳ Configuración disponible pronto.")
                    
            with col_logout:
                if st.button("🚪 Logout", use_container_width=True, key="navbar_logout_btn"):
                    _cm = st.session_state.get("_cm")
                    from src.core.access_control import logout
                    logout(_cm)
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
