"""Utility functions for working with native vector columns and embeddings."""

import json
import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

def migrate_json_to_vector(json_embedding: Optional[List[float]]) -> Optional[Any]:
    """
    Convert JSON-stored embedding to native vector format.

    Args:
        json_embedding: List of floats stored in JSON column

    Returns:
        Vector-compatible format or None if input is None/invalid
    """
    if json_embedding is None:
        return None

    if not isinstance(json_embedding, list):
        logger.warning(f"Expected list, got {type(json_embedding)}")
        return None

    if not json_embedding:  # Empty list
        return None

    # pgvector expects the raw list for SQLAlchemy operations
    return json_embedding

def vector_to_json_fallback(vector_embedding: Any) -> Optional[List[float]]:
    """
    Convert native vector back to JSON format for fallback compatibility.

    Args:
        vector_embedding: Native vector column value

    Returns:
        List of floats or None if input is None/invalid
    """
    if vector_embedding is None:
        return None

    # If it's already a list, return as-is
    if isinstance(vector_embedding, list):
        return vector_embedding

    # Handle string representation (shouldn't happen normally)
    if isinstance(vector_embedding, str):
        try:
            return json.loads(vector_embedding)
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Could not parse vector string: {vector_embedding}")
            return None

    # Try to convert to list (for numpy arrays or similar)
    try:
        return list(vector_embedding)
    except (TypeError, ValueError):
        logger.warning(f"Could not convert vector to list: {type(vector_embedding)}")
        return None

def get_embedding_for_search(obj, field_name: str) -> Optional[List[float]]:
    """
    Get embedding for similarity search, preferring vector column over JSON.

    Args:
        obj: Database model instance
        field_name: Base field name (e.g., 'description_embedding')

    Returns:
        List of floats suitable for similarity search
    """
    # Try vector column first (optimal performance)
    vector_field = f"{field_name}_vec"
    if hasattr(obj, vector_field):
        vector_value = getattr(obj, vector_field)
        if vector_value is not None:
            return vector_to_json_fallback(vector_value)

    # Fall back to JSON column
    if hasattr(obj, field_name):
        json_value = getattr(obj, field_name)
        if json_value is not None:
            return json_value

    return None

def set_embeddings_dual_format(obj, field_name: str, embedding: List[float]) -> None:
    """
    Set embedding in both vector and JSON formats for compatibility.

    Args:
        obj: Database model instance
        field_name: Base field name (e.g., 'description_embedding')
        embedding: List of floats to store
    """
    if embedding is None:
        return

    # Set JSON format (legacy compatibility)
    if hasattr(obj, field_name):
        setattr(obj, field_name, embedding)

    # Set vector format (optimal performance)
    vector_field = f"{field_name}_vec"
    if hasattr(obj, vector_field):
        setattr(obj, vector_field, migrate_json_to_vector(embedding))
