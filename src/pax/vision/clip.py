"""CLIP wrapper for scene understanding and semantic feature extraction."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

LOGGER = logging.getLogger(__name__)

# Common scene labels for urban traffic scenes
DEFAULT_SCENE_LABELS = [
    "busy street",
    "quiet street",
    "pedestrian crossing",
    "intersection",
    "sidewalk",
    "traffic jam",
    "empty road",
    "crowded area",
    "urban scene",
    "traffic light",
    "crosswalk",
    "parking area",
    "construction zone",
    "residential area",
    "commercial area",
]


class CLIPWrapper:
    """CLIP model wrapper for scene understanding and semantic feature extraction."""

    def __init__(
        self,
        model_name: str = "openai/clip-vit-base-patch32",
        scene_labels: list[str] | None = None,
    ) -> None:
        """
        Initialize CLIP model.

        Args:
            model_name: HuggingFace model identifier for CLIP model.
            scene_labels: Custom list of scene labels to use. If None, uses default urban scene labels.
        """
        self.model_name = model_name
        self.scene_labels = scene_labels or DEFAULT_SCENE_LABELS

        LOGGER.info("Loading CLIP model: %s", model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model = CLIPModel.from_pretrained(model_name)
        self.model.eval()  # Set to evaluation mode

        # Move to CPU (can be changed to GPU if available)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        LOGGER.info("CLIP model loaded on device: %s", self.device)

    def understand_scene(
        self, image_path: str | Path, custom_labels: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Analyze scene and extract semantic features.

        Args:
            image_path: Path to the image file.
            custom_labels: Optional custom labels to use instead of default scene labels.

        Returns:
            Dictionary with:
                - scene_labels: List of scene labels with confidence scores
                - top_scene: Most likely scene label
                - top_confidence: Confidence score for top scene
                - semantic_features: Raw CLIP embedding vector
                - all_scores: Dictionary mapping labels to scores
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Load and process image
        image = Image.open(image_path).convert("RGB")
        labels = custom_labels or self.scene_labels

        # Process inputs
        inputs = self.processor(
            text=labels, images=image, return_tensors="pt", padding=True
        ).to(self.device)

        # Run inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)

        # Extract results
        scores = probs[0].cpu().numpy()
        label_scores = dict(zip(labels, scores.tolist()))

        # Get top scene
        top_idx = scores.argmax()
        top_scene = labels[top_idx]
        top_confidence = float(scores[top_idx])

        # Get image embedding (semantic features)
        image_features = outputs.image_embeds[0].cpu().numpy()
        semantic_features = image_features.tolist()

        # Create scene labels list with scores
        scene_labels_list = [
            {"label": label, "score": float(score)}
            for label, score in sorted(
                label_scores.items(), key=lambda x: x[1], reverse=True
            )
        ]

        return {
            "scene_labels": scene_labels_list,
            "top_scene": top_scene,
            "top_confidence": top_confidence,
            "semantic_features": semantic_features,
            "all_scores": label_scores,
        }

    def extract_features(self, image_path: str | Path) -> list[float]:
        """
        Extract raw CLIP embedding features from an image.

        Args:
            image_path: Path to the image file.

        Returns:
            List of float values representing the CLIP embedding vector.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Load and process image
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        # Extract features
        with torch.no_grad():
            outputs = self.model.get_image_features(**inputs)
            features = outputs[0].cpu().numpy()

        return features.tolist()

    def understand_batch(
        self, image_paths: list[str | Path], custom_labels: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Analyze multiple images.

        Args:
            image_paths: List of paths to image files.
            custom_labels: Optional custom labels to use.

        Returns:
            List of scene understanding dictionaries, one per image.
        """
        results = []
        for image_path in image_paths:
            try:
                result = self.understand_scene(image_path, custom_labels=custom_labels)
                result["image_path"] = str(image_path)
                results.append(result)
            except Exception as exc:
                LOGGER.warning("Failed to process image %s: %s", image_path, exc)
                results.append(
                    {
                        "image_path": str(image_path),
                        "scene_labels": [],
                        "top_scene": None,
                        "top_confidence": 0.0,
                        "semantic_features": [],
                        "all_scores": {},
                        "error": str(exc),
                    }
                )
        return results


def understand_scene(
    image_path: str | Path, custom_labels: list[str] | None = None
) -> dict[str, Any]:
    """
    Convenience function to analyze scene in a single image.

    Args:
        image_path: Path to the image file.
        custom_labels: Optional custom labels to use.

    Returns:
        Dictionary with scene understanding results.
    """
    clip_wrapper = CLIPWrapper()
    return clip_wrapper.understand_scene(image_path, custom_labels=custom_labels)

