"""Main FastAPI application bootstrap with observability.

Defines the FastAPI `app`, includes modular routers, and exposes a root health
endpoint plus an admin cache clear endpoint. All business logic resides in
router modules under `app.api`.
"""

import base64 as _b64
import datetime as _dt
import json as _json
import sys
from typing import Any, Dict

import boto3
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .api.feedback import router as feedback_router
from .api.ingest import router as ingest_router
from .api.inventory import router as inventory_router
from .api.search import router as search_router
from .api.user_profile import router as user_router
from .auth import build_user_key_prefix, cognito_dependency
from .config import settings
from .core import clear_embedding_cache, get_client
from .describe_images import describe_image, embed_text
from .health_simple import router as health_router
from .observability_simple import (
    create_prometheus_metrics_endpoint,
    get_logger,
    instrument_app,
    logging_middleware,
)

# Re-export get_client for backward compatibility with tests importing
# backend.app.main.get_client
__all__ = ["app", "get_client", "describe_image", "embed_text"]

# Initialize logger
logger = get_logger(__name__)

app = FastAPI(
    title="Prethrift API",
    description="Enhanced thrift store search with AI-powered visual and text matching",
    version=settings.service_version,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=settings.allowed_methods_list,
    allow_headers=settings.allowed_headers_list,
)

# Add observability middleware
app.middleware("http")(logging_middleware)

# Instrument with OpenTelemetry
instrument_app(app)

# Include routers
app.include_router(health_router)
app.include_router(search_router)
app.include_router(user_router)
app.include_router(feedback_router)
app.include_router(inventory_router)
app.include_router(ingest_router)

# Add metrics endpoint
app.get("/metrics")(create_prometheus_metrics_endpoint())


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(
        "Starting Prethrift API",
        version=app.version,
        environment=settings.environment,
        python_version=sys.version,
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Prethrift API")


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint with basic API information."""
    logger.info("Root endpoint accessed")
    return {
        "status": "ok",
        "message": "Prethrift API",
        "version": app.version,
        "environment": settings.environment,
    }


@app.post("/admin/clear-embedding-cache")
def clear_embedding() -> dict[str, str]:
    clear_embedding_cache()
    return {"status": "cleared"}


class PresignRequest(BaseModel):
    object_key: str | None = None
    content_type: str | None = None
    upload_type: str | None = "post"  # 'post' or 'put'
    acl: str | None = None
    cache_control: str | None = None


def _build_post_policy(
    bucket: str,
    key: str,
    content_type: str | None,
    max_bytes: int,
    acl: str | None,
    cache_control: str | None,
    region: str,
    access_key: str,
) -> dict[str, str]:
    expiration = (_dt.datetime.utcnow() + _dt.timedelta(minutes=5)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )
    date_stamp = _dt.datetime.utcnow().strftime("%Y%m%d")
    amz_date = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    credential = f"{access_key}/{date_stamp}/{region}/s3/aws4_request"
    conditions: list = [
        {"bucket": bucket},
        ["starts-with", "$key", key],
        ["content-length-range", 1, max_bytes],
        {"x-amz-algorithm": "AWS4-HMAC-SHA256"},
        {"x-amz-credential": credential},
        {"x-amz-date": amz_date},
    ]
    if content_type:
        conditions.append(["starts-with", "$Content-Type", content_type])
    if acl:
        conditions.append({"acl": acl})
    if cache_control:
        conditions.append(["starts-with", "$Cache-Control", cache_control])
    policy_doc = {"expiration": expiration, "conditions": conditions}
    policy_b64 = _b64.b64encode(_json.dumps(policy_doc).encode()).decode()
    return {"policy": policy_b64, "x_amz_date": amz_date, "x_amz_credential": credential}


def require_api_key(x_api_key: str | None = Header(default=None)):
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.post("/upload/presign")
def create_presigned_upload(
    req: PresignRequest,
    _: None = Depends(require_api_key),
    claims: Dict[str, Any] = Depends(cognito_dependency),
) -> Dict[str, Any]:
    """Return pre-signed upload parameters for external clients.

    Supports:
    - POST (browser form upload) returning policy + form fields
    - PUT (simple single-shot upload) returning a signed URL
    """
    bucket = settings.images_bucket
    if not bucket:
        raise HTTPException(status_code=500, detail="IMAGES_BUCKET not configured")
    region = settings.aws_region
    session = boto3.Session()
    credentials = session.get_credentials()
    if not credentials:
        raise HTTPException(status_code=500, detail="AWS credentials not available")
    frozen = credentials.get_frozen_credentials()
    s3 = session.client("s3", region_name=region)
    max_bytes = settings.max_upload_bytes

    key_prefix = build_user_key_prefix(claims)
    object_key = req.object_key or "upload.bin"
    if not object_key.startswith(key_prefix):
        object_key = key_prefix + object_key.lstrip("/")

    if req.upload_type == "put":
        params = {"Bucket": bucket, "Key": object_key}
        if req.content_type:
            params["ContentType"] = req.content_type
        if req.acl:
            params["ACL"] = req.acl
        if req.cache_control:
            params["CacheControl"] = req.cache_control
        url = s3.generate_presigned_url("put_object", Params=params, ExpiresIn=300)
        return {"type": "put", "url": url, "key": object_key, "method": "PUT"}

    # POST policy route (SigV4). We compute signature manually.
    policy_parts = _build_post_policy(
        bucket,
        object_key,
        req.content_type,
        max_bytes,
        req.acl,
        req.cache_control,
        region,
        frozen.access_key,
    )
    policy_b64 = policy_parts["policy"]
    amz_date = policy_parts["x_amz_date"]
    credential = policy_parts["x_amz_credential"]

    def _sign(key: bytes, msg: str) -> bytes:
        import hashlib
        import hmac

        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    date_stamp = amz_date[:8]
    k_date = _sign(("AWS4" + frozen.secret_key).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, "s3")
    k_signing = _sign(k_service, "aws4_request")
    import hashlib
    import hmac

    signature = hmac.new(k_signing, policy_b64.encode(), hashlib.sha256).hexdigest()

    form_fields: dict[str, str] = {
        "key": object_key,
        "policy": policy_b64,
        "x-amz-algorithm": "AWS4-HMAC-SHA256",
        "x-amz-credential": credential,
        "x-amz-date": amz_date,
        "x-amz-signature": signature,
    }
    if frozen.token:
        form_fields["x-amz-security-token"] = frozen.token
    if req.content_type:
        form_fields["Content-Type"] = req.content_type
    if req.acl:
        form_fields["acl"] = req.acl
    if req.cache_control:
        form_fields["Cache-Control"] = req.cache_control

    return {
        "type": "post",
        "url": f"https://{bucket}.s3.{region}.amazonaws.com",
        "fields": form_fields,
        "key": object_key,
    }


try:
    from mangum import Mangum  # type: ignore

    handler = Mangum(app)
except Exception:  # pragma: no cover
    handler = None
