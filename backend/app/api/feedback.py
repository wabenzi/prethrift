from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy import select as _select
from sqlalchemy.orm import Session

from .. import user_state
from ..db_models import Base, Garment

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    user_id: str
    garment_id: int
    action: str  # like, dislike, view, click
    weight: float | None = None
    negative: bool | None = None


@router.post("")
def feedback(req: FeedbackRequest):  # pragma: no cover
    action = req.action.lower().strip()
    if action not in {"like", "dislike", "view", "click"}:
        raise HTTPException(status_code=400, detail="invalid action")
    engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./prethrift.db"), future=True)
    Base.metadata.create_all(engine)
    from ..db_models import InteractionEvent, UserPreference

    with Session(engine) as session:
        garment = session.get(Garment, req.garment_id)
        if not garment:
            raise HTTPException(status_code=404, detail="garment not found")
        _ = garment.attributes
        session.add(
            InteractionEvent(
                user_id=req.user_id,
                garment_id=garment.id,
                event_type=action,
                weight_delta=req.weight or 1.0,
            )
        )
        delta = 0.0
        if action == "like":
            delta = req.weight or 1.0
        elif action == "dislike":
            delta = -1.0 * (req.weight or 1.0)
        elif action == "view":
            delta = 0.1 * (req.weight or 1.0)
        elif action == "click":
            delta = 0.3 * (req.weight or 1.0)
        if delta != 0 and garment.attributes:
            for ga in garment.attributes:
                av_id = ga.attribute_value_id
                pref = session.scalar(
                    _select(UserPreference).where(
                        (UserPreference.user_id == req.user_id)
                        & (UserPreference.attribute_value_id == av_id)
                    )
                )
                if pref is None:
                    session.add(
                        UserPreference(
                            user_id=req.user_id,
                            attribute_value_id=av_id,
                            weight=delta,
                            confidence=1.0,
                        )
                    )
                else:
                    pref.weight += delta
        session.commit()
    user_state.set_user_embedding(req.user_id, None)
    user_state.set_user_embedding(req.user_id + "__neg", None)
    return {"status": "ok"}
