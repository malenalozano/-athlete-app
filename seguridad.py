from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()

# Intentamos cargar la llave desde el .env
# Si no existe, deberás crear una con Fernet.generate_key()
SECRET_KEY = os.getenv("ENCRYPTION_KEY")

if not SECRET_KEY:
    raise ValueError("❌ No se encontró ENCRYPTION_KEY en el archivo .env")

cipher_suite = Fernet(SECRET_KEY.encode())

def encriptar_password(password: str) -> str:
    """Convierte texto plano en código cifrado"""
    return cipher_suite.encrypt(password.encode()).decode()

def desencriptar_password(token: str) -> str:
    """Convierte el código cifrado en texto plano"""
    return cipher_suite.decrypt(token.encode()).decode()
