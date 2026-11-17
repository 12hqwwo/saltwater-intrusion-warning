import hashlib
import hmac
import os

DUMMY_PASSWORD_HASH = (
    'scrypt$16384$8$1'
    '$00000000000000000000000000000000'
    '$0000000000000000000000000000000000000000000000000000000000000000'
)


def hash_password(password: str) -> str:
    if len(password) < 12 or len(password) > 1024:
        raise ValueError('Mật khẩu phải dài từ 12 đến 1024 ký tự.')
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f'scrypt$16384$8$1${salt.hex()}${digest.hex()}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, digest = encoded.split('$')
        if algorithm != 'scrypt' or (int(n), int(r), int(p)) != (16384, 8, 1):
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(actual, bytes.fromhex(digest))
    except (ValueError, TypeError, UnicodeError):
        return False
