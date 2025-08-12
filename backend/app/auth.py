import json
import os
import time
import urllib.request
from typing import Any, Dict

from fastapi import Header, HTTPException
from jose import jwk, jwt
from jose.utils import base64url_decode

_JWKS_CACHE: Dict[str, Any] | None = None
_JWKS_EXPIRES_AT: float = 0.0


def _fetch_jwks(jwks_url: str) -> Dict[str, Any]:
    global _JWKS_CACHE, _JWKS_EXPIRES_AT
    now = time.time()
    if _JWKS_CACHE and now < _JWKS_EXPIRES_AT:
        return _JWKS_CACHE
    with urllib.request.urlopen(jwks_url) as resp:  # nosec B310
        data = json.loads(resp.read())
    _JWKS_CACHE = data
    _JWKS_EXPIRES_AT = now + 3600  # 1 hour cache
    return data


def verify_cognito_jwt(token: str) -> Dict[str, Any]:
    region = os.getenv("COGNITO_REGION") or os.getenv("AWS_REGION") or "us-east-1"
    user_pool_id = os.getenv("COGNITO_USER_POOL_ID")
    app_client_id = os.getenv("COGNITO_APP_CLIENT_ID")
    if not user_pool_id or not app_client_id:
        raise HTTPException(status_code=500, detail="Cognito not configured")
    jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
    keys = _fetch_jwks(jwks_url)["keys"]
    try:
        headers = jwt.get_unverified_header(token)
    except Exception:  # pragma: no cover - invalid header
        raise HTTPException(status_code=401, detail="Invalid token header")
    kid = headers.get("kid")
    key_data = next((k for k in keys if k.get("kid") == kid), None)
    if not key_data:
        raise HTTPException(status_code=401, detail="Unknown kid")
    public_key = jwk.construct(key_data)
    message, encoded_sig = token.rsplit(".", 1)
    decoded_sig = base64url_decode(encoded_sig.encode())
    if not public_key.verify(message.encode(), decoded_sig):
        raise HTTPException(status_code=401, detail="Signature verification failed")
    claims = jwt.get_unverified_claims(token)
    if time.time() > claims.get("exp", 0):
        raise HTTPException(status_code=401, detail="Token expired")
    aud = claims.get("aud") or claims.get("client_id")
    if app_client_id and aud != app_client_id:
        raise HTTPException(status_code=401, detail="Invalid audience")
    return claims


def cognito_dependency(authorization: str | None = Header(default=None)) -> Dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split()[1]
    return verify_cognito_jwt(token)


def build_user_key_prefix(claims: Dict[str, Any]) -> str:
    sub = claims.get("sub") or "anonymous"
    return f"users/{sub}/uploads/"
