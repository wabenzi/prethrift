"""
Local computer vision module for garment analysis.
Uses CLIP (Contrastive Language-Image Pre-training) for garment classification and description.
"""

import logging
from typing import Dict, List, Optional

import torch
from PIL import Image

logger = logging.getLogger(__name__)

try:
    from transformers import CLIPModel, CLIPProcessor
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers not available. Local CV will return fallback responses.")


class LocalGarmentAnalyzer:
    """
    Local garment analysis using CLIP model.
    Optimized for fashion and clothing recognition.
    """

    # Comprehensive garment categories optimized for fashion
    GARMENT_CATEGORIES = [
        "t-shirt", "shirt", "blouse", "tank top", "sweater", "hoodie", "cardigan",
        "dress", "skirt", "pants", "jeans", "shorts", "leggings", "trousers",
        "jacket", "coat", "blazer", "vest", "windbreaker", "puffer jacket",
        "sneakers", "boots", "sandals", "heels", "flats", "loafers",
        "hat", "cap", "scarf", "belt", "bag", "backpack", "purse",
        "socks", "underwear", "lingerie", "swimwear", "activewear", "athleisure"
    ]

    # Color categories for fashion
    COLOR_CATEGORIES = [
        "black", "white", "gray", "navy", "blue", "red", "pink", "purple",
        "green", "yellow", "orange", "brown", "beige", "cream", "khaki",
        "denim", "multicolor", "patterned", "striped", "plaid"
    ]

    # Style categories
    STYLE_CATEGORIES = [
        "casual", "formal", "business", "sporty", "elegant", "vintage",
        "bohemian", "minimalist", "trendy", "classic", "edgy", "romantic"
    ]

    # Material categories
    MATERIAL_CATEGORIES = [
        "cotton", "polyester", "wool", "silk", "linen", "denim", "leather",
        "synthetic", "blend", "knit", "woven", "stretch", "waterproof"
    ]

    def __init__(self):
        """Initialize the local garment analyzer."""
        self.model = None
        self.processor = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the CLIP model and processor."""
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Transformers not available. Local CV disabled.")
            return

        try:
            # Use OpenAI's CLIP model from Hugging Face
            model_name = "openai/clip-vit-base-patch32"
            self.model = CLIPModel.from_pretrained(model_name)
            self.processor = CLIPProcessor.from_pretrained(model_name)

            # Set to evaluation mode
            self.model.eval()

            logger.info(f"Loaded CLIP model: {model_name}")

        except Exception as e:
            logger.error(f"Failed to initialize CLIP model: {e}")
            self.model = None
            self.processor = None

    def analyze_image(self, image: Image.Image) -> Dict[str, any]:
        """
        Analyze a garment image and return detailed information.

        Args:
            image: PIL Image of the garment

        Returns:
            Dictionary containing garment analysis results
        """
        if not self._is_available():
            return self._get_fallback_response()

        try:
            # Classify garments in the image
            garments = self._classify_garments(image)

            # Extract attributes for each garment
            attributes = {}
            for garment in garments:
                attributes[garment['name']] = {
                    'colors': self._classify_colors(image, garment['name']),
                    'styles': self._classify_styles(image, garment['name']),
                    'materials': self._classify_materials(image, garment['name'])
                }

            # Generate natural language description
            description = self._generate_description(garments, attributes)

            return {
                'garments': garments,
                'attributes': attributes,
                'description': description,
                'confidence': sum(g['confidence'] for g in garments) / len(garments) if garments else 0.0,
                'model': 'local-clip-vit-base-patch32'
            }

        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return self._get_fallback_response()

    def get_image_embedding(self, image: Image.Image) -> Optional[List[float]]:
        """
        Generate CLIP visual embedding for the image.
        Returns a 512-dimensional vector for similarity search.

        Args:
            image: PIL Image to generate embedding for

        Returns:
            List of 512 floats representing the visual embedding, or None if unavailable
        """
        if not self._is_available():
            logger.warning("CLIP model not available, cannot generate image embedding")
            return None

        try:
            # Preprocess image for CLIP
            inputs = self.processor(images=image, return_tensors="pt")

            # Generate image features using CLIP
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                # Normalize the features for cosine similarity
                image_features = image_features / image_features.norm(dim=1, keepdim=True)

            # Convert to list of floats
            embedding = image_features.squeeze().cpu().numpy().tolist()

            logger.debug(f"Generated CLIP image embedding with dimension: {len(embedding)}")
            return embedding

        except Exception as e:
            logger.error(f"Error generating CLIP image embedding: {e}")
            return None

    def get_text_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate CLIP text embedding for fashion-related text.
        Returns a 512-dimensional vector matching image embedding space.

        Args:
            text: Text to generate embedding for (garment description, etc.)

        Returns:
            List of 512 floats representing the text embedding, or None if unavailable
        """
        if not self._is_available():
            logger.warning("CLIP model not available, cannot generate text embedding")
            return None

        try:
            # Preprocess text for CLIP
            inputs = self.processor(text=[text], return_tensors="pt", padding=True)

            # Generate text features using CLIP
            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)
                # Normalize the features for cosine similarity
                text_features = text_features / text_features.norm(dim=1, keepdim=True)

            # Convert to list of floats
            embedding = text_features.squeeze().cpu().numpy().tolist()

            logger.debug(f"Generated CLIP text embedding with dimension: {len(embedding)}")
            return embedding

        except Exception as e:
            logger.error(f"Error generating CLIP text embedding: {e}")
            return None

    def _classify_garments(self, image: Image.Image) -> List[Dict[str, any]]:
        """Classify garments in the image using CLIP."""
        if not self._is_available():
            return []

        try:
            # Prepare text prompts for garment classification
            text_prompts = [f"a photo of {garment}" for garment in self.GARMENT_CATEGORIES]

            # Process inputs
            inputs = self.processor(
                text=text_prompts,
                images=image,
                return_tensors="pt",
                padding=True
            )

            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)[0]

            # Get top predictions
            top_k = min(3, len(self.GARMENT_CATEGORIES))
            top_probs, top_indices = torch.topk(probs, top_k)

            garments = []
            for prob, idx in zip(top_probs, top_indices):
                confidence = float(prob)
                if confidence > 0.1:  # Minimum confidence threshold
                    garments.append({
                        'name': self.GARMENT_CATEGORIES[idx],
                        'confidence': confidence,
                        'category': 'clothing'
                    })

            return garments

        except Exception as e:
            logger.error(f"Error classifying garments: {e}")
            return []

    def _classify_colors(self, image: Image.Image, garment: str) -> List[Dict[str, any]]:
        """Classify colors for a specific garment."""
        if not self._is_available():
            return []

        try:
            text_prompts = [f"a {color} {garment}" for color in self.COLOR_CATEGORIES]

            inputs = self.processor(
                text=text_prompts,
                images=image,
                return_tensors="pt",
                padding=True
            )

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)[0]

            # Get top color predictions
            top_k = min(2, len(self.COLOR_CATEGORIES))
            top_probs, top_indices = torch.topk(probs, top_k)

            colors = []
            for prob, idx in zip(top_probs, top_indices):
                confidence = float(prob)
                if confidence > 0.15:  # Higher threshold for colors
                    colors.append({
                        'name': self.COLOR_CATEGORIES[idx],
                        'confidence': confidence
                    })

            return colors

        except Exception as e:
            logger.error(f"Error classifying colors: {e}")
            return []

    def _classify_styles(self, image: Image.Image, garment: str) -> List[Dict[str, any]]:
        """Classify style for a specific garment."""
        if not self._is_available():
            return []

        try:
            text_prompts = [f"a {style} {garment}" for style in self.STYLE_CATEGORIES]

            inputs = self.processor(
                text=text_prompts,
                images=image,
                return_tensors="pt",
                padding=True
            )

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)[0]

            top_probs, top_indices = torch.topk(probs, 2)

            styles = []
            for prob, idx in zip(top_probs, top_indices):
                confidence = float(prob)
                if confidence > 0.2:  # Higher threshold for styles
                    styles.append({
                        'name': self.STYLE_CATEGORIES[idx],
                        'confidence': confidence
                    })

            return styles

        except Exception as e:
            logger.error(f"Error classifying styles: {e}")
            return []

    def _classify_materials(self, image: Image.Image, garment: str) -> List[Dict[str, any]]:
        """Classify materials for a specific garment."""
        if not self._is_available():
            return []

        try:
            text_prompts = [f"a {garment} made of {material}" for material in self.MATERIAL_CATEGORIES]

            inputs = self.processor(
                text=text_prompts,
                images=image,
                return_tensors="pt",
                padding=True
            )

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)[0]

            top_probs, top_indices = torch.topk(probs, 2)

            materials = []
            for prob, idx in zip(top_probs, top_indices):
                confidence = float(prob)
                if confidence > 0.15:  # Threshold for materials
                    materials.append({
                        'name': self.MATERIAL_CATEGORIES[idx],
                        'confidence': confidence
                    })

            return materials

        except Exception as e:
            logger.error(f"Error classifying materials: {e}")
            return []

    def _generate_description(self, garments: List[Dict], attributes: Dict) -> str:
        """Generate a natural language description of the garments."""
        if not garments:
            return "No clear garments detected in the image."

        descriptions = []

        for garment in garments:
            garment_name = garment['name']
            garment_attrs = attributes.get(garment_name, {})

            # Build description parts
            parts = []

            # Add colors
            colors = garment_attrs.get('colors', [])
            if colors:
                color_names = [c['name'] for c in colors[:2]]
                parts.append(' and '.join(color_names))

            # Add garment name
            parts.append(garment_name)

            # Add style
            styles = garment_attrs.get('styles', [])
            if styles:
                style_name = styles[0]['name']
                parts.append(f"with a {style_name} style")

            # Add material
            materials = garment_attrs.get('materials', [])
            if materials:
                material_name = materials[0]['name']
                parts.append(f"appears to be made of {material_name}")

            description = ' '.join(parts)
            descriptions.append(description.capitalize())

        if len(descriptions) == 1:
            return descriptions[0] + "."
        else:
            return "The image contains: " + "; ".join(descriptions) + "."

    def _is_available(self) -> bool:
        """Check if the local CV model is available."""
        return TRANSFORMERS_AVAILABLE and self.model is not None and self.processor is not None

    def _get_fallback_response(self) -> Dict[str, any]:
        """Return a fallback response when the model is not available."""
        return {
            'garments': [{'name': 'clothing item', 'confidence': 0.5, 'category': 'clothing'}],
            'attributes': {
                'clothing item': {
                    'colors': [{'name': 'unknown', 'confidence': 0.5}],
                    'styles': [{'name': 'casual', 'confidence': 0.5}],
                    'materials': [{'name': 'unknown', 'confidence': 0.5}]
                }
            },
            'description': 'Local computer vision model not available. Showing placeholder data.',
            'confidence': 0.5,
            'model': 'fallback'
        }
