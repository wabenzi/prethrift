"""Main FastAPI application bootstrap (minimal).

Defines the FastAPI `app`, includes modular routers, and exposes a root health
endpoint plus an admin cache clear endpoint. All business logic resides in
router modules under `app.api`.
"""

from fastapi import FastAPI

from .api.feedback import router as feedback_router
from .api.ingest import router as ingest_router
from .api.inventory import router as inventory_router
from .api.search import router as search_router
from .api.user_profile import router as user_router
from .core import clear_embedding_cache, get_client
from .describe_images import describe_image, embed_text

# Re-export get_client for backward compatibility with tests importing
# backend.app.main.get_client
__all__ = ["app", "get_client", "describe_image", "embed_text"]

app = FastAPI()
app.include_router(search_router)
app.include_router(user_router)
app.include_router(feedback_router)
app.include_router(inventory_router)
app.include_router(ingest_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "message": "Prethrift API"}


@app.post("/admin/clear-embedding-cache")
def clear_embedding() -> dict[str, str]:
    clear_embedding_cache()
    return {"status": "cleared"}
