"""
Test comparing local CV extractor with Grok descriptions.
Uses real garment images and their corresponding Grok analyses from design/ directory.
"""

import json
from pathlib import Path

import pytest
from PIL import Image

from app.local_cv import LocalGarmentAnalyzer


class GrokVsLocalCVComparison:
    """
    Test suite for comparing local CV extractor with Grok descriptions.
    """

    def __init__(self):
        self.design_path = Path("/Users/leonhardt/dev/prethrift/design")
        self.images_path = self.design_path / "images"
        self.text_path = self.design_path / "text"
        self.analyzer = LocalGarmentAnalyzer()

    def get_image_description_pairs(self) -> list[tuple[str, str, str]]:
        """
        Get pairs of images and their corresponding Grok descriptions.
        Returns: List of (image_name, image_path, description_text) tuples
        """
        pairs = []

        # Define known image-description mappings
        mappings = {
            "queen-tshirt.jpeg": "queen-tshirt.txt",
            "baggy-jeans.jpeg": "baggy-jeans.txt",
            "blue-black-pattern-dress.jpeg": "blue-black-pattern-dress.txt",
            "orange-pattern-dress.jpeg": "orange-pattern-dress.txt",
            "flat-mars-shirt.jpeg": "flat-mars-shirt.txt",
            "test-blue-and-grey-shirts.jpg": "Test-blue-and-grey-shirts.txt",
        }

        for image_file, text_file in mappings.items():
            image_path = self.images_path / image_file
            text_path = self.text_path / text_file

            if image_path.exists() and text_path.exists():
                with open(text_path, encoding="utf-8") as f:
                    description = f.read().strip()
                pairs.append((image_file, str(image_path), description))

        return pairs

    def analyze_with_local_cv(self, image_path: str) -> dict:
        """Analyze image with local CV system."""
        if not self.analyzer._is_available():
            return {
                "error": "Local CV not available",
                "garments": [],
                "description": "Local CV system unavailable",
            }

        try:
            image = Image.open(image_path)
            result = self.analyzer.analyze_image(image)
            return result
        except Exception as e:
            return {"error": str(e), "garments": [], "description": f"Error analyzing image: {e}"}

    def extract_grok_key_terms(self, grok_description: str) -> dict[str, list[str]]:
        """
        Extract key terms from Grok description for comparison.
        """
        description_lower = grok_description.lower()

        # Extract garment types mentioned
        garment_types = []
        garment_keywords = [
            "t-shirt",
            "shirt",
            "blouse",
            "tank top",
            "dress",
            "jeans",
            "pants",
            "skirt",
            "jacket",
            "coat",
            "sweater",
            "hoodie",
            "shorts",
            "leggings",
        ]
        for keyword in garment_keywords:
            if keyword in description_lower:
                garment_types.append(keyword)

        # Extract colors mentioned
        colors = []
        color_keywords = [
            "black",
            "white",
            "blue",
            "red",
            "orange",
            "yellow",
            "green",
            "purple",
            "pink",
            "brown",
            "gray",
            "grey",
            "cream",
            "beige",
            "navy",
            "denim",
        ]
        for color in color_keywords:
            if color in description_lower:
                colors.append(color)

        # Extract style descriptors
        styles = []
        style_keywords = [
            "casual",
            "formal",
            "relaxed",
            "fitted",
            "oversized",
            "vintage",
            "trendy",
            "classic",
            "bohemian",
            "streetwear",
            "elegant",
        ]
        for style in style_keywords:
            if style in description_lower:
                styles.append(style)

        # Extract material mentions
        materials = []
        material_keywords = ["cotton", "denim", "wool", "silk", "polyester", "blend", "lightweight"]
        for material in material_keywords:
            if material in description_lower:
                materials.append(material)

        return {
            "garments": garment_types,
            "colors": colors,
            "styles": styles,
            "materials": materials,
        }

    def compare_results(self, local_result: dict, grok_terms: dict) -> dict:
        """
        Compare local CV results with extracted Grok terms.
        """
        comparison = {
            "garment_matches": [],
            "color_matches": [],
            "style_matches": [],
            "material_matches": [],
            "local_confidence": local_result.get("confidence", 0.0),
            "analysis": {},
        }

        # Compare garments
        local_garments = [g["name"] for g in local_result.get("garments", [])]
        for garment in local_garments:
            if garment in grok_terms["garments"]:
                comparison["garment_matches"].append(garment)

        # Compare colors
        local_attrs = local_result.get("attributes", {})
        local_colors = []
        for garment_attrs in local_attrs.values():
            for color in garment_attrs.get("colors", []):
                local_colors.append(color["name"])

        for color in local_colors:
            if color in grok_terms["colors"]:
                comparison["color_matches"].append(color)

        # Compare styles
        local_styles = []
        for garment_attrs in local_attrs.values():
            for style in garment_attrs.get("styles", []):
                local_styles.append(style["name"])

        for style in local_styles:
            if style in grok_terms["styles"]:
                comparison["style_matches"].append(style)

        # Compare materials
        local_materials = []
        for garment_attrs in local_attrs.values():
            for material in garment_attrs.get("materials", []):
                local_materials.append(material["name"])

        for material in local_materials:
            if material in grok_terms["materials"]:
                comparison["material_matches"].append(material)

        # Calculate match percentages
        comparison["analysis"] = {
            "garment_match_rate": len(comparison["garment_matches"])
            / max(len(grok_terms["garments"]), 1),
            "color_match_rate": len(comparison["color_matches"])
            / max(len(grok_terms["colors"]), 1),
            "style_match_rate": len(comparison["style_matches"])
            / max(len(grok_terms["styles"]), 1),
            "material_match_rate": len(comparison["material_matches"])
            / max(len(grok_terms["materials"]), 1),
            "local_detected_garments": len(local_garments),
            "grok_mentioned_garments": len(grok_terms["garments"]),
        }

        return comparison

    def run_comprehensive_comparison(self) -> dict:
        """
        Run comprehensive comparison across all available image-description pairs.
        """
        pairs = self.get_image_description_pairs()
        results = {}

        print("\n🔍 GROK vs LOCAL CV COMPARISON")
        print(f"{'=' * 60}")
        print(f"Found {len(pairs)} image-description pairs to analyze")

        for image_name, image_path, grok_description in pairs:
            print(f"\n📸 Analyzing: {image_name}")
            print(f"{'─' * 40}")

            # Analyze with local CV
            local_result = self.analyze_with_local_cv(image_path)

            # Extract key terms from Grok description
            grok_terms = self.extract_grok_key_terms(grok_description)

            # Compare results
            comparison = self.compare_results(local_result, grok_terms)

            # Store results
            results[image_name] = {
                "local_result": local_result,
                "grok_terms": grok_terms,
                "comparison": comparison,
                "grok_description": grok_description[:200] + "..."
                if len(grok_description) > 200
                else grok_description,
            }

            # Print analysis
            print(
                f"Grok detected: {', '.join(grok_terms['garments']) if grok_terms['garments'] else 'No garments'}"
            )
            print(
                f"Local CV detected: {', '.join([g['name'] for g in local_result.get('garments', [])])}"
            )
            print(f"Garment matches: {comparison['garment_matches']}")
            print(f"Color matches: {comparison['color_matches']}")
            print(
                f"Match rates - Garments: {comparison['analysis']['garment_match_rate']:.2f}, Colors: {comparison['analysis']['color_match_rate']:.2f}"
            )
            print(f"Local confidence: {comparison['local_confidence']:.3f}")

        # Calculate overall statistics
        overall_stats = self._calculate_overall_stats(results)
        results["_overall_stats"] = overall_stats

        print("\n📊 OVERALL COMPARISON RESULTS")
        print(f"{'=' * 60}")
        print(f"Average garment match rate: {overall_stats['avg_garment_match']:.2f}")
        print(f"Average color match rate: {overall_stats['avg_color_match']:.2f}")
        print(f"Average style match rate: {overall_stats['avg_style_match']:.2f}")
        print(f"Average local CV confidence: {overall_stats['avg_confidence']:.3f}")
        print(
            f"Images where local CV found garments: {overall_stats['detection_success_rate']:.2f}"
        )

        return results

    def _calculate_overall_stats(self, results: dict) -> dict:
        """Calculate overall statistics across all comparisons."""
        comparisons = [r["comparison"] for r in results.values() if "comparison" in r]

        if not comparisons:
            return {}

        total_garment_match = sum(c["analysis"]["garment_match_rate"] for c in comparisons)
        total_color_match = sum(c["analysis"]["color_match_rate"] for c in comparisons)
        total_style_match = sum(c["analysis"]["style_match_rate"] for c in comparisons)
        total_confidence = sum(c["local_confidence"] for c in comparisons)
        successful_detections = sum(
            1 for c in comparisons if c["analysis"]["local_detected_garments"] > 0
        )

        return {
            "avg_garment_match": total_garment_match / len(comparisons),
            "avg_color_match": total_color_match / len(comparisons),
            "avg_style_match": total_style_match / len(comparisons),
            "avg_confidence": total_confidence / len(comparisons),
            "detection_success_rate": successful_detections / len(comparisons),
            "total_images_analyzed": len(comparisons),
        }


