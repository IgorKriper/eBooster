from __future__ import annotations

import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def verify_wata_signature(*, public_key_pem: str, signature: str, body: bytes) -> bool:
    public_key = serialization.load_pem_public_key(public_key_pem.encode())
    try:
        signature_bytes = base64.b64decode(signature)
    except ValueError:
        return False
    try:
        public_key.verify(signature_bytes, body, padding.PKCS1v15(), hashes.SHA512())
    except InvalidSignature:
        return False
    return True
