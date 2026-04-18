import base64
import hashlib
import hmac
import os
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
    try:
        if "APP_PASSWORD" in st.secrets:
            return str(st.secrets.get("APP_PASSWORD", "")).strip()
    except Exception:
        pass
    return str(os.getenv("APP_PASSWORD", "")).strip()


def _get_cookie_secret() -> str:
    """Secret para firmar la cookie persistente de autenticación."""
    try:
        if "AUTH_COOKIE_SECRET" in st.secrets:
            secret = str(st.secrets.get("AUTH_COOKIE_SECRET", "")).strip()
            if secret:
                return secret
    except Exception:
        pass

    env_secret = str(os.getenv("AUTH_COOKIE_SECRET", "")).strip()
    if env_secret:
        return env_secret

    # Fallback: usable without extra config, but less ideal than AUTH_COOKIE_SECRET.
    return _get_app_password()


def _build_auth_cookie_token() -> str | None:
    """Crea token firmado con expiración para recordar dispositivo."""
    secret = _get_cookie_secret()
    if not secret:
        return None

    expires = int((datetime.utcnow() + timedelta(days=_COOKIE_DAYS)).timestamp())
    payload = f"v1:{expires}"
    sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def _verify_auth_cookie_token(token: str | None) -> bool:
    """Valida formato, firma y expiración del token de cookie."""
    if not token or not isinstance(token, str):
        return False

    parts = token.split(":")
    if len(parts) != 3:
        return False
    version, exp_s, sig = parts
    if version != "v1":
        return False

    try:
        expires = int(exp_s)
    except ValueError:
        return False

    if int(datetime.utcnow().timestamp()) >= expires:
        return False

    secret = _get_cookie_secret()
    if not secret:
        return False

    payload = f"v1:{exp_s}"
    expected_sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_sig, sig)


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
            if cookie_token == "authenticated" or _verify_auth_cookie_token(cookie_token):
                st.session_state["auth_ok"] = True
                st.rerun()
        except Exception:
            pass

    # ── Pantalla de login: primer elemento visible = campo contraseña ──────
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: #0e1117;
        min-height: 100vh;
    }
    </style>
    """, unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 1.3, 1])
    with col_center:
        with st.form("login_password_form", clear_on_submit=False):
            password = st.text_input(
                "Contraseña",
                type="password",
                placeholder="Introduce la contraseña",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Entrar", type="primary", use_container_width=True)

        if submitted:
            if password == app_password:
                st.session_state["auth_ok"] = True
                if cm is not None:
                    try:
                        cookie_token = _build_auth_cookie_token() or "authenticated"
                        cm.set(
                            _COOKIE_NAME,
                            cookie_token,
                            expires_at=datetime.now() + timedelta(days=_COOKIE_DAYS),
                        )
                    except Exception:
                        pass
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")

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
