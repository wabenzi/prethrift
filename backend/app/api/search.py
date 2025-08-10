from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import query_pipeline

router = APIRouter(prefix="", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    limit: int | None = 10
    model: str | None = None
    user_id: str | None = None


@router.post("/search")
def search(req: SearchRequest) -> dict[str, Any]:
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")
    try:
        return query_pipeline.search(
            req.query, limit=req.limit or 10, model=req.model, user_id=req.user_id
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e
