"""Authentication utilities.

This module provides helpers for password hashing and JSON Web Token
creation/verification used across the application. The helpers are
intentionally small and focussed to keep the crypto surface area easy to
test and review.

Security notes:
- Passwords are hashed using bcrypt with a per-password salt.
- JWT creation uses symmetric signing with the key in `src.config.Config`.
    Ensure the key is strong and kept secret in production.
"""

import bcrypt
from datetime import datetime, timedelta, timezone
import jwt
import uuid
from src.config import Config
from fastapi import HTTPException, status

def generate_password_hash(password: str) -> str:
    """Return a bcrypt hash for the provided plaintext password.

    The returned value is a utf-8 string suitable for storage in the
    user database. The implementation uses a randomly generated salt
    (via `bcrypt.gensalt`) so callers should only compare hashes using
    `verify_password_hash`.

    Args:
        password: Plaintext password to hash.

    Returns:
        The bcrypt hash as a utf-8 string.
    """

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password_hash(password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash.

    Use this function to validate a user's password during authentication.

    Args:
        password: Plaintext password supplied by the user.
        hashed_password: Stored bcrypt hash to verify against.

    Returns:
        True if the password matches the hash, False otherwise.
    """

    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))



def create_token(user_data: dict, expiry_delta: timedelta, type: str):

    current_time = datetime.now(timezone.utc)
    payload = {
        'iat': current_time,
        'jti': str(uuid.uuid4()),
        'sub': str(user_data.get('user_id')),
    }

    # Compute absolute expiration time once to keep iat/exp consistent.
    payload['exp'] = current_time + expiry_delta

    payload['type'] = type.lower()


    if type == "access":
        payload['email'] = user_data.get('email')

    token = jwt.encode(
        payload=payload,
        key=Config.JWT_KEY,
        algorithm=Config.JWT_ALGORITHM
    )

    return token


def decode_token(token: str) -> dict:
    
    try:

        token_data = jwt.decode(
            jwt=token,
            key=Config.JWT_KEY,
            algorithms=[Config.JWT_ALGORITHM],
            leeway=10
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token."
        )

    except Exception as e:
        print(f"Unexpected error: {e}") 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Something went wrong processing the token."
        )
    return token_data

