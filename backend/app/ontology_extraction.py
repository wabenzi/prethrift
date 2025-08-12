"""
Ontology extraction service for populating garment properties from CLIP analysis and descriptions.

This service uses the enhanced ontology system to extract structured properties
from garment images and descriptions, populating the database columns for
rich filtering and display capabilities.
"""

import logging
from datetime import UTC, datetime
from typing import Any, Optional

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from sqlalchemy.orm import Session

from .db_models import Garment
from .local_cv import LocalGarmentAnalyzer
from .ontology import attribute_confidences, classify_basic_cached

logger = logging.getLogger(__name__)


class OntologyExtractionService:
    """Service for extracting and populating ontology-based garment properties."""

    def __init__(self):
        self.clip_analyzer = None
        self._initialize_clip()

    def _initialize_clip(self):
        """Initialize CLIP analyzer if available."""
        try:
            self.clip_analyzer = LocalGarmentAnalyzer()
            logger.info("CLIP analyzer initialized for ontology extraction")
        except Exception as e:
            logger.warning(f"CLIP analyzer not available: {e}")

    def extract_properties(
        self, garment: Garment, session: Session, force_reextract: bool = False
    ) -> bool:
        """
        Extract and populate ontology properties for a garment.

        Args:
            garment: Garment instance to process
            session: SQLAlchemy session
            force_reextract: Whether to re-extract even if already processed

        Returns:
            True if properties were extracted successfully
        """
        # Skip if already processed (unless forcing)
        if not force_reextract and garment.properties_extracted_at is not None:
            logger.debug(f"Garment {garment.id} already has properties extracted")
            return True

        try:
            # Extract properties from multiple sources
            image_properties = self._extract_from_image(garment)
            text_properties = self._extract_from_text(garment)

            # Combine and resolve conflicts
            final_properties = self._merge_properties(image_properties, text_properties)

            # Apply properties to garment
            self._apply_properties(garment, final_properties)

            # Generate OpenAI embeddings if description available
            if garment.description:
                self._generate_openai_embeddings(garment)

            # Mark as processed
            garment.properties_extracted_at = datetime.now(UTC)

            session.commit()
            logger.info(f"Successfully extracted properties for garment {garment.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to extract properties for garment {garment.id}: {e}")
            session.rollback()
            return False

    def _extract_from_image(self, garment: Garment) -> dict[str, Any]:
        """Extract properties from garment image using CLIP."""
        properties = {}

        if not self.clip_analyzer or not garment.image_path:
            return properties

        try:
            # Load image
            if not PIL_AVAILABLE:
                logger.warning("PIL not available, skipping image analysis")
                return properties

            image = Image.open(garment.image_path)
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Use CLIP to analyze the image
            analysis = self.clip_analyzer.analyze_image(image)

            # Extract structured properties from CLIP analysis
            if analysis.get("garments"):
                primary_garment = analysis["garments"][0]  # Use the most confident detection

                # Map CLIP categories to our ontology
                category_mapping = {
                    "t-shirt": "tops",
                    "shirt": "tops",
                    "blouse": "tops",
                    "dress": "dresses",
                    "skirt": "bottoms",
                    "pants": "bottoms",
                    "jeans": "bottoms",
                    "shorts": "bottoms",
                    "jacket": "outerwear",
                    "coat": "outerwear",
                    "blazer": "outerwear",
                    "sneakers": "shoes",
                    "boots": "shoes",
                    "heels": "shoes",
                }

                clip_category = primary_garment.get("category", "").lower()
                if clip_category in category_mapping:
                    properties["category"] = category_mapping[clip_category]
                    properties["subcategory"] = clip_category

            # Extract color information
            if analysis.get("attributes", {}).get("colors"):
                colors = analysis["attributes"]["colors"]
                if colors:
                    properties["primary_color"] = colors[0].get("color", "").lower()
                    if len(colors) > 1:
                        properties["secondary_color"] = colors[1].get("color", "").lower()

            # Extract style and material hints
            if analysis.get("attributes", {}).get("styles"):
                styles = analysis["attributes"]["styles"]
                if styles:
                    properties["style"] = styles[0].get("style", "").lower()

            # Set confidence based on CLIP confidence
            properties["ontology_confidence"] = analysis.get("confidence", 0.5)

        except Exception as e:
            logger.warning(f"Image analysis failed for garment {garment.id}: {e}")

        return properties

    def _extract_from_text(self, garment: Garment) -> dict[str, Any]:
        """Extract properties from garment description using ontology mapping."""
        properties = {}

        if not garment.description:
            return properties

        try:
            # Use our enhanced ontology system
            raw_attributes = classify_basic_cached(garment.description)
            confidence_scores = attribute_confidences(garment.description, raw_attributes)

            # Convert to expected format with confidence scores
            ontology_result = {}
            for family, values in raw_attributes.items():
                ontology_result[family] = [
                    {"value": value, "confidence": confidence_scores.get((family, value), 0.5)}
                    for value in values
                ]

            # Map ontology results to database columns
            dimension_mapping = {
                "category": "category",
                "color": "primary_color",
                "material": "material",
                "style": "style",
                "fit": "fit",
                "season": "season",
                "occasion": "occasion",
                "era": "era",
                "gender": "gender",
                "brand": "brand",  # Can validate against existing brand
            }

            for dimension, db_column in dimension_mapping.items():
                if dimension in ontology_result:
                    values = ontology_result[dimension]
                    if values:
                        # Take the highest confidence value
                        best_value = max(values, key=lambda x: x["confidence"])
                        properties[db_column] = best_value["value"].lower()

            # Extract subcategory if available
            if "subcategory" in ontology_result and ontology_result["subcategory"]:
                best_subcat = max(ontology_result["subcategory"], key=lambda x: x["confidence"])
                properties["subcategory"] = best_subcat["value"].lower()

            # Calculate overall confidence
            all_confidences = []
            for values in ontology_result.values():
                if isinstance(values, list):
                    all_confidences.extend([v["confidence"] for v in values])

            if all_confidences:
                properties["ontology_confidence"] = sum(all_confidences) / len(all_confidences)

        except Exception as e:
            logger.warning(f"Text analysis failed for garment {garment.id}: {e}")

        return properties

    def _merge_properties(
        self, image_props: dict[str, Any], text_props: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge properties from image and text analysis, resolving conflicts."""
        merged = {}

        # Start with text properties (generally more reliable for detailed attributes)
        merged.update(text_props)

        # Override with image properties where they're more reliable
        image_priority_fields = ["primary_color", "secondary_color", "category"]

        for field in image_priority_fields:
            if field in image_props and image_props[field]:
                merged[field] = image_props[field]

        # Take the higher confidence score
        text_conf = text_props.get("ontology_confidence", 0)
        image_conf = image_props.get("ontology_confidence", 0)
        merged["ontology_confidence"] = max(text_conf, image_conf)

        return merged

    def _apply_properties(self, garment: Garment, properties: dict[str, Any]):
        """Apply extracted properties to the garment instance."""
        property_fields = [
            "category",
            "subcategory",
            "primary_color",
            "secondary_color",
            "pattern",
            "material",
            "style",
            "fit",
            "season",
            "occasion",
            "era",
            "gender",
            "ontology_confidence",
        ]

        for field in property_fields:
            if field in properties:
                setattr(garment, field, properties[field])

        # Set designer tier based on brand (simple heuristic)
        if garment.brand:
            luxury_brands = {"gucci", "prada", "louis vuitton", "chanel", "dior"}
            premium_brands = {"ralph lauren", "tommy hilfiger", "calvin klein", "hugo boss"}

            brand_lower = garment.brand.lower()
            if any(luxury in brand_lower for luxury in luxury_brands):
                garment.designer_tier = "luxury"
            elif any(premium in brand_lower for premium in premium_brands):
                garment.designer_tier = "premium"
            else:
                garment.designer_tier = "mid-range"

    def _generate_openai_embeddings(self, garment: Garment):
        """Generate OpenAI embeddings for the garment description."""
        # This would integrate with the existing describe_images.py functionality
        # For now, we'll use a placeholder since OpenAI embeddings are already
        # being generated elsewhere in the system
        logger.info(f"OpenAI embeddings should be generated for garment {garment.id}")

    def batch_extract(
        self, session: Session, limit: Optional[int] = None, force_reextract: bool = False
    ) -> tuple[int, int]:
        """
        Extract properties for multiple garments in batch.

        Args:
            session: SQLAlchemy session
            limit: Maximum number of garments to process
            force_reextract: Whether to re-extract for garments already processed

        Returns:
            Tuple of (processed_count, success_count)
        """
        query = session.query(Garment)

        if not force_reextract:
            query = query.filter(Garment.properties_extracted_at.is_(None))

        if limit:
            query = query.limit(limit)

        garments = query.all()
        processed = 0
        successful = 0

        for garment in garments:
            processed += 1
            if self.extract_properties(garment, session, force_reextract):
                successful += 1

            if processed % 10 == 0:
                logger.info(f"Processed {processed}/{len(garments)} garments")

        logger.info(f"Batch extraction complete: {successful}/{processed} successful")
        return processed, successful


def extract_properties_for_garment(garment_id: int, session: Session) -> bool:
    """
    Convenience function to extract properties for a single garment.

    Args:
        garment_id: ID of the garment to process
        session: SQLAlchemy session

    Returns:
        True if successful
    """
    service = OntologyExtractionService()
    garment = session.get(Garment, garment_id)

    if not garment:
        logger.error(f"Garment {garment_id} not found")
        return False

    return service.extract_properties(garment, session)


def batch_extract_properties(session: Session, limit: Optional[int] = None) -> tuple[int, int]:
    """
    Convenience function for batch property extraction.

    Args:
        session: SQLAlchemy session
        limit: Maximum number of garments to process

    Returns:
        Tuple of (processed_count, success_count)
    """
    service = OntologyExtractionService()
    return service.batch_extract(session, limit)
