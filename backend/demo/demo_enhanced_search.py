#!/usr/bin/env python3
"""
Prethrift v2.0 Search Demonstration Script

This script demonstrates the enhanced search capabilities using real design assets
from the design/images and design/text folders. It showcases:

1. Multi-modal search (text, image, hybrid)
2. Ontology-based property extraction and filtering
3. CLIP visual embeddings for similarity search
4. Rich metadata search and faceted filtering
5. Performance comparisons between legacy and v2.0 search

Usage:
    python demo_enhanced_search.py
    python demo_enhanced_search.py --test-case similarity
    python demo_enhanced_search.py --verbose --export-results
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).parent.parent / "app"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db_models import Garment
from app.hybrid_search import HybridSearchEngine, SearchQuery
from app.local_cv import LocalGarmentAnalyzer
from app.ontology_extraction import OntologyExtractionService

# Demo configuration
DESIGN_IMAGES_PATH = Path(__file__).parent / "design" / "images"
DESIGN_TEXT_PATH = Path(__file__).parent / "design" / "text"
DATABASE_URL = "postgresql://localhost/prethrift_dev"


class SearchDemoRunner:
    """Demonstrates enhanced search capabilities with real examples."""

    def __init__(self, database_url: str = DATABASE_URL):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Initialize services
        self.search_engine = None
        self.ontology_service = OntologyExtractionService()
        self.clip_analyzer = None
        self._initialize_services()

        # Demo data
        self.demo_garments = self._load_demo_data()

    def _initialize_services(self):
        """Initialize search and analysis services."""
        try:
            self.clip_analyzer = LocalGarmentAnalyzer()
            print("✅ CLIP analyzer initialized")
        except Exception as e:
            print(f"⚠️  CLIP analyzer not available: {e}")

        with self.SessionLocal() as session:
            self.search_engine = HybridSearchEngine(session)
            print("✅ Hybrid search engine initialized")

    def _load_demo_data(self) -> dict[str, dict]:
        """Load demo garment data from design folder."""
        demo_items = {
            "baggy_jeans": {
                "title": "Wide-Leg Star Appliqué Jeans",
                "image_path": DESIGN_IMAGES_PATH / "baggy-jeans.jpeg",
                "description_file": DESIGN_TEXT_PATH / "baggy-jeans.txt",
                "expected_properties": {
                    "category": "bottoms",
                    "subcategory": "jeans",
                    "primary_color": "blue",
                    "style": "wide-leg",
                    "fit": "relaxed",
                    "season": "spring",
                    "occasion": "casual",
                },
            },
            "pattern_dress": {
                "title": "Geometric Pattern A-Line Dress",
                "image_path": DESIGN_IMAGES_PATH / "blue-black-pattern-dress.jpeg",
                "description_file": DESIGN_TEXT_PATH / "blue-black-pattern-dress.txt",
                "expected_properties": {
                    "category": "dresses",
                    "subcategory": "a-line",
                    "primary_color": "blue",
                    "secondary_color": "red",
                    "pattern": "geometric",
                    "style": "bohemian",
                    "season": "summer",
                    "occasion": "casual",
                },
            },
            "queen_tshirt": {
                "title": "QUEEN Eagle Graphic Tee",
                "image_path": DESIGN_IMAGES_PATH / "queen-tshirt.jpeg",
                "description_file": DESIGN_TEXT_PATH / "queen-tshirt.txt",
                "expected_properties": {
                    "category": "tops",
                    "subcategory": "t-shirt",
                    "primary_color": "cream",
                    "style": "graphic",
                    "fit": "relaxed",
                    "season": "summer",
                    "occasion": "casual",
                },
            },
            "orange_dress": {
                "title": "Orange Pattern Dress",
                "image_path": DESIGN_IMAGES_PATH / "orange-pattern-dress.jpeg",
                "description_file": DESIGN_TEXT_PATH / "orange-pattern-dress.txt",
                "expected_properties": {
                    "category": "dresses",
                    "primary_color": "orange",
                    "pattern": "floral",
                    "season": "summer",
                    "occasion": "casual",
                },
            },
            "mars_shirt": {
                "title": "Flat Mars Graphic Shirt",
                "image_path": DESIGN_IMAGES_PATH / "flat-mars-shirt.jpeg",
                "description_file": DESIGN_TEXT_PATH / "flat-mars-shirt.txt",
                "expected_properties": {
                    "category": "tops",
                    "subcategory": "shirt",
                    "style": "graphic",
                    "occasion": "casual",
                },
            },
        }

        # Load descriptions
        for item_id, item_data in demo_items.items():
            try:
                with open(item_data["description_file"]) as f:
                    item_data["description"] = f.read().strip()
            except FileNotFoundError:
                print(f"⚠️  Description file not found: {item_data['description_file']}")
                item_data["description"] = f"Demo {item_data['title']}"

        return demo_items

    async def demo_text_search(self) -> dict[str, Any]:
        """Demonstrate enhanced text search capabilities."""
        print("\n🔍 DEMO: Enhanced Text Search")
        print("=" * 50)

        test_queries = [
            "blue wide leg jeans with stars",
            "colorful geometric pattern dress",
            "cream graphic t-shirt with eagles",
            "orange summer dress",
            "casual graphic shirt",
        ]

        results = {}

        for query in test_queries:
            print(f"\n📝 Query: '{query}'")
            start_time = time.time()

            # Create search query with ontology enhancement
            search_query = SearchQuery(
                text_embedding=None,  # Would be generated from OpenAI in real implementation
                similarity_threshold=0.6,
                limit=10,
            )

            with self.SessionLocal() as session:
                search_engine = HybridSearchEngine(session)

                # Simulate text embedding search by using description matching
                matching_garments = []
                for garment in session.query(Garment).all():
                    if garment.description:
                        # Simple keyword matching for demo
                        query_words = query.lower().split()
                        desc_words = garment.description.lower().split()
                        matches = sum(
                            1
                            for word in query_words
                            if any(word in desc_word for desc_word in desc_words)
                        )

                        if matches > 0:
                            confidence = matches / len(query_words)
                            matching_garments.append((garment, confidence))

                # Sort by confidence
                matching_garments.sort(key=lambda x: x[1], reverse=True)

                search_time = (time.time() - start_time) * 1000

                print(f"⏱️  Search time: {search_time:.1f}ms")
                print(f"📊 Results: {len(matching_garments)} matches")

                # Show top results
                for i, (garment, confidence) in enumerate(matching_garments[:3]):
                    print(f"  {i + 1}. {garment.title or 'Unknown'} (confidence: {confidence:.2f})")
                    if hasattr(garment, "category") and garment.category:
                        print(f"      Category: {garment.category}")
                    if hasattr(garment, "primary_color") and garment.primary_color:
                        print(f"      Color: {garment.primary_color}")

                results[query] = {
                    "matches": len(matching_garments),
                    "search_time_ms": search_time,
                    "top_results": [
                        {
                            "title": g.title,
                            "confidence": conf,
                            "category": getattr(g, "category", None),
                            "color": getattr(g, "primary_color", None),
                        }
                        for g, conf in matching_garments[:3]
                    ],
                }

        return results

    async def demo_visual_similarity(self) -> dict[str, Any]:
        """Demonstrate CLIP-based visual similarity search."""
        print("\n🖼️  DEMO: Visual Similarity Search")
        print("=" * 50)

        if not self.clip_analyzer:
            print("❌ CLIP analyzer not available - skipping visual demo")
            return {}

        results = {}

        # Test similarity between different garment types
        test_pairs = [
            ("baggy_jeans", "pattern_dress", "Different categories"),
            ("pattern_dress", "orange_dress", "Same category (dresses)"),
            ("queen_tshirt", "mars_shirt", "Same category (tops)"),
        ]

        with self.SessionLocal() as session:
            for item1_id, item2_id, comparison_type in test_pairs:
                print(f"\n🔄 Comparing: {comparison_type}")

                item1 = self.demo_garments[item1_id]
                item2 = self.demo_garments[item2_id]

                print(f"  📷 {item1['title']} vs {item2['title']}")

                try:
                    # Generate embeddings for both images
                    if item1["image_path"].exists() and item2["image_path"].exists():
                        emb1 = self.clip_analyzer.get_image_embedding(str(item1["image_path"]))
                        emb2 = self.clip_analyzer.get_image_embedding(str(item2["image_path"]))

                        if emb1 is not None and emb2 is not None:
                            # Calculate cosine similarity
                            import numpy as np

                            similarity = np.dot(emb1, emb2) / (
                                np.linalg.norm(emb1) * np.linalg.norm(emb2)
                            )

                            print(f"  📊 Visual similarity: {similarity:.3f}")

                            # Interpret similarity
                            if similarity > 0.8:
                                interpretation = "Very similar"
                            elif similarity > 0.6:
                                interpretation = "Moderately similar"
                            elif similarity > 0.4:
                                interpretation = "Somewhat similar"
                            else:
                                interpretation = "Not similar"

                            print(f"  💭 Interpretation: {interpretation}")

                            results[f"{item1_id}_vs_{item2_id}"] = {
                                "similarity_score": float(similarity),
                                "interpretation": interpretation,
                                "comparison_type": comparison_type,
                            }

                except Exception as e:
                    print(f"  ❌ Error computing similarity: {e}")

        return results

    async def demo_ontology_extraction(self) -> dict[str, Any]:
        """Demonstrate ontology-based property extraction."""
        print("\n🏷️  DEMO: Ontology Property Extraction")
        print("=" * 50)

        results = {}

        for item_id, item_data in self.demo_garments.items():
            print(f"\n📝 Analyzing: {item_data['title']}")

            # Extract properties from description
            from app.ontology import attribute_confidences, classify_basic_cached

            description = item_data["description"]
            raw_attributes = classify_basic_cached(description)
            confidence_scores = attribute_confidences(description, raw_attributes)

            # Convert to structured format
            extracted_properties = {}
            for family, values in raw_attributes.items():
                if values:
                    best_value = max(values, key=lambda v: confidence_scores.get((family, v), 0))
                    confidence = confidence_scores.get((family, best_value), 0)
                    extracted_properties[family] = {"value": best_value, "confidence": confidence}

            print(f"  📊 Extracted {len(extracted_properties)} properties:")

            # Compare with expected properties
            expected = item_data["expected_properties"]
            matches = 0
            total_expected = len(expected)

            for prop, expected_value in expected.items():
                extracted = extracted_properties.get(prop)
                if extracted and extracted["value"] == expected_value:
                    print(
                        f"    ✅ {prop}: {extracted['value']} (confidence: {extracted['confidence']:.2f})"
                    )
                    matches += 1
                elif extracted:
                    print(
                        f"    ⚠️  {prop}: got '{extracted['value']}', expected '{expected_value}' (confidence: {extracted['confidence']:.2f})"
                    )
                else:
                    print(f"    ❌ {prop}: not detected (expected '{expected_value}')")

            accuracy = matches / total_expected if total_expected > 0 else 0
            print(f"  🎯 Accuracy: {matches}/{total_expected} ({accuracy:.1%})")

            results[item_id] = {
                "extracted_properties": extracted_properties,
                "expected_properties": expected,
                "accuracy": accuracy,
                "matches": matches,
                "total_expected": total_expected,
            }

        return results

    async def demo_hybrid_search(self) -> dict[str, Any]:
        """Demonstrate hybrid search combining multiple signals."""
        print("\n🔄 DEMO: Hybrid Search (Text + Image + Filters)")
        print("=" * 50)

        results = {}

        # Test scenarios
        test_scenarios = [
            {
                "name": "Find blue casual wear",
                "text_query": "blue casual",
                "filters": {"colors": ["blue"], "categories": ["casual"]},
                "description": "Searching for blue casual items",
            },
            {
                "name": "Summer dresses",
                "text_query": "summer dress",
                "filters": {"categories": ["dress", "dresses"]},
                "description": "Looking for summer dresses",
            },
            {
                "name": "Graphic t-shirts",
                "text_query": "graphic tshirt",
                "filters": {"categories": ["shirt", "top"]},
                "description": "Looking for graphic t-shirts",
            },
        ]

        with self.SessionLocal() as session:
            for scenario in test_scenarios:
                print(f"\n🎯 Scenario: {scenario['name']}")
                print(f"   📝 Query: '{scenario['text_query']}'")
                print(f"   🔍 Filters: {scenario['filters']}")

                start_time = time.time()

                # Create hybrid search query
                search_query = SearchQuery(
                    text_embedding=None,  # Would use OpenAI embeddings
                    **scenario["filters"],
                    limit=20,
                    similarity_threshold=0.5,
                    use_vector_search=False,  # Using metadata for demo
                    combine_scores=True,
                )

                # Execute search using metadata filtering
                search_engine = HybridSearchEngine(session)

                # Build filter conditions
                garments = session.query(Garment)

                for filter_key, filter_value in scenario["filters"].items():
                    if hasattr(Garment, filter_key):
                        column = getattr(Garment, filter_key)
                        garments = garments.filter(column == filter_value)

                # Apply text matching
                if scenario["text_query"]:
                    query_words = scenario["text_query"].lower().split()
                    matching_garments = []

                    for garment in garments.all():
                        if garment.description:
                            desc_words = garment.description.lower()
                            match_score = sum(1 for word in query_words if word in desc_words)
                            if match_score > 0:
                                relevance = match_score / len(query_words)
                                matching_garments.append((garment, relevance))

                    matching_garments.sort(key=lambda x: x[1], reverse=True)
                else:
                    matching_garments = [(g, 1.0) for g in garments.all()]

                search_time = (time.time() - start_time) * 1000

                print(f"   ⏱️  Search time: {search_time:.1f}ms")
                print(f"   📊 Results: {len(matching_garments)} matches")

                # Show results
                for i, (garment, relevance) in enumerate(matching_garments[:3]):
                    print(
                        f"     {i + 1}. {garment.title or 'Unknown'} (relevance: {relevance:.2f})"
                    )

                    properties = []
                    for prop in ["category", "primary_color", "style", "season"]:
                        value = getattr(garment, prop, None)
                        if value:
                            properties.append(f"{prop}: {value}")

                    if properties:
                        print(f"        Properties: {', '.join(properties)}")

                results[scenario["name"]] = {
                    "query": scenario["text_query"],
                    "filters": scenario["filters"],
                    "matches": len(matching_garments),
                    "search_time_ms": search_time,
                    "top_results": [
                        {
                            "title": g.title,
                            "relevance": rel,
                            "properties": {
                                prop: getattr(g, prop, None)
                                for prop in ["category", "primary_color", "style", "season"]
                                if getattr(g, prop, None)
                            },
                        }
                        for g, rel in matching_garments[:3]
                    ],
                }

        return results

    async def demo_performance_comparison(self) -> dict[str, Any]:
        """Compare performance between legacy and v2.0 search."""
        print("\n⚡ DEMO: Performance Comparison")
        print("=" * 50)

        results = {"legacy_search": {}, "v2_search": {}, "performance_gain": {}}

        test_queries = ["blue jeans", "summer dress", "graphic tshirt", "casual wear"]

        with self.SessionLocal() as session:
            for query in test_queries:
                print(f"\n🔍 Testing query: '{query}'")

                # Legacy search simulation (simple text matching)
                start_time = time.time()
                legacy_results = []

                for garment in session.query(Garment).all():
                    if garment.description and query.lower() in garment.description.lower():
                        legacy_results.append(garment)

                legacy_time = (time.time() - start_time) * 1000

                # V2.0 search simulation (with ontology and smart matching)
                start_time = time.time()
                v2_results = []

                # Parse query with ontology
                from app.ontology import classify_basic_cached

                query_attributes = classify_basic_cached(query)

                for garment in session.query(Garment).all():
                    relevance_score = 0

                    # Text matching
                    if garment.description and query.lower() in garment.description.lower():
                        relevance_score += 0.5

                    # Attribute matching
                    for attr_family, attr_values in query_attributes.items():
                        garment_value = getattr(garment, attr_family, None)
                        if garment_value and garment_value in attr_values:
                            relevance_score += 0.3

                    # Category inference
                    if (
                        "jeans" in query
                        and getattr(garment, "category", None) == "bottoms"
                        or "dress" in query
                        and getattr(garment, "category", None) == "dresses"
                        or "tshirt" in query
                        and getattr(garment, "category", None) == "tops"
                    ):
                        relevance_score += 0.2

                    if relevance_score > 0:
                        v2_results.append((garment, relevance_score))

                v2_results.sort(key=lambda x: x[1], reverse=True)
                v2_time = (time.time() - start_time) * 1000

                print(f"  📊 Legacy: {len(legacy_results)} results in {legacy_time:.1f}ms")
                print(f"  🚀 V2.0: {len(v2_results)} results in {v2_time:.1f}ms")

                if legacy_time > 0:
                    speedup = legacy_time / v2_time if v2_time > 0 else float("inf")
                    print(
                        f"  ⚡ Performance: {speedup:.1f}x {'faster' if speedup > 1 else 'slower'}"
                    )

                precision_legacy = len(legacy_results)
                precision_v2 = len([r for r in v2_results if r[1] > 0.5])

                print(
                    f"  🎯 Quality: Legacy={precision_legacy}, V2.0={precision_v2} high-relevance results"
                )

                results["legacy_search"][query] = {
                    "results_count": len(legacy_results),
                    "search_time_ms": legacy_time,
                }

                results["v2_search"][query] = {
                    "results_count": len(v2_results),
                    "high_relevance_count": precision_v2,
                    "search_time_ms": v2_time,
                }

                results["performance_gain"][query] = {
                    "speedup_factor": speedup if legacy_time > 0 else 0,
                    "quality_improvement": precision_v2 - precision_legacy,
                }

        return results

    async def run_full_demo(self, export_results: bool = False) -> dict[str, Any]:
        """Run complete demonstration of all v2.0 features."""
        print("🚀 PRETHRIFT V2.0 SEARCH DEMONSTRATION")
        print("=" * 60)
        print(f"🕐 Demo started at: {datetime.now(UTC).isoformat()}")
        print(f"📂 Using demo data from: {DESIGN_IMAGES_PATH}")
        print(f"📝 Demo garments loaded: {len(self.demo_garments)}")

        full_results = {
            "demo_metadata": {
                "timestamp": datetime.now(UTC).isoformat(),
                "demo_garments_count": len(self.demo_garments),
                "database_url": DATABASE_URL,
            },
            "text_search": await self.demo_text_search(),
            "visual_similarity": await self.demo_visual_similarity(),
            "ontology_extraction": await self.demo_ontology_extraction(),
            "hybrid_search": await self.demo_hybrid_search(),
            "performance_comparison": await self.demo_performance_comparison(),
        }

        # Summary
        print("\n📊 DEMO SUMMARY")
        print("=" * 40)

        ontology_results = full_results["ontology_extraction"]
        if ontology_results:
            avg_accuracy = sum(r["accuracy"] for r in ontology_results.values()) / len(
                ontology_results
            )
            print(f"🏷️  Ontology Extraction Accuracy: {avg_accuracy:.1%}")

        performance_results = full_results["performance_comparison"]
        if performance_results.get("performance_gain"):
            avg_speedup = sum(
                r["speedup_factor"] for r in performance_results["performance_gain"].values()
            ) / len(performance_results["performance_gain"])
            print(f"⚡ Average Performance Gain: {avg_speedup:.1f}x")

        visual_results = full_results["visual_similarity"]
        if visual_results:
            print(f"🖼️  Visual Similarity Tests: {len(visual_results)} comparisons completed")

        if export_results:
            output_file = f"demo_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, "w") as f:
                json.dump(full_results, f, indent=2, default=str)
            print(f"💾 Results exported to: {output_file}")

        print("\n✅ Demo completed successfully!")
        return full_results


async def main():
    """Main demo execution function."""
    parser = argparse.ArgumentParser(description="Prethrift v2.0 Search Demonstration")
    parser.add_argument(
        "--test-case",
        choices=["text", "visual", "ontology", "hybrid", "performance", "all"],
        default="all",
        help="Specific test case to run",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--export-results", action="store_true", help="Export results to JSON file")
    parser.add_argument("--database-url", default=DATABASE_URL, help="Database URL")

    args = parser.parse_args()

    try:
        demo_runner = SearchDemoRunner(args.database_url)

        if args.test_case == "all":
            results = await demo_runner.run_full_demo(args.export_results)
        elif args.test_case == "text":
            results = await demo_runner.demo_text_search()
        elif args.test_case == "visual":
            results = await demo_runner.demo_visual_similarity()
        elif args.test_case == "ontology":
            results = await demo_runner.demo_ontology_extraction()
        elif args.test_case == "hybrid":
            results = await demo_runner.demo_hybrid_search()
        elif args.test_case == "performance":
            results = await demo_runner.demo_performance_comparison()

        if args.verbose:
            print(f"\n📄 Raw Results:\n{json.dumps(results, indent=2, default=str)}")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    import asyncio

    exit_code = asyncio.run(main())
    exit(exit_code)
