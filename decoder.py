from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from config import KEY
import base64


def decrypt_session_id(encrypted_payload: str) -> str:
    data = base64.b64decode(encrypted_payload)
    nonce, encrypted_data = data[:12], data[12:]  # Разделяем nonce и зашифрованные данные

    aesgcm = AESGCM(KEY)
    decrypted_data = aesgcm.decrypt(nonce, encrypted_data, None)
    result = decrypted_data.decode()
    return result
