from cryptography.fernet import Fernet
from src.config import settings

_cipher: Fernet | None = None


def _get_cipher() -> Fernet:
    global _cipher
    if _cipher is None:
        key = settings.PHI_ENCRYPTION_KEY.encode() if settings.PHI_ENCRYPTION_KEY else Fernet.generate_key()
        _cipher = Fernet(key)
    return _cipher


def encrypt_phi(plaintext: str) -> str:
    return _get_cipher().encrypt(plaintext.encode()).decode()


def decrypt_phi(ciphertext: str) -> str:
    return _get_cipher().decrypt(ciphertext.encode()).decode()
