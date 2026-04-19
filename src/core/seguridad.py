from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()

_LOCAL_KEY_FILE = os.path.join(os.path.dirname(__file__), ".encryption_key")


def _get_secret_key() -> str:
    # 1) Prefer explicit key from env var (set in Streamlit Cloud secrets or .env).
    env_key = os.getenv("ENCRYPTION_KEY")
    if env_key:
        return env_key

    # 2) Try st.secrets (Streamlit Cloud — key stored in secrets.toml).
    try:
        import streamlit as st
        secrets_key = st.secrets.get("ENCRYPTION_KEY")
        if secrets_key:
            return str(secrets_key).strip()
    except Exception:
        pass

    # 3) Reuse a local persistent key file (development only).
    if os.path.exists(_LOCAL_KEY_FILE):
        with open(_LOCAL_KEY_FILE, "r", encoding="utf-8") as f:
            key = f.read().strip()
            if key:
                return key

    # 4) Generate and save a new key if nothing else exists.
    key = Fernet.generate_key().decode()
    try:
        with open(_LOCAL_KEY_FILE, "w", encoding="utf-8") as f:
            f.write(key)
    except Exception:
        pass
    return key


SECRET_KEY = _get_secret_key()
cipher_suite = Fernet(SECRET_KEY.encode())

def encriptar_password(password: str) -> str:
    """Convierte texto plano en código cifrado"""
    return cipher_suite.encrypt(password.encode()).decode()

def desencriptar_password(token: str) -> str:
    """Convierte el código cifrado en texto plano"""
    return cipher_suite.decrypt(token.encode()).decode()
