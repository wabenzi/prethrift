#!/usr/bin/env python3
"""Test script to demonstrate the enhanced ontology capabilities."""

import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.ontology import classify_basic_cached, all_values

def test_description(description: str):
    """Test a garment description with the enhanced ontology."""
    print(f"\n🔍 Testing: '{description}'")
    print("=" * 60)

    result = classify_basic_cached(description)

    if not result:
        print("❌ No attributes detected")
        return

    for family, values in result.items():
        print(f"📋 {family.upper().replace('_', ' ')}: {', '.join(values)}")

def main():
    """Test various garment descriptions with enhanced ontology."""

    print("🌟 ENHANCED ONTOLOGY TEST")
    print("Testing era, brand, subcategory detection and expanded vocabulary")
    print("=" * 70)

    # Test descriptions with new dimensions
    test_descriptions = [
        # Era testing
        "Vintage 1990s grunge flannel shirt",
        "1950s style circle skirt in navy blue",
        "Y2K millennium silver metallic mini dress",
        "1980s power blazer with shoulder pads",
        "2000s low-rise bootcut jeans",

        # Brand testing
        "Chanel tweed jacket with gold buttons",
        "Levi's 501 vintage denim jeans",
        "Lululemon align yoga leggings in black",
        "Patagonia fleece jacket for hiking",
        "Nike air max sneakers in white",
        "J.Crew silk blouse in navy stripe",

        # Subcategory testing
        "Bodycon mini dress in red sequins",
        "Oversized bomber jacket in olive green",
        "High-waisted wide-leg trousers in wool",
        "Cropped tank top in organic cotton",
        "Platform ankle boots in black leather",
        "Crossbody bag in cognac leather",

        # Material testing
        "Merino wool sweater with cable knit",
        "Bamboo fiber t-shirt in sage green",
        "Recycled polyester puffer coat",
        "Tencel lyocell midi dress with floral print",
        "Vegan leather jacket in dark brown",

        # Complex descriptions
        "Vintage Chanel 1980s black wool bouclé jacket with gold chain trim",
        "Sustainable deadstock denim wide-leg jeans from the 1990s",
        "Luxury cashmere turtleneck sweater in cream by The Row",
        "Athletic moisture-wicking running shorts in neon green",
        "Bohemian 1970s style maxi dress with paisley print in earth tones"
    ]

    for description in test_descriptions:
        test_description(description)

    print("\n📊 ONTOLOGY STATS")
    print("=" * 40)
    ontology = all_values()
    for family, values in ontology.items():
        print(f"{family}: {len(values)} values")

    total_values = sum(len(values) for values in ontology.values())
    print(f"\nTotal vocabulary: {total_values} terms across {len(ontology)} dimensions")

if __name__ == "__main__":
    main()
