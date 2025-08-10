from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy import select as _select
from sqlalchemy.orm import Session

from ..color_utils import map_rgb_to_color_name
from ..core import embed_text_cached, get_client
from ..db_models import (
    AttributeValue,
    Base,
    Garment,
    InventoryImage,
    InventoryItem,
)
from ..image_features import feature_cache_stats, image_to_feature
from ..inventory_processing import (
    color_stats,
    describe_inventory_image_multi,
    persist_raw_image,
    standardize_and_optimize,
)
from ..inventory_utils import safe_add_garment_attribute
from ..ontology import attribute_confidences, classify_basic_cached

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _ensure_inventory_tables():
    engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./prethrift.db"), future=True)
    Base.metadata.create_all(engine)
    return engine


## image persistence & optimization moved to inventory_processing


def _upsert_inventory_image(
    session: Session,
    file_path: str,
    width: int,
    height: int,
    optimized_format: str,
    overwrite: bool,
) -> InventoryImage:
    existing = session.scalar(_select(InventoryImage).where(InventoryImage.file_path == file_path))
    if existing and not overwrite:
        return existing
    h = hashlib.sha1(Path(file_path).read_bytes()).hexdigest()
    if existing and overwrite:
        existing.width = width
        existing.height = height
        existing.optimized_format = optimized_format
        existing.hash = h
        existing.processed = False
        session.flush()
        return existing
    img = InventoryImage(
        file_path=file_path,
        width=width,
        height=height,
        optimized_format=optimized_format,
        original_format=optimized_format,
        hash=h,
    )
    session.add(img)
    session.flush()
    return img


## multi-garment description moved to inventory_processing


## color stats moved to inventory_processing


class InventoryUploadRequest(BaseModel):
    filename: str
    image_base64: str
    overwrite: bool = False


@router.post("/upload")
def inventory_upload(data: InventoryUploadRequest) -> dict[str, Any]:
    engine = _ensure_inventory_tables()
    with Session(engine) as session:
        # Persist + optimize image
        disk_path = persist_raw_image(data.filename, data.image_base64)
        optimized_path, w, h, fmt = standardize_and_optimize(disk_path)
        img = _upsert_inventory_image(session, optimized_path, w, h, fmt, data.overwrite)
        session.commit()
        return {
            "image_id": img.id,
            "file_path": img.file_path,
            "width": img.width,
            "height": img.height,
        }


class InventoryBatchUploadRequest(BaseModel):
    items: list[InventoryUploadRequest]
    overwrite: bool = False


@router.post("/batch-upload")
def inventory_batch_upload(data: InventoryBatchUploadRequest) -> dict[str, Any]:
    engine = _ensure_inventory_tables()
    results: list[dict[str, Any]] = []
    with Session(engine) as session:
        for item in data.items:
            disk_path = persist_raw_image(item.filename, item.image_base64)
            optimized_path, w, h, fmt = standardize_and_optimize(disk_path)
            img = _upsert_inventory_image(
                session, optimized_path, w, h, fmt, data.overwrite or item.overwrite
            )
            results.append(
                {
                    "image_id": img.id,
                    "file_path": img.file_path,
                    "width": img.width,
                    "height": img.height,
                }
            )
        session.commit()
    return {"count": len(results), "images": results}


class InventoryProcessRequest(BaseModel):
    image_id: int | None = None
    overwrite: bool = False
    model: str | None = None
    limit: int | None = None


