#!/usr/bin/env python3
"""
Demo Data Setup Script for Prethrift v2.0

This script populates the database with demo garments from the design folder,
processes them through the enhanced ontology extraction pipeline, and generates
CLIP embeddings for visual search demonstrations.

Usage:
    python setup_demo_data.py
    python setup_demo_data.py --reset-db
    python setup_demo_data.py --verbose --include-embeddings
"""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

# Add app modules to path
sys.path.append(str(Path(__file__).parent.parent / "app"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db_models import Base, Garment
from app.local_cv import LocalGarmentAnalyzer
from app.ontology_extraction import OntologyExtractionService
from app.vector_utils import migrate_json_to_vector

# Configuration
DESIGN_IMAGES_PATH = Path(__file__).parent.parent / "design" / "images"
DESIGN_TEXT_PATH = Path(__file__).parent.parent / "design" / "text"
DATABASE_URL = "postgresql://localhost/prethrift_dev"

class DemoDataSetup:
    """Sets up comprehensive demo data for v2.0 search demonstrations."""

    def __init__(self, database_url: str = DATABASE_URL):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Initialize services
        self.ontology_service = OntologyExtractionService()
        self.clip_analyzer = None

        try:
            self.clip_analyzer = LocalGarmentAnalyzer()
            print("✅ CLIP analyzer initialized")
        except Exception as e:
            print(f"⚠️  CLIP analyzer not available: {e}")

        # Demo garment definitions
        self.demo_garments = self._define_demo_garments()

    def _define_demo_garments(self) -> Dict[str, Dict]:
        """Define demo garment data with rich metadata."""
        return {
            "baggy_jeans": {
                "title": "Wide-Leg Star Appliqué Jeans",
                "brand": "Vintage Denim Co",
                "price": 45.00,
                "size": "M",
                "condition": "Good",
                "image_filename": "baggy-jeans.jpeg",
                "description_file": "baggy-jeans.txt",
                "metadata": {
                    "upload_date": "2024-01-15",
                    "seller": "VintageCollector",
                    "location": "San Francisco, CA",
                    "views": 127,
                    "likes": 23
                }
            },
            "blue_black_pattern_dress": {
                "title": "Geometric Pattern A-Line Dress",
                "brand": "Boho Chic",
                "price": 32.00,
                "size": "S",
                "condition": "Excellent",
                "image_filename": "blue-black-pattern-dress.jpeg",
                "description_file": "blue-black-pattern-dress.txt",
                "metadata": {
                    "upload_date": "2024-01-18",
                    "seller": "BohemianStyle",
                    "location": "Austin, TX",
                    "views": 89,
                    "likes": 15
                }
            },
            "blue_flower_dress": {
                "title": "Blue Floral Summer Dress",
                "brand": "Garden Party",
                "price": 28.00,
                "size": "M",
                "condition": "Very Good",
                "image_filename": "blue-flower-dress.jpeg",
                "description_file": "blue-flower-dress.txt",
                "metadata": {
                    "upload_date": "2024-01-20",
                    "seller": "SpringWardrobe",
                    "location": "Portland, OR",
                    "views": 156,
                    "likes": 31
                }
            },
            "flat_mars_shirt": {
                "title": "Flat Mars Graphic Shirt",
                "brand": "Space Cadet",
                "price": 22.00,
                "size": "L",
                "condition": "Good",
                "image_filename": "flat-mars-shirt.jpeg",
                "description_file": "flat-mars-shirt.txt",
                "metadata": {
                    "upload_date": "2024-01-22",
                    "seller": "SciFiTees",
                    "location": "Seattle, WA",
                    "views": 67,
                    "likes": 12
                }
            },
            "orange_pattern_dress": {
                "title": "Orange Floral Pattern Dress",
                "brand": "Sunset Styles",
                "price": 35.00,
                "size": "S",
                "condition": "Excellent",
                "image_filename": "orange-pattern-dress.jpeg",
                "description_file": "orange-pattern-dress.txt",
                "metadata": {
                    "upload_date": "2024-01-25",
                    "seller": "SummerVibes",
                    "location": "Miami, FL",
                    "views": 198,
                    "likes": 42
                }
            },
            "queen_tshirt": {
                "title": "QUEEN Eagle Graphic Tee",
                "brand": "Rock Heritage",
                "price": 18.00,
                "size": "M",
                "condition": "Very Good",
                "image_filename": "queen-tshirt.jpeg",
                "description_file": "queen-tshirt.txt",
                "metadata": {
                    "upload_date": "2024-01-28",
                    "seller": "ClassicRock",
                    "location": "Nashville, TN",
                    "views": 245,
                    "likes": 67
                }
            },
            "test_blue_grey_shirts": {
                "title": "Blue and Grey Casual Shirts Set",
                "brand": "Everyday Essentials",
                "price": 25.00,
                "size": "L",
                "condition": "Good",
                "image_filename": "test-blue-and-grey-shirts.jpg",
                "description_file": None,  # No description file available
                "description_override": "Two casual shirts in blue and grey colors. Perfect for everyday wear, made from comfortable cotton blend. Relaxed fit suitable for casual occasions.",
                "metadata": {
                    "upload_date": "2024-01-30",
                    "seller": "CasualCloset",
                    "location": "Denver, CO",
                    "views": 78,
                    "likes": 9
                }
            }
        }

    async def reset_database(self):
        """Reset database and create fresh tables."""
        print("🗑️  Resetting database...")

        # Drop all tables
        with self.engine.begin() as conn:
            # Drop tables in reverse dependency order
            conn.execute(text("DROP TABLE IF EXISTS garments CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            print("  ✅ Dropped existing tables")

        # Create all tables
        Base.metadata.create_all(self.engine)
        print("  ✅ Created fresh tables")

    async def load_descriptions(self) -> Dict[str, str]:
        """Load text descriptions from design/text folder."""
        descriptions = {}

        for garment_id, garment_data in self.demo_garments.items():
            description_file = garment_data.get("description_file")

            if description_file:
                description_path = DESIGN_TEXT_PATH / description_file
                try:
                    with open(description_path, encoding='utf-8') as f:
                        descriptions[garment_id] = f.read().strip()
                    print(f"  ✅ Loaded description: {description_file}")
                except FileNotFoundError:
                    print(f"  ⚠️  Description file not found: {description_path}")
                    descriptions[garment_id] = f"Demo {garment_data['title']}"
            else:
                # Use override description if provided
                descriptions[garment_id] = garment_data.get("description_override", f"Demo {garment_data['title']}")
                print(f"  ✅ Using override description for: {garment_id}")

        return descriptions

    async def extract_ontology_properties(self, descriptions: Dict[str, str]) -> Dict[str, Dict]:
        """Extract ontology properties from descriptions."""
        print("\n🏷️  Extracting ontology properties...")

        ontology_results = {}

        for garment_id, description in descriptions.items():
            print(f"  🔍 Processing: {garment_id}")

            # Extract properties using ontology service
            from app.ontology import attribute_confidences, classify_basic_cached

            raw_attributes = classify_basic_cached(description)
            confidence_scores = attribute_confidences(description, raw_attributes)

            # Convert to structured format
            extracted_properties = {}
            for family, values in raw_attributes.items():
                if values:
                    best_value = max(values, key=lambda v: confidence_scores.get((family, v), 0))
                    confidence = confidence_scores.get((family, best_value), 0)

                    if confidence > 0.3:  # Only include confident predictions
                        extracted_properties[family] = best_value

            print(f"    📊 Extracted {len(extracted_properties)} properties")
            ontology_results[garment_id] = extracted_properties

        return ontology_results

    async def generate_image_embeddings(self) -> Dict[str, Optional[np.ndarray]]:
        """Generate CLIP embeddings for images."""
        print("\n🖼️  Generating CLIP embeddings...")

        if not self.clip_analyzer:
            print("  ❌ CLIP analyzer not available - skipping embeddings")
            return {}

        embeddings = {}

        for garment_id, garment_data in self.demo_garments.items():
            image_filename = garment_data["image_filename"]
            image_path = DESIGN_IMAGES_PATH / image_filename

            print(f"  🔍 Processing: {image_filename}")

            if image_path.exists():
                try:
                    with Image.open(image_path) as img:
                        embedding = self.clip_analyzer.get_image_embedding(img)
                    embeddings[garment_id] = embedding
                    print(f"    ✅ Generated embedding (length: {len(embedding) if embedding is not None else 'None'})")
                except Exception as e:
                    print(f"    ❌ Error generating embedding: {e}")
                    embeddings[garment_id] = None
            else:
                print(f"    ⚠️  Image file not found: {image_path}")
                embeddings[garment_id] = None

        return embeddings

    async def create_garment_records(self, descriptions: Dict[str, str],
                                   ontology_data: Dict[str, Dict],
                                   embeddings: Dict[str, Optional[np.ndarray]]) -> List[Garment]:
        """Create Garment database records."""
        print("\n💾 Creating garment records...")

        garments = []

        with self.SessionLocal() as session:
            for garment_id, garment_data in self.demo_garments.items():
                print(f"  🔍 Creating: {garment_data['title']}")

                # Check if garment already exists
                external_id = f"demo_{garment_id}"
                existing_garment = session.query(Garment).filter(Garment.external_id == external_id).first()

                if existing_garment:
                    print(f"    ⚠️  Garment already exists, skipping: {external_id}")
                    garments.append(existing_garment)
                    continue

                # Get extracted properties
                properties = ontology_data.get(garment_id, {})

                # Create garment record
                garment = Garment(
                    external_id=f"demo_{garment_id}",
                    title=garment_data["title"],
                    description=descriptions.get(garment_id, ""),
                    brand=garment_data.get("brand"),
                    price=garment_data.get("price"),
                    size=garment_data.get("size"),
                    condition=garment_data.get("condition"),

                    # Extracted ontology properties
                    category=properties.get("category"),
                    subcategory=properties.get("subcategory"),
                    primary_color=properties.get("primary_color"),
                    secondary_color=properties.get("secondary_color"),
                    material=properties.get("material"),
                    pattern=properties.get("pattern"),
                    style=properties.get("style"),
                    fit=properties.get("fit"),
                    occasion=properties.get("occasion"),
                    season=properties.get("season"),
                    gender=properties.get("gender"),
                    era=properties.get("era"),

                    # Image info
                    image_path=f"/images/{garment_data['image_filename']}",

                    # Metadata
                    created_at=datetime.fromisoformat(garment_data["metadata"]["upload_date"])
                )

                # Add CLIP embedding if available
                embedding = embeddings.get(garment_id)
                if embedding is not None:
                    # Convert numpy array to list if needed
                    if hasattr(embedding, 'tolist'):
                        embedding_list = embedding.tolist()
                    else:
                        embedding_list = list(embedding)
                    # Store in both legacy JSON and vector columns
                    garment.image_embedding = embedding_list
                    garment.image_embedding_vec = migrate_json_to_vector(embedding_list)

                session.add(garment)
                garments.append(garment)

                print(f"    ✅ Created with {len(properties)} properties")
                if embedding is not None:
                    print("    🧠 Added CLIP embedding")

            session.commit()
            print(f"  💾 Saved {len(garments)} garments to database")

        return garments

    async def validate_demo_data(self):
        """Validate that demo data was created correctly."""
        print("\n✅ Validating demo data...")

        with self.SessionLocal() as session:
            total_garments = session.query(Garment).count()
            print(f"  📊 Total garments in database: {total_garments}")

            # Check for ontology properties
            garments_with_category = session.query(Garment).filter(Garment.category.isnot(None)).count()
            garments_with_color = session.query(Garment).filter(Garment.primary_color.isnot(None)).count()
            garments_with_embeddings = session.query(Garment).filter(Garment.image_embedding.isnot(None)).count()

            print(f"  🏷️  Garments with category: {garments_with_category}")
            print(f"  🎨 Garments with color: {garments_with_color}")
            print(f"  🧠 Garments with embeddings: {garments_with_embeddings}")

            # Sample property distribution
            categories = session.query(Garment.category).filter(Garment.category.isnot(None)).distinct().all()
            colors = session.query(Garment.primary_color).filter(Garment.primary_color.isnot(None)).distinct().all()

            print(f"  📈 Categories found: {[c[0] for c in categories]}")
            print(f"  🌈 Colors found: {[c[0] for c in colors]}")

            # Check specific examples
            sample_garments = session.query(Garment).limit(3).all()
            for garment in sample_garments:
                print(f"  🔍 Sample: {garment.title}")
                print(f"    Category: {garment.category}, Color: {garment.primary_color}")
                print(f"    Has embedding: {'✅' if garment.image_embedding else '❌'}")

    async def generate_search_examples(self):
        """Generate example search queries for testing."""
        print("\n📝 Generating search examples...")

        examples = {
            "text_searches": [
                "blue denim jeans with stars",
                "geometric pattern dress bohemian",
                "queen graphic tee cream colored",
                "orange floral summer dress",
                "mars space graphic shirt",
                "blue flower spring dress"
            ],
            "filter_combinations": [
                {"category": "dresses", "season": "summer"},
                {"primary_color": "blue", "style": "casual"},
                {"category": "tops", "style": "graphic"},
                {"pattern": "floral", "season": "spring"},
                {"material": "denim", "fit": "relaxed"}
            ],
            "similarity_searches": [
                "Find items similar to the blue pattern dress",
                "Show me clothes like the QUEEN t-shirt",
                "Similar to the wide-leg jeans",
                "More dresses like the orange floral one"
            ]
        }

        # Save examples to file
        examples_file = Path(__file__).parent / "demo_search_examples.json"
        with open(examples_file, 'w') as f:
            json.dump(examples, f, indent=2)

        print(f"  💾 Saved search examples to: {examples_file}")
        print(f"  📝 Generated {len(examples['text_searches'])} text search examples")
        print(f"  🔍 Generated {len(examples['filter_combinations'])} filter combinations")
        print(f"  👀 Generated {len(examples['similarity_searches'])} similarity searches")

        return examples

    async def setup_full_demo_data(self, reset_db: bool = False, include_embeddings: bool = True):
        """Set up complete demo data pipeline."""
        print("🚀 SETTING UP PRETHRIFT V2.0 DEMO DATA")
        print("=" * 60)
        print(f"🕐 Setup started at: {datetime.now(UTC).isoformat()}")

        if reset_db:
            await self.reset_database()

        # Load and process data
        print(f"\n📂 Loading data from: {DESIGN_IMAGES_PATH}")
        descriptions = await self.load_descriptions()

        ontology_data = await self.extract_ontology_properties(descriptions)

        embeddings = {}
        if include_embeddings:
            embeddings = await self.generate_image_embeddings()
        else:
            print("\n⏭️  Skipping CLIP embeddings (--no-embeddings)")

        # Create database records
        garments = await self.create_garment_records(descriptions, ontology_data, embeddings)

        # Validate and generate examples
        await self.validate_demo_data()
        search_examples = await self.generate_search_examples()

        # Summary
        print("\n📊 SETUP SUMMARY")
        print("=" * 40)
        print(f"✅ Demo garments created: {len(garments)}")
        print(f"🏷️  Ontology properties extracted: {sum(len(props) for props in ontology_data.values())}")
        if include_embeddings:
            embeddings_count = sum(1 for emb in embeddings.values() if emb is not None)
            print(f"🧠 CLIP embeddings generated: {embeddings_count}/{len(embeddings)}")
        print(f"📝 Search examples generated: {len(search_examples['text_searches'])}")

        print("\n🎯 Ready for demonstrations!")
        print("Next steps:")
        print("  1. Run backend demo: python demo/demo_enhanced_search.py")
        print("  2. Run frontend demo: node demo_frontend_integration.js")
        print("  3. Start the API server: uvicorn app.main:app --reload")
        print("  4. Start the frontend: cd frontend/web && npm run dev")

        return {
            "garments_created": len(garments),
            "ontology_properties": ontology_data,
            "embeddings_generated": len([e for e in embeddings.values() if e is not None]),
            "search_examples": search_examples
        }


async def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description="Setup Prethrift v2.0 Demo Data")
    parser.add_argument("--reset-db", action="store_true", help="Reset database before setup")
    parser.add_argument("--no-embeddings", action="store_true", help="Skip CLIP embedding generation")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--database-url", default=DATABASE_URL, help="Database URL")

    args = parser.parse_args()

    try:
        setup = DemoDataSetup(args.database_url)

        result = await setup.setup_full_demo_data(
            reset_db=args.reset_db,
            include_embeddings=not args.no_embeddings
        )

        if args.verbose:
            print(f"\n📄 Setup Results:\n{json.dumps(result, indent=2, default=str)}")

        print("\n✅ Demo data setup completed successfully!")

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
