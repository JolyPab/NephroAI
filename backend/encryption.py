import os
from cryptography.fernet import Fernet
from typing import Optional

_fernet: Optional[Fernet] = None

def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.getenv("FERNET_KEY")
        if not key:
            # For development, generate a temporary key if not set. In production this should be set.
            key = Fernet.generate_key().decode("utf-8")
            print(f"[WARN] FERNET_KEY not set in environment. Using temporary key.")
            os.environ["FERNET_KEY"] = key
        _fernet = Fernet(key.encode("utf-8"))
    return _fernet

def encrypt_file_data(data: bytes) -> bytes:
    """Encrypts binary file data."""
    f = get_fernet()
    return f.encrypt(data)

def decrypt_file_data(data: bytes) -> bytes:
    """Decrypts binary file data, with fallback if not encrypted."""
    try:
        f = get_fernet()
        return f.decrypt(data)
    except Exception:
        return data
