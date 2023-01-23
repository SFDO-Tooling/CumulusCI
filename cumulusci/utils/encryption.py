import base64
import os
from typing import Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CBC

BS = 16
backend = default_backend()


def pad(s):
    return s + (BS - len(s) % BS) * b" "


def encrypt_and_b64(config_data: bytes, key: str) -> bytes:
    assert isinstance(config_data, bytes)
    padded = pad(config_data)
    cipher, iv = _get_cipher(key)
    return base64.b64encode(iv + cipher.encryptor().update(padded))


def _get_cipher(key: Union[str, bytes], iv=None):
    if not isinstance(key, bytes):
        key = key.encode()
    if iv is None:
        iv = os.urandom(16)
    cipher = Cipher(AES(key), CBC(iv), backend=backend)
    return cipher, iv
