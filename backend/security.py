"""AES encryption utilities for the credential vault (Module 5)."""
import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _key() -> bytes:
    raw = os.environ["VAULT_MASTER_KEY"].encode("utf-8")
    return hashlib.sha256(raw).digest()  # 32 bytes for AES-256


def encrypt_secret(plaintext: str) -> str:
    if plaintext is None or plaintext == "":
        return ""
    aes = AESGCM(_key())
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("utf-8")


def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    try:
        data = base64.b64decode(token.encode("utf-8"))
        nonce, ct = data[:12], data[12:]
        aes = AESGCM(_key())
        return aes.decrypt(nonce, ct, None).decode("utf-8")
    except Exception:
        return ""
