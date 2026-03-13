from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()

_LOCAL_KEY_FILE = os.path.join(os.path.dirname(__file__), ".encryption_key")


def _get_secret_key() -> str:
    # 1) Prefer explicit key from env.
    env_key = os.getenv("ENCRYPTION_KEY")
    if env_key:
        return env_key

    # 2) Reuse a local persistent key for development/local usage.
    if os.path.exists(_LOCAL_KEY_FILE):
        with open(_LOCAL_KEY_FILE, "r", encoding="utf-8") as f:
            key = f.read().strip()
            if key:
                return key

    # 3) Create one if it does not exist so app can boot without .env.
    key = Fernet.generate_key().decode()
    with open(_LOCAL_KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key)
    return key


SECRET_KEY = _get_secret_key()
cipher_suite = Fernet(SECRET_KEY.encode())

def encriptar_password(password: str) -> str:
    """Convierte texto plano en código cifrado"""
    return cipher_suite.encrypt(password.encode()).decode()

def desencriptar_password(token: str) -> str:
    """Convierte el código cifrado en texto plano"""
    return cipher_suite.decrypt(token.encode()).decode()
