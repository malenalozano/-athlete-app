import base64
import hashlib
import hmac
import os
from collections.abc import Mapping
from datetime import datetime, timedelta

import streamlit as st

_COOKIE_NAME = "athlete_auth_user"
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


def _get_users_from_secrets() -> dict:
    users = st.secrets.get("APP_USERS", {})
    if isinstance(users, Mapping):
        return {str(k): str(v) for k, v in users.items() if k and v}
    return {}


def is_auth_required() -> bool:
    return len(_get_users_from_secrets()) > 0


def require_auth(cm=None) -> None:
    """
    cm: CookieManager de extra-streamlit-components (opcional).
        Si se pasa, el login se persiste en cookie 30 días — survives F5/reload.
    """
    if not is_auth_required():
        return

    if st.session_state.get("auth_ok"):
        return

    users = _get_users_from_secrets()

    # ── Intentar auto-login desde cookie ────────────────────────────
    if cm is not None:
        try:
            cookie_user = cm.get(_COOKIE_NAME)
            if cookie_user and str(cookie_user).strip() in users:
                st.session_state["auth_ok"] = True
                st.session_state["auth_user"] = str(cookie_user).strip()
                st.rerun()
        except Exception:
            pass

    # ── Pantalla de login ────────────────────────────────────────────
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0E1117 0%, #0A2E0A 52%, #0E1117 100%);
    }
    .login-center { max-width: 400px; margin: 6vh auto 0; padding: 0 16px; }
    .login-title  { font-size: 2rem; font-weight: 700; color: #fff; margin-bottom: 4px; }
    .login-sub    { color: #8B949E; font-size: 0.9rem; margin-bottom: 24px; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='text-align:center;margin:40px 0 24px;'>", unsafe_allow_html=True)
        st.markdown(
            "<div style='width:64px;height:64px;background:#C9FF00;border-radius:12px;"
            "display:inline-flex;align-items:center;justify-content:center;"
            "box-shadow:0 10px 24px rgba(201,255,0,0.4);margin-bottom:16px;'>"
            "<svg width='32' height='32' viewBox='0 0 24 24' fill='#0E1117'>"
            "<path d='M12 12c2.2 0 4-1.8 4-4s-1.8-4-4-4-4 1.8-4 4 1.8 4 4 4zm0 2c-2.7 0-8 1.3-8 4v2h16v-2c0-2.7-5.3-4-8-4z'/>"
            "</svg></div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='login-title'>Proyecto Athlete</div>", unsafe_allow_html=True)
        st.markdown("<div class='login-sub'>Acceso privado</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Entrar", type="primary", use_container_width=True)

        if submitted:
            stored = users.get((username or "").strip())
            if stored and verify_password(password or "", stored):
                st.session_state["auth_ok"] = True
                st.session_state["auth_user"] = username.strip()
                if cm is not None:
                    try:
                        cm.set(
                            _COOKIE_NAME,
                            username.strip(),
                            expires_at=datetime.now() + timedelta(days=_COOKIE_DAYS),
                        )
                    except Exception:
                        pass
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

    st.stop()


def logout(cm=None) -> None:
    """Limpia sesión y cookie."""
    for key in ("auth_ok", "auth_user", "usuario_id", "gc", "gc_failed", "gc_error"):
        st.session_state.pop(key, None)
    if cm is not None:
        try:
            cm.delete(_COOKIE_NAME)
        except Exception:
            pass
    st.cache_data.clear()
    st.rerun()
