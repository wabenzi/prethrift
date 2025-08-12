"""
Simple demonstration of the local CV system working.
"""

import logging
import sys

from PIL import Image

# Set up the path
sys.path.insert(0, "/Users/leonhardt/dev/prethrift/backend")

from app.local_cv import LocalGarmentAnalyzer


def demonstrate_local_cv():
    """Demonstrate the local CV system with sample images."""

    print("🔍 LOCAL COMPUTER VISION DEMONSTRATION")
    print("=" * 50)

    # Initialize the analyzer
    analyzer = LocalGarmentAnalyzer()

    if not analyzer._is_available():
        print("❌ Local CV not available (missing dependencies)")
        return

    print("✅ Local CV system initialized successfully!")
    print(f"Model: {analyzer.model.__class__.__name__ if analyzer.model else 'Unknown'}")
    print(
        f"Processor: {analyzer.processor.__class__.__name__ if analyzer.processor else 'Unknown'}"
    )

    # Test with different colored squares to simulate clothing items
    test_cases = [
        ("Red Garment", Image.new("RGB", (224, 224), color="red")),
        ("Blue Garment", Image.new("RGB", (224, 224), color="blue")),
        ("Green Garment", Image.new("RGB", (224, 224), color="green")),
        ("Black Garment", Image.new("RGB", (224, 224), color="black")),
    ]

    print(f"\n🧥 ANALYZING {len(test_cases)} TEST IMAGES")
    print("-" * 50)

    for i, (name, image) in enumerate(test_cases, 1):
        print(f"\n{i}. {name}:")
        result = analyzer.analyze_image(image)

        # Show garments detected
        garments = result.get("garments", [])
        print(f"   Garments detected: {len(garments)}")

        if garments:
            top_garment = garments[0]
            print(
                f"   Top prediction: {top_garment['name']} (confidence: {top_garment['confidence']:.3f})"
            )

            # Show attributes
            attrs = result.get("attributes", {}).get(top_garment["name"], {})

            colors = attrs.get("colors", [])
            if colors:
                color_str = ", ".join([f"{c['name']} ({c['confidence']:.3f})" for c in colors[:2]])
                print(f"   Colors: {color_str}")

            styles = attrs.get("styles", [])
            if styles:
                style_str = ", ".join([f"{s['name']} ({s['confidence']:.3f})" for s in styles[:1]])
                print(f"   Style: {style_str}")

        # Show description
        description = result.get("description", "No description")
        print(f"   Description: {description}")

        print(f"   Overall confidence: {result.get('confidence', 0):.3f}")

    # Performance information
    print("\n📊 SYSTEM INFORMATION")
    print("-" * 50)
    print("✅ Model loaded: openai/clip-vit-base-patch32")
    print(f"✅ Garment categories: {len(analyzer.GARMENT_CATEGORIES)}")
    print(f"✅ Color categories: {len(analyzer.COLOR_CATEGORIES)}")
    print(f"✅ Style categories: {len(analyzer.STYLE_CATEGORIES)}")
    print(f"✅ Material categories: {len(analyzer.MATERIAL_CATEGORIES)}")

    print("\n🔧 CONFIGURATION")
    print("-" * 50)
    print("To use local CV in production:")
    print("  export USE_LOCAL_CV=true")
    print("")
    print("To use OpenAI GPT-4o-mini:")
    print("  export USE_LOCAL_CV=false")

    print("\n🚀 BENEFITS OF LOCAL CV")
    print("-" * 50)
    print("✅ No API calls or internet required")
    print("✅ Fast processing (no network latency)")
    print("✅ Privacy-focused (data stays local)")
    print("✅ Consistent costs (no per-request charges)")
    print("✅ Detailed attribute analysis")
    print("✅ Confidence scores for all predictions")


if __name__ == "__main__":
    # Set up logging to see what's happening
    logging.basicConfig(level=logging.INFO)

    demonstrate_local_cv()
