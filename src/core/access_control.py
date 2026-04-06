import base64
import hashlib
import hmac
import os
from collections.abc import Mapping

import streamlit as st


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
    users = _get_users_from_secrets()
    return len(users) > 0


def require_auth() -> None:
    if not is_auth_required():
        return

    if st.session_state.get("auth_ok"):
        # Auth OK - navbar.py maneja el UX de logout en el avatar dropdown
        # Este bloque solo valida que el usuario está loggeado
        return

    users = _get_users_from_secrets()
    st.title("Acceso privado")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Usuario")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        stored = users.get((username or "").strip())
        if stored and verify_password(password or "", stored):
            st.session_state["auth_ok"] = True
            st.session_state["auth_user"] = username.strip()
            st.rerun()
        else:
            st.error("Usuario o password incorrectos")

    st.stop()