@router.post("/process")
def inventory_process(data: InventoryProcessRequest) -> dict[str, Any]:
    engine = _ensure_inventory_tables()
    processed_items: list[dict[str, Any]] = []
    client_local = get_client() if "OPENAI_API_KEY" in os.environ else None
    with Session(engine) as session:
        if data.image_id is not None:
            single = session.get(InventoryImage, data.image_id)
            images: list[InventoryImage] = [single] if single else []
        else:
            stmt = _select(InventoryImage).where(InventoryImage.processed.is_(False))
            if data.limit:
                stmt = stmt.limit(data.limit)
            images = list(session.scalars(stmt).all())  # concrete list[InventoryImage]
        for img in images:
            if img.processed and not data.overwrite:
                continue
            garment_entries = describe_inventory_image_multi(
                client_local, img.file_path, data.model
            )
            if data.overwrite:
                session.query(InventoryItem).filter(InventoryItem.image_id == img.id).delete()
            for entry in garment_entries:
                idx = entry["index"]
                desc = entry["description"]
                existing_item = (
                    session.query(InventoryItem).filter_by(image_id=img.id, slot_index=idx).first()
                )
                if existing_item and not data.overwrite:
                    continue
                embedding: list[float] = []
                if client_local:
                    try:
                        embedding = embed_text_cached(desc)
                    except Exception:  # noqa: BLE001
                        embedding = []
                try:
                    img_feature = image_to_feature(img.file_path).tolist()
                except Exception:  # noqa: BLE001
                    img_feature = []
                external_id = f"inv-{img.id}-{idx}"
                g_existing = session.query(Garment).filter_by(external_id=external_id).first()
                if g_existing and data.overwrite:
                    g_existing.description = desc
                    if embedding:
                        g_existing.description_embedding = embedding
                elif not g_existing:
                    g_existing = Garment(
                        external_id=external_id,
                        image_path=img.file_path,
                        description=desc,
                        description_embedding=embedding or None,
                        image_embedding=img_feature or None,
                    )
                    session.add(g_existing)
                    session.flush()
                if existing_item and data.overwrite:
                    existing_item.description = desc
                    existing_item.description_embedding = embedding or None
                    inv_item = existing_item
                elif not existing_item:
                    inv_item = InventoryItem(
                        image_id=img.id,
                        garment_id=g_existing.id,
                        slot_index=idx,
                        description=desc,
                        description_embedding=embedding or None,
                        attributes_extracted=False,
                        color_stats=None,
                    )
                    session.add(inv_item)
                    session.flush()
                else:
                    inv_item = existing_item
                inferred = classify_basic_cached(desc)
                conf_map = attribute_confidences(desc, inferred) if inferred else {}
                if inferred and g_existing:
                    existing_pairs = {
                        (ga.attribute.family, ga.attribute.value)
                        for ga in g_existing.attributes or []
                    }
                    for fam, vals in inferred.items():
                        for v in vals:
                            if (fam, v) in existing_pairs and not data.overwrite:
                                continue
                            if (fam, v) in existing_pairs and data.overwrite:
                                continue
                            av = (
                                session.query(AttributeValue).filter_by(family=fam, value=v).first()
                            )
                            if not av:
                                av = AttributeValue(family=fam, value=v)
                                session.add(av)
                                session.flush()
                            safe_add_garment_attribute(
                                session,
                                garment_id=g_existing.id,
                                av_id=av.id,
                                confidence=conf_map.get((fam, v), 0.5),
                            )
                            existing_pairs.add((fam, v))
                    inv_item.attributes_extracted = True
                inv_item.color_stats = color_stats(img.file_path)
                cs = inv_item.color_stats or {}
                mean_rgb = cs.get("mean_rgb") if isinstance(cs, dict) else None
                if mean_rgb:
                    dom_color = map_rgb_to_color_name(mean_rgb)
                    if dom_color:
                        from ..ontology import normalize as _norm

                        norm_val = _norm("color_primary", dom_color) or dom_color
                        av = (
                            session.query(AttributeValue)
                            .filter_by(family="color_primary", value=norm_val)
                            .first()
                        )
                        if not av:
                            av = AttributeValue(family="color_primary", value=norm_val)
                            session.add(av)
                            session.flush()
                        safe_add_garment_attribute(
                            session, garment_id=g_existing.id, av_id=av.id, confidence=0.6
                        )
                processed_items.append(
                    {
                        "image_id": img.id,
                        "slot_index": idx,
                        "garment_id": g_existing.id if g_existing else None,
                        "description_len": len(desc),
                        "attributes": inferred,
                        "color_stats": inv_item.color_stats,
                    }
                )
            img.processed = True
            session.commit()
        session.commit()
    return {"processed_count": len(processed_items), "items": processed_items}