def test_grok_vs_local_cv_comparison():
    """Test function for pytest to compare Grok vs Local CV."""
    comparison = GrokVsLocalCVComparison()
    results = comparison.run_comprehensive_comparison()

    # Assert that we have some results
    assert len(results) > 1, "Should have analyzed at least one image-description pair"

    # Assert that local CV is working (at least some detections)
    overall_stats = results.get("_overall_stats", {})
    if overall_stats:
        assert overall_stats["detection_success_rate"] > 0, (
            "Local CV should detect garments in at least some images"
        )

    # Print detailed results for manual inspection
    print("\n🔬 DETAILED COMPARISON RESULTS")
    print(f"{'=' * 80}")

    for image_name, result in results.items():
        if image_name.startswith("_"):
            continue

        print(f"\n📷 {image_name}")
        print(f"{'─' * 50}")

        grok_desc = result["grok_description"]
        local_desc = result["local_result"].get("description", "No description")

        print(f"Grok: {grok_desc}")
        print(f"Local CV: {local_desc}")

        comparison = result["comparison"]
        print(
            f"Matches - Garments: {comparison['garment_matches']}, Colors: {comparison['color_matches']}"
        )


def test_individual_image_analysis():
    """Test individual image analysis with detailed output."""
    comparison = GrokVsLocalCVComparison()

    if not comparison.analyzer._is_available():
        pytest.skip("Local CV not available")

    pairs = comparison.get_image_description_pairs()

    if not pairs:
        pytest.skip("No image-description pairs found")

    # Test the first available pair
    image_name, image_path, grok_description = pairs[0]

    print(f"\n🧪 DETAILED ANALYSIS: {image_name}")
    print(f"{'=' * 60}")

    # Analyze with local CV
    local_result = comparison.analyze_with_local_cv(image_path)
    grok_terms = comparison.extract_grok_key_terms(grok_description)

    print("📝 Grok Description:")
    print(f"{grok_description[:300]}...")

    print("\n🤖 Local CV Analysis:")
    print(f"Garments: {[g['name'] for g in local_result.get('garments', [])]}")
    print(f"Description: {local_result.get('description', 'No description')}")
    print(f"Confidence: {local_result.get('confidence', 0):.3f}")

    print("\n🔍 Extracted Grok Terms:")
    for category, terms in grok_terms.items():
        print(f"{category.capitalize()}: {terms}")

    # Should have detected something
    assert len(local_result.get("garments", [])) > 0 or "error" in local_result, (
        f"Should detect garments or have error for {image_name}"
    )


if __name__ == "__main__":
    # Run the comparison when script is executed directly
    comparison = GrokVsLocalCVComparison()
    results = comparison.run_comprehensive_comparison()

    # Save results to JSON for further analysis
    output_file = "/Users/leonhardt/dev/prethrift/design/images/grok_vs_local_cv_comparison.json"
    with open(output_file, "w") as f:
        # Convert PIL Image objects to strings for JSON serialization
        json_results = {}
        for key, value in results.items():
            if isinstance(value, dict):
                json_results[key] = value
            else:
                json_results[key] = str(value)

        json.dump(json_results, f, indent=2, default=str)

    print(f"\n💾 Results saved to: {output_file}")
