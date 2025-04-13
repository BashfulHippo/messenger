# security.py
"""Password hashing utilities for secure credential storage."""

import hashlib
import os

# try to use bcrypt if available, otherwise use pbkdf2
try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False


def hash_password(password: str) -> str:
    """hash a password securely.

    uses bcrypt if available, otherwise falls back to pbkdf2.
    """
    if HAS_BCRYPT:
        return bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
    else:
        # fallback to pbkdf2
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        return f"pbkdf2:{salt.hex()}:{key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """verify a password against its hash."""
    if HAS_BCRYPT and not hashed.startswith('pbkdf2:'):
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed.encode('utf-8')
        )
    elif hashed.startswith('pbkdf2:'):
        # pbkdf2 format: pbkdf2:salt_hex:key_hex
        parts = hashed.split(':')
        if len(parts) != 3:
            return False
        salt = bytes.fromhex(parts[1])
        stored_key = bytes.fromhex(parts[2])
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        return key == stored_key
    else:
        # plain text comparison for legacy data
        return password == hashed
