import base64
import hashlib
import hmac
import os
from collections.abc import Mapping
from datetime import datetime, timedelta

import streamlit as st

_COOKIE_NAME = "athlete_auth_token"
_COOKIE_DAYS = 30


def build_password_hash(password: str, *, iterations: int = 200_000) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt_b64}${digest_b64}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algo, iterations_s, salt_b64, digest_b64 = encoded_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(digest_b64.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def _get_app_password() -> str:
    """Obtiene la contraseña maestra de la app desde secrets."""
    return str(st.secrets.get("APP_PASSWORD", "")).strip()


def require_simple_password_auth(cm=None) -> None:
    """
    Autenticación simple: solo contraseña para acceder a la app.
    Una vez autenticado, puede elegir entre Malena (1) y Dani (2) desde el menú.
    """
    app_password = _get_app_password()
    if not app_password:
        # Sin contraseña configurada — acceso libre
        return

    if st.session_state.get("auth_ok"):
        # Ya autenticado
        return

    # ── Intentar auto-login desde cookie ────────────────────────────
    if cm is not None:
        try:
            cookie_token = cm.get(_COOKIE_NAME)
            if cookie_token == "authenticated":
                st.session_state["auth_ok"] = True
                st.rerun()
        except Exception:
            pass

    # ── Pantalla de login con solo contraseña ────────────────────────
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0E1117 0%, #0A2E0A 52%, #0E1117 100%);
        min-height: 100vh;
    }
    .login-center { max-width: 400px; margin: 12vh auto 0; padding: 0 16px; }
    .login-title  { font-size: 2.2rem; font-weight: 800; color: #C9FF00; margin-bottom: 8px; letter-spacing: -0.5px; }
    .login-sub    { color: #8B949E; font-size: 0.95rem; margin-bottom: 32px; line-height: 1.5; }
    .login-form { background: rgba(13, 17, 23, 0.8); border: 1px solid #30363d; border-radius: 12px; padding: 24px; backdrop-filter: blur(10px); }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        # Avatar
        st.markdown(
            "<div style='text-align:center;margin-bottom:24px;'>"
            "<div style='width:72px;height:72px;background:linear-gradient(135deg,#C9FF00,#A3E635);border-radius:16px;"
            "display:inline-flex;align-items:center;justify-content:center;box-shadow:0 12px 32px rgba(201,255,0,0.25);'>"
            "<svg width='40' height='40' viewBox='0 0 24 24' fill='#0E1117' style='font-weight:bold;'>"
            "<path d='M16.5 12c1.93 0 3.5-1.57 3.5-3.5S18.43 5 16.5 5 13 6.57 13 8.5s1.57 3.5 3.5 3.5zm-9 0c1.93 0 3.5-1.57 3.5-3.5S9.43 5 7.5 5 4 6.57 4 8.5 5.57 12 7.5 12zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4zm9 0c-.29 0-.74.02-1.5.15 1.42 1.25 2.5 2.71 2.5 4.35v2h6v-2c0-2.66-5.33-4-7-4.5z'/>"
            "</svg></div>"
            "</div>",
            unsafe_allow_html=True,
        )

        # Títulos
        st.markdown(
            "<div style='text-align:center;'>"
            "<div class='login-title'>🏃 athlete.</div>"
            "<div class='login-sub'>Sistema privado de entrenamiento<br>para Malena y Dani</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        # Formulario
        with st.form("login_password_form", clear_on_submit=False):
            password = st.text_input(
                "🔐 Contraseña de acceso",
                type="password",
                placeholder="Ingresa la contraseña",
                help="Solo personas autorizadas pueden acceder"
            )
            submitted = st.form_submit_button("🔓 Entrar", type="primary", use_container_width=True)

        if submitted:
            if password == app_password:
                st.session_state["auth_ok"] = True
                if cm is not None:
                    try:
                        cm.set(
                            _COOKIE_NAME,
                            "authenticated",
                            expires_at=datetime.now() + timedelta(days=_COOKIE_DAYS),
                        )
                    except Exception:
                        pass
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta. Intenta de nuevo.")

    st.stop()


def logout(cm=None) -> None:
    """Limpia sesión y cookie."""
    for key in ("auth_ok", "usuario_id", "gc", "gc_failed", "gc_error", "auth_user"):
        st.session_state.pop(key, None)
    if cm is not None:
        try:
            cm.delete(_COOKIE_NAME)
        except Exception:
            pass
    st.cache_data.clear()
    st.rerun()


# ── Mantener compatibilidad con sistema antiguo (opcional) ──
def is_auth_required() -> bool:
    return len(_get_app_password()) > 0


def require_auth(cm=None) -> None:
    """Alias para compatibilidad — ahora redirecciona a autenticación simple."""
    require_simple_password_auth(cm)
