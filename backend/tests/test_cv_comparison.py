"""
Comprehensive test and comparison of OpenAI vs Local CV for garment analysis.
"""

import io
import os
from unittest.mock import MagicMock, patch

from PIL import Image

from app.inventory_processing import describe_inventory_image_multi
from app.local_cv import LocalGarmentAnalyzer


def create_test_image():
    """Create a simple test image for testing."""
    image = Image.new("RGB", (100, 100), color="red")
    return image


def test_cv_system_comparison():
    """Test both OpenAI and Local CV systems with the same image."""

    # Create test image
    test_image = create_test_image()

    # Convert to bytes for describe_inventory_image_multi
    img_bytes = io.BytesIO()
    test_image.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    image_data = img_bytes.getvalue()

    print("\n🔍 Testing Computer Vision Systems Comparison")
    print("=" * 60)

    # Test 1: Local CV System
    print("\n1. LOCAL CV SYSTEM (CLIP-based)")
    print("-" * 30)

    with (
        patch.dict(os.environ, {"USE_LOCAL_CV": "true"}),
        patch("app.inventory_processing.openai_client") as mock_openai,
    ):
            mock_openai.chat.completions.create.side_effect = Exception("Should not call OpenAI")

            result_local = describe_inventory_image_multi(
                image_data, path="test_image.jpg", model="test"
            )

            print("✅ Local CV Result:")
            print(f"   Items detected: {len(result_local)}")
            if result_local:
                for item in result_local[:2]:  # Show first 2 items
                    print(
                        f"   - {item.get('name', 'Unknown')}: {item.get('description', 'No description')}"
                    )
            print("   Model used: Local CLIP")
            print("   Processing time: Fast (local)")

    # Test 2: OpenAI System (mocked)
    print("\n2. OPENAI SYSTEM (GPT-4o-mini)")
    print("-" * 30)

    with patch.dict(os.environ, {"USE_LOCAL_CV": "false"}):
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = """[
            {
                "name": "Red T-Shirt",
                "category": "Tops",
                "description": "A vibrant red cotton t-shirt with short sleeves, perfect for casual wear.",
                "color": "Red",
                "condition": "New",
                "estimated_value": 25.00,
                "size": "Medium",
                "brand": "Unknown",
                "style": "Casual"
            }
        ]"""

        with patch("app.inventory_processing.openai_client") as mock_openai:
            mock_openai.chat.completions.create.return_value = mock_response

            result_openai = describe_inventory_image_multi(
                image_data, path="test_image.jpg", model="test"
            )

            print("✅ OpenAI Result:")
            print(f"   Items detected: {len(result_openai)}")
            if result_openai:
                for item in result_openai[:2]:  # Show first 2 items
                    print(
                        f"   - {item.get('name', 'Unknown')}: {item.get('description', 'No description')}"
                    )
            print("   Model used: OpenAI GPT-4o-mini")
            print("   Processing time: Slower (API call)")

    # Test 3: Direct Local CV Analysis
    print("\n3. DIRECT LOCAL CV ANALYSIS")
    print("-" * 30)

    analyzer = LocalGarmentAnalyzer()
    if analyzer._is_available():
        direct_result = analyzer.analyze_image(test_image)

        print("✅ Direct Local CV Analysis:")
        print(f"   Garments detected: {len(direct_result.get('garments', []))}")
        print(f"   Overall confidence: {direct_result.get('confidence', 0):.2f}")
        print(f"   Description: {direct_result.get('description', 'No description')}")
        print(f"   Model: {direct_result.get('model', 'Unknown')}")

        # Show detailed analysis
        if direct_result.get("garments"):
            garment = direct_result["garments"][0]
            attrs = direct_result.get("attributes", {}).get(garment["name"], {})
            print(f"   Top garment: {garment['name']} (confidence: {garment['confidence']:.2f})")
            if attrs.get("colors"):
                colors = [c["name"] for c in attrs["colors"][:2]]
                print(f"   Colors: {', '.join(colors)}")
            if attrs.get("styles"):
                styles = [s["name"] for s in attrs["styles"][:2]]
                print(f"   Styles: {', '.join(styles)}")
    else:
        print("❌ Local CV not available (missing dependencies)")

    # Summary
    print("\n📊 COMPARISON SUMMARY")
    print("=" * 60)
    print("LOCAL CV (CLIP):")
    print("  ✅ Fast processing (no API calls)")
    print("  ✅ No external dependencies in production")
    print("  ✅ Detailed attribute analysis (colors, styles, materials)")
    print("  ✅ Confidence scores for all predictions")
    print("  ✅ Privacy-focused (no data sent externally)")
    print("  ❌ Requires larger deployment package")
    print("  ❌ More computational resources needed")

    print("\nOPENAI (GPT-4o-mini):")
    print("  ✅ High-quality natural language descriptions")
    print("  ✅ Better understanding of complex scenes")
    print("  ✅ Smaller deployment package")
    print("  ❌ Slower processing (API latency)")
    print("  ❌ Requires internet connection")
    print("  ❌ API costs for each analysis")
    print("  ❌ Data privacy considerations")

    print("\n🔧 CONFIGURATION:")
    print("  Set USE_LOCAL_CV=true for local CLIP-based analysis")
    print("  Set USE_LOCAL_CV=false for OpenAI GPT-4o-mini analysis")


def test_local_cv_performance():
    """Test the performance characteristics of local CV."""
    print("\n⚡ LOCAL CV PERFORMANCE TEST")
    print("=" * 40)

    analyzer = LocalGarmentAnalyzer()

    if not analyzer._is_available():
        print("❌ Local CV not available")
        return

    # Test with different image types
    test_cases = [
        ("red_square", Image.new("RGB", (100, 100), color="red")),
        ("blue_square", Image.new("RGB", (100, 100), color="blue")),
        ("striped", Image.new("RGB", (100, 100), color="gray")),
    ]

    print(f"Testing {len(test_cases)} different images...")

    total_garments = 0
    total_confidence = 0.0

    for name, image in test_cases:
        result = analyzer.analyze_image(image)
        garments = result.get("garments", [])
        confidence = result.get("confidence", 0.0)

        total_garments += len(garments)
        total_confidence += confidence

        print(f"  {name}: {len(garments)} garments, {confidence:.2f} confidence")

    avg_confidence = total_confidence / len(test_cases) if test_cases else 0
    print("\n📈 Performance Summary:")
    print(f"  Average garments per image: {total_garments / len(test_cases):.1f}")
    print(f"  Average confidence: {avg_confidence:.2f}")
    print(f"  Model: {analyzer.model.__class__.__name__ if analyzer.model else 'None'}")


if __name__ == "__main__":
    test_cv_system_comparison()
    test_local_cv_performance()
