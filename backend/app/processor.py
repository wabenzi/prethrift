"""S3 object created processor Lambda entrypoint.

This Lambda is triggered when a new image is uploaded to the IMAGES_BUCKET.
It standardizes, classifies, and inserts records similar to the synchronous
/process API but in an asynchronous batch fashion.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

import boto3
from sqlalchemy.orm import Session

from .api.inventory import (  # type: ignore
    AttributeValue,
    Garment,
    InventoryItem,
    _upsert_inventory_image,  # reuse
    attribute_confidences,
    classify_basic_cached,
    safe_add_garment_attribute,
)
from .core import embed_text_cached, get_client
from .image_features import image_to_feature
from .ingest import get_engine
from .inventory_processing import (
    color_stats,
    describe_inventory_image_multi,
    standardize_and_optimize,
)

s3 = boto3.client("s3")
events = boto3.client("events")


def handler(event, context):  # noqa: D401
    bucket = os.getenv("IMAGES_BUCKET")
    if not bucket:
        return {"status": "error", "reason": "IMAGES_BUCKET not set"}
    engine = get_engine()
    client_local = get_client() if "OPENAI_API_KEY" in os.environ else None
    for record in event.get("Records", []):
        if record.get("eventName", "").startswith("ObjectCreated"):
            key = record["s3"]["object"]["key"]
            with tempfile.NamedTemporaryFile(suffix="-inv") as tmp:
                s3.download_file(bucket, key, tmp.name)
                optimized_path, w, h, fmt = standardize_and_optimize(tmp.name)
                with Session(engine) as session:
                    img = _upsert_inventory_image(
                        session, optimized_path, w, h, fmt, overwrite=False
                    )
                    # classification pipeline
                    garment_entries = describe_inventory_image_multi(
                        client_local, img.file_path, None
                    )
                    for entry in garment_entries:
                        idx = entry["index"]
                        desc = entry["description"]
                        embedding = []
                        if client_local:
                            try:
                                embedding = embed_text_cached(desc)
                            except Exception:
                                embedding = []
                        try:
                            img_feature = image_to_feature(img.file_path).tolist()
                        except Exception:
                            img_feature = []
                        external_id = f"inv-{img.id}-{idx}"
                        g_existing = (
                            session.query(Garment).filter_by(external_id=external_id).first()
                        )
                        if not g_existing:
                            g_existing = Garment(
                                external_id=external_id,
                                image_path=img.file_path,
                                description=desc,
                                description_embedding=embedding or None,
                                image_embedding=img_feature or None,
                            )
                            session.add(g_existing)
                            session.flush()
                        inv_item = (
                            session.query(InventoryItem)
                            .filter_by(image_id=img.id, slot_index=idx)
                            .first()
                        )
                        if not inv_item:
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
                        inferred = classify_basic_cached(desc)
                        conf_map = attribute_confidences(desc, inferred) if inferred else {}
                        if inferred and g_existing:
                            existing_pairs = {
                                (ga.attribute.family, ga.attribute.value)
                                for ga in g_existing.attributes or []
                            }
                            for fam, vals in inferred.items():
                                for v in vals:
                                    if (fam, v) in existing_pairs:
                                        continue
                                    av = (
                                        session.query(AttributeValue)
                                        .filter_by(family=fam, value=v)
                                        .first()
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
                    img.processed = True
                    session.commit()
                    # Emit EventBridge event summarizing processing result
                    try:
                        bus_name = os.getenv("EVENT_BUS_NAME")
                        if bus_name:
                            details: dict[str, Any] = {
                                "image_id": img.id,
                                "file_path": img.file_path,
                                "garments": len(garment_entries),
                                "width": w,
                                "height": h,
                            }
                            events.put_events(
                                Entries=[
                                    {
                                        "Source": "prethrift.image-processor",
                                        "DetailType": "InventoryImageProcessed",
                                        "Detail": json.dumps(details),
                                        "EventBusName": bus_name,
                                    }
                                ]
                            )
                    except Exception:
                        # Swallow event emission errors to not fail ingestion
                        pass
    return {"status": "ok"}
