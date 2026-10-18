import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

# Argon2id password hasher with production-standard configuration
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
    salt_len=16
)

def hash_secret(secret: str) -> str:
    """
    Hash a password or secret string with Argon2id.
    """
    return _hasher.hash(secret)

def verify_secret(secret_hash: str, secret: str) -> bool:
    """
    Verify a password or secret against an Argon2id hash in constant time.
    """
    try:
        return _hasher.verify(secret_hash, secret)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:
        return False

def generate_recovery_codes(count: int = 10) -> tuple[list[str], list[str]]:
    """
    Generate single-use formatted recovery codes.
    Returns:
        (plain_codes, hashed_codes)
    """
    plain_codes = []
    hashed_codes = []
    for _ in range(count):
        # Human-readable format: LL-XXXX-XXXX
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        code = f"LL-{part1}-{part2}"
        plain_codes.append(code)
        hashed_codes.append(hash_secret(code))
    return plain_codes, hashed_codes

def verify_recovery_code(code_hash: str, candidate_code: str) -> bool:
    """
    Verify candidate recovery code against an Argon2id hash.
    Normalizes candidate whitespace and casing.
    """
    clean_candidate = candidate_code.strip().upper()
    return verify_secret(code_hash, clean_candidate)
