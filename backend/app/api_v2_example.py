"""
Enhanced API example demonstrating Prethrift v2.0 capabilities.

This module shows how to integrate the new vector search and ontology
system into production API endpoints for maximum functionality.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .db_models import Garment
from .hybrid_search import HybridSearchEngine, SearchQuery
from .local_cv import LocalGarmentAnalyzer
from .ontology_extraction import OntologyExtractionService

app = FastAPI(title="Prethrift v2.0 API", version="2.0.0")

# Request/Response Models
class SearchFilters(BaseModel):
    """Advanced search filters using ontology properties."""
    category: Optional[str] = None
    subcategory: Optional[str] = None
    primary_color: Optional[str] = None
    material: Optional[str] = None
    style: Optional[str] = None
    brand: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    season: Optional[str] = None
    occasion: Optional[str] = None
    designer_tier: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None

class SearchRequest(BaseModel):
    """Enhanced search request with multiple query types."""
    text_query: Optional[str] = Field(None, description="Text description of desired item")
    image_query: Optional[str] = Field(None, description="Base64 encoded image or image URL")
    filters: Optional[SearchFilters] = None
    search_type: str = Field("hybrid", description="Search type: 'text', 'image', 'hybrid'")
    limit: int = Field(20, ge=1, le=100)
    min_similarity: float = Field(0.7, ge=0.0, le=1.0)

class GarmentResponse(BaseModel):
    """Enhanced garment response with ontology properties."""
    id: int
    external_id: str
    title: Optional[str]
    brand: Optional[str]
    price: Optional[float]
    currency: Optional[str]
    image_path: Optional[str]
    description: Optional[str]

    # Ontology properties
    category: Optional[str]
    subcategory: Optional[str]
    primary_color: Optional[str]
    secondary_color: Optional[str]
    material: Optional[str]
    style: Optional[str]
    fit: Optional[str]
    season: Optional[str]
    occasion: Optional[str]
    designer_tier: Optional[str]
    ontology_confidence: Optional[float]

    # Search relevance
    similarity_score: Optional[float] = None
    match_reason: Optional[str] = None

class SearchResponse(BaseModel):
    """Search results with metadata."""
    results: List[GarmentResponse]
    total_found: int
    search_time_ms: float
    filters_applied: Dict[str, Any]
    search_metadata: Dict[str, Any]

# Dependency injection
def get_db_session() -> Session:
    """Get database session (implement based on your DB setup)."""
    # This is a placeholder - implement based on your actual database setup
    # Example:
    # from sqlalchemy import create_engine
    # from sqlalchemy.orm import sessionmaker
    # engine = create_engine(DATABASE_URL)
    # SessionLocal = sessionmaker(bind=engine)
    # return SessionLocal()
    raise NotImplementedError("Implement database session creation")

def get_search_engine(session: Session = Depends(get_db_session)) -> HybridSearchEngine:
    """Get configured search engine."""
    return HybridSearchEngine(session)

def get_ontology_service() -> OntologyExtractionService:
    """Get ontology extraction service."""
    return OntologyExtractionService()

def get_clip_analyzer() -> LocalGarmentAnalyzer:
    """Get CLIP analyzer."""
    return LocalGarmentAnalyzer()

# API Endpoints

@app.post("/api/v2/search", response_model=SearchResponse)
async def enhanced_search(
    request: SearchRequest,
    search_engine: HybridSearchEngine = Depends(get_search_engine)
) -> SearchResponse:
    """
    Enhanced search with vector similarity and ontology filtering.

    Supports multiple search modes:
    - Text search: Uses OpenAI embeddings for semantic understanding
    - Image search: Uses CLIP embeddings for visual similarity
    - Hybrid search: Combines both with ontology filtering
    """
    start_time = datetime.now()

    try:
        # Convert Pydantic filters to dict
        filters_dict = {}
        if request.filters:
            filters_dict = {
                k: v for k, v in request.filters.dict().items()
                if v is not None
            }

            # Handle price range
            if request.filters.price_min or request.filters.price_max:
                filters_dict['price_range'] = (
                    request.filters.price_min or 0,
                    request.filters.price_max or float('inf')
                )
                filters_dict.pop('price_min', None)
                filters_dict.pop('price_max', None)

        # Execute search based on type
        if request.search_type == "text" and request.text_query:
            # For text search, we need to generate text embedding first
            # This would integrate with OpenAI or other text embedding service
            query = SearchQuery(
                text_embedding=None,  # Would generate from request.text_query
                limit=request.limit,
                similarity_threshold=request.min_similarity,
                brand=filters_dict.get('brand'),
                price_min=filters_dict.get('price_range', (None, None))[0],
                price_max=filters_dict.get('price_range', (None, None))[1],
                categories=[filters_dict['category']] if filters_dict.get('category') else None
            )
            search_results = search_engine.search(query)
        elif request.search_type == "image" and request.image_query:
            # For image search, we need to generate image embedding first
            query = SearchQuery(
                image_embedding=None,  # Would generate from request.image_query
                limit=request.limit,
                similarity_threshold=request.min_similarity,
                brand=filters_dict.get('brand'),
                price_min=filters_dict.get('price_range', (None, None))[0],
                price_max=filters_dict.get('price_range', (None, None))[1],
                categories=[filters_dict['category']] if filters_dict.get('category') else None
            )
            search_results = search_engine.search(query)
        elif request.search_type == "hybrid":
            # Hybrid search with both text and image if available
            query = SearchQuery(
                text_embedding=None,  # Would generate from request.text_query if provided
                image_embedding=None,  # Would generate from request.image_query if provided
                limit=request.limit,
                similarity_threshold=request.min_similarity,
                brand=filters_dict.get('brand'),
                price_min=filters_dict.get('price_range', (None, None))[0],
                price_max=filters_dict.get('price_range', (None, None))[1],
                categories=[filters_dict['category']] if filters_dict.get('category') else None
            )
            search_results = search_engine.search(query)
        else:
            raise HTTPException(status_code=400, detail="Invalid search configuration")

        # Convert SearchResult objects to dict format for response
        results = []
        for search_result in search_results:
            result_dict = {
                'garment': search_result.garment,
                'similarity_score': search_result.similarity_score,
                'match_reason': search_result.match_type
            }
            results.append(result_dict)

        # Convert results to response format
        garment_responses = []
        for result in results:
            garment_response = GarmentResponse(
                id=result['garment'].id,
                external_id=result['garment'].external_id,
                title=result['garment'].title,
                brand=result['garment'].brand,
                price=result['garment'].price,
                currency=result['garment'].currency,
                image_path=result['garment'].image_path,
                description=result['garment'].description,
                category=result['garment'].category,
                subcategory=result['garment'].subcategory,
                primary_color=result['garment'].primary_color,
                secondary_color=result['garment'].secondary_color,
                material=result['garment'].material,
                style=result['garment'].style,
                fit=result['garment'].fit,
                season=result['garment'].season,
                occasion=result['garment'].occasion,
                designer_tier=result['garment'].designer_tier,
                ontology_confidence=result['garment'].ontology_confidence,
                similarity_score=result.get('similarity_score'),
                match_reason=result.get('match_reason')
            )
            garment_responses.append(garment_response)

        end_time = datetime.now()
        search_time_ms = (end_time - start_time).total_seconds() * 1000

        return SearchResponse(
            results=garment_responses,
            total_found=len(results),
            search_time_ms=search_time_ms,
            filters_applied=filters_dict,
            search_metadata={
                'search_type': request.search_type,
                'has_text_query': bool(request.text_query),
                'has_image_query': bool(request.image_query),
                'min_similarity': request.min_similarity
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/api/v2/garments/{garment_id}", response_model=GarmentResponse)
async def get_garment(
    garment_id: int,
    session: Session = Depends(get_db_session)
) -> GarmentResponse:
    """Get detailed garment information with ontology properties."""
    garment = session.get(Garment, garment_id)
    if not garment:
        raise HTTPException(status_code=404, detail="Garment not found")

    return GarmentResponse(
        id=garment.id,
        external_id=garment.external_id,
        title=garment.title,
        brand=garment.brand,
        price=garment.price,
        currency=garment.currency,
        image_path=garment.image_path,
        description=garment.description,
        category=garment.category,
        subcategory=garment.subcategory,
        primary_color=garment.primary_color,
        secondary_color=garment.secondary_color,
        material=garment.material,
        style=garment.style,
        fit=garment.fit,
        season=garment.season,
        occasion=garment.occasion,
        designer_tier=garment.designer_tier,
        ontology_confidence=garment.ontology_confidence
    )

@app.get("/api/v2/garments/{garment_id}/similar")
async def find_similar_garments(
    garment_id: int,
    limit: int = Query(10, ge=1, le=50),
    min_similarity: float = Query(0.7, ge=0.0, le=1.0),
    search_engine: HybridSearchEngine = Depends(get_search_engine)
) -> SearchResponse:
    """Find visually similar garments using CLIP embeddings."""
    start_time = datetime.now()

    try:
        results = search_engine.similar_garments(
            garment_id=garment_id,
            limit=limit
        )

        garment_responses = [
            GarmentResponse(
                id=result.garment.id,
                external_id=result.garment.external_id,
                title=result.garment.title,
                brand=result.garment.brand,
                price=result.garment.price,
                currency=result.garment.currency,
                image_path=result.garment.image_path,
                description=result.garment.description,
                category=result.garment.category,
                subcategory=result.garment.subcategory,
                primary_color=result.garment.primary_color,
                secondary_color=result.garment.secondary_color,
                material=result.garment.material,
                style=result.garment.style,
                fit=result.garment.fit,
                season=result.garment.season,
                occasion=result.garment.occasion,
                designer_tier=result.garment.designer_tier,
                ontology_confidence=result.garment.ontology_confidence,
                similarity_score=result.similarity_score
            )
            for result in results
        ]

        end_time = datetime.now()
        search_time_ms = (end_time - start_time).total_seconds() * 1000

        return SearchResponse(
            results=garment_responses,
            total_found=len(results),
            search_time_ms=search_time_ms,
            filters_applied={},
            search_metadata={
                'search_type': 'similarity',
                'reference_garment_id': garment_id,
                'min_similarity': min_similarity
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similarity search failed: {str(e)}")

@app.post("/api/v2/garments/{garment_id}/extract-properties")
async def extract_garment_properties(
    garment_id: int,
    force_reextract: bool = Query(False),
    session: Session = Depends(get_db_session),
    ontology_service: OntologyExtractionService = Depends(get_ontology_service)
) -> Dict[str, Any]:
    """Extract and update ontology properties for a garment."""
    garment = session.get(Garment, garment_id)
    if not garment:
        raise HTTPException(status_code=404, detail="Garment not found")

    try:
        success = ontology_service.extract_properties(
            garment=garment,
            session=session,
            force_reextract=force_reextract
        )

        if success:
            return {
                "success": True,
                "garment_id": garment_id,
                "properties_extracted": {
                    "category": garment.category,
                    "subcategory": garment.subcategory,
                    "primary_color": garment.primary_color,
                    "material": garment.material,
                    "style": garment.style,
                    "designer_tier": garment.designer_tier,
                    "ontology_confidence": garment.ontology_confidence
                },
                "extracted_at": garment.properties_extracted_at.isoformat() if garment.properties_extracted_at else None
            }
        else:
            raise HTTPException(status_code=500, detail="Property extraction failed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Property extraction failed: {str(e)}")

@app.get("/api/v2/filters/options")
async def get_filter_options(
    session: Session = Depends(get_db_session)
) -> Dict[str, List[str]]:
    """Get available filter options from existing garment data."""
    try:
        # Query distinct values for each ontology property
        filter_options = {}

        # Categories
        categories = session.query(Garment.category).distinct().filter(Garment.category.isnot(None)).all()
        filter_options['categories'] = sorted([c[0] for c in categories])

        # Colors
        colors = session.query(Garment.primary_color).distinct().filter(Garment.primary_color.isnot(None)).all()
        filter_options['colors'] = sorted([c[0] for c in colors])

        # Materials
        materials = session.query(Garment.material).distinct().filter(Garment.material.isnot(None)).all()
        filter_options['materials'] = sorted([m[0] for m in materials])

        # Brands
        brands = session.query(Garment.brand).distinct().filter(Garment.brand.isnot(None)).all()
        filter_options['brands'] = sorted([b[0] for b in brands])

        # Styles
        styles = session.query(Garment.style).distinct().filter(Garment.style.isnot(None)).all()
        filter_options['styles'] = sorted([s[0] for s in styles])

        # Designer tiers
        tiers = session.query(Garment.designer_tier).distinct().filter(Garment.designer_tier.isnot(None)).all()
        filter_options['designer_tiers'] = sorted([t[0] for t in tiers])

        return filter_options

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get filter options: {str(e)}")

@app.get("/api/v2/stats")
async def get_system_stats(
    session: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """Get system statistics and health metrics."""
    try:
        # Count garments with different embedding types
        total_garments = session.query(Garment).count()
        with_clip_embeddings = session.query(Garment).filter(Garment.image_embedding_vec.isnot(None)).count()
        with_openai_embeddings = session.query(Garment).filter(Garment.openai_text_embedding_vec.isnot(None)).count()
        with_properties = session.query(Garment).filter(Garment.properties_extracted_at.isnot(None)).count()

        # Calculate coverage percentages
        clip_coverage = (with_clip_embeddings / total_garments * 100) if total_garments > 0 else 0
        openai_coverage = (with_openai_embeddings / total_garments * 100) if total_garments > 0 else 0
        properties_coverage = (with_properties / total_garments * 100) if total_garments > 0 else 0

        return {
            "total_garments": total_garments,
            "embedding_coverage": {
                "clip_embeddings": {
                    "count": with_clip_embeddings,
                    "percentage": round(clip_coverage, 1)
                },
                "openai_embeddings": {
                    "count": with_openai_embeddings,
                    "percentage": round(openai_coverage, 1)
                }
            },
            "ontology_coverage": {
                "properties_extracted": {
                    "count": with_properties,
                    "percentage": round(properties_coverage, 1)
                }
            },
            "system_version": "2.0.0",
            "capabilities": [
                "CLIP visual embeddings",
                "OpenAI text embeddings",
                "Hybrid vector search",
                "Ontology property extraction",
                "HNSW indexing"
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system stats: {str(e)}")

# Example usage client code
"""
import requests

# Enhanced search example
search_request = {
    "text_query": "vintage blue denim jacket",
    "filters": {
        "category": "outerwear",
        "price_min": 50,
        "price_max": 200,
        "designer_tier": "premium"
    },
    "search_type": "hybrid",
    "limit": 20,
    "min_similarity": 0.75
}

response = requests.post("http://localhost:8000/api/v2/search", json=search_request)
results = response.json()

print(f"Found {results['total_found']} garments in {results['search_time_ms']:.1f}ms")
for garment in results['results']:
    print(f"- {garment['title']} by {garment['brand']} "
          f"({garment['category']}/{garment['subcategory']}) "
          f"- Similarity: {garment['similarity_score']:.2f}")
"""