@router.get("/images")
def inventory_images(
    limit: int = 50, offset: int = 0, processed: bool | None = None
) -> dict[str, Any]:
    engine = _ensure_inventory_tables()
    with Session(engine) as session:
        stmt = _select(InventoryImage)
        if processed is not None:
            stmt = stmt.where(InventoryImage.processed.is_(processed))
        rows = session.scalars(stmt).all()
        subset = rows[offset : offset + limit]
        return {
            "count": len(rows),
            "images": [
                {
                    "id": im.id,
                    "file_path": im.file_path,
                    "width": im.width,
                    "height": im.height,
                    "processed": im.processed,
                }
                for im in subset
            ],
        }


@router.get("/items")
def inventory_items(
    image_id: int | None = None, limit: int = 50, offset: int = 0
) -> dict[str, Any]:
    engine = _ensure_inventory_tables()
    with Session(engine) as session:
        stmt = _select(InventoryItem)
        if image_id is not None:
            stmt = stmt.where(InventoryItem.image_id == image_id)
        rows = session.scalars(stmt).all()
        subset = rows[offset : offset + limit]
        return {
            "count": len(rows),
            "items": [
                {
                    "id": it.id,
                    "image_id": it.image_id,
                    "garment_id": it.garment_id,
                    "slot_index": it.slot_index,
                    "has_embedding": bool(it.description_embedding),
                    "attributes_extracted": it.attributes_extracted,
                    "has_color_stats": bool(it.color_stats),
                }
                for it in subset
            ],
        }


@router.get("/stats")
def inventory_stats() -> dict[str, Any]:
    engine = _ensure_inventory_tables()
    from ..ontology import classify_cache_stats

    with Session(engine) as session:
        total_images = session.query(InventoryImage).count()
        processed_images = (
            session.query(InventoryImage).filter(InventoryImage.processed.is_(True)).count()
        )
        total_items = session.query(InventoryItem).count()
        color_stats_items = (
            session.query(InventoryItem).filter(InventoryItem.color_stats.is_not(None)).count()
        )
        inventory_garments = (
            session.query(Garment).filter(Garment.external_id.like("inv-%")).count()
        )
        color_cluster_dist: dict[int, int] = {}
        avg_cluster_count = 0.0
        single_color_items = 0
        multi_color_items = 0
        if color_stats_items:
            items_with_color = (
                session.query(InventoryItem.id, InventoryItem.color_stats)
                .filter(InventoryItem.color_stats.is_not(None))
                .all()
            )
            cluster_counts: list[int] = []
            for _id, cs in items_with_color:
                if isinstance(cs, dict):
                    cc = cs.get("cluster_count")
                    if isinstance(cc, int) and cc >= 0:
                        cluster_counts.append(cc)
                        color_cluster_dist[cc] = color_cluster_dist.get(cc, 0) + 1
            if cluster_counts:
                from statistics import fmean

                avg_cluster_count = float(fmean(cluster_counts))
                single_color_items = color_cluster_dist.get(1, 0)
                multi_color_items = sum(v for k, v in color_cluster_dist.items() if k > 1)
        return {
            "total_images": total_images,
            "processed_images": processed_images,
            "unprocessed_images": total_images - processed_images,
            "total_items": total_items,
            "items_with_color_stats": color_stats_items,
            "inventory_garments": inventory_garments,
            "color_clusters": {
                "distribution": color_cluster_dist,
                "avg_cluster_count": round(avg_cluster_count, 3),
                "single_color_items": single_color_items,
                "multi_color_items": multi_color_items,
            },
            "classifier_cache": classify_cache_stats(),
            "feature_cache": feature_cache_stats(),
        }
