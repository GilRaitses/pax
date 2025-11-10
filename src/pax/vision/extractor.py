"""Unified feature extraction pipeline combining YOLOv8n, Detectron2, and CLIP."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pax.vision.clip import CLIPWrapper
from pax.vision.detectron2 import Detectron2Wrapper
from pax.vision.yolov8n import YOLOv8nDetector

LOGGER = logging.getLogger(__name__)


class FeatureExtractor:
    """Unified feature extraction combining all vision models."""

    def __init__(
        self,
        use_yolo: bool = True,
        use_detectron2: bool = True,
        use_clip: bool = True,
        yolo_conf_threshold: float = 0.25,
        detectron2_conf_threshold: float = 0.5,
    ) -> None:
        """
        Initialize feature extractor with specified models.

        Args:
            use_yolo: Whether to use YOLOv8n for object detection.
            use_detectron2: Whether to use Detectron2 for instance segmentation.
            use_clip: Whether to use CLIP for scene understanding.
            yolo_conf_threshold: Confidence threshold for YOLOv8n.
            detectron2_conf_threshold: Confidence threshold for Detectron2.
        """
        self.use_yolo = use_yolo
        self.use_detectron2 = use_detectron2
        self.use_clip = use_clip

        self.yolo_detector = None
        self.detectron2_wrapper = None
        self.clip_wrapper = None

        # Initialize models
        if use_yolo:
            try:
                self.yolo_detector = YOLOv8nDetector()
                LOGGER.info("YOLOv8n detector initialized")
            except Exception as e:
                LOGGER.warning("Failed to initialize YOLOv8n: %s", e)
                self.use_yolo = False

        if use_detectron2:
            try:
                self.detectron2_wrapper = Detectron2Wrapper()
                LOGGER.info("Detectron2 wrapper initialized")
            except Exception as e:
                LOGGER.warning("Failed to initialize Detectron2: %s", e)
                self.use_detectron2 = False

        if use_clip:
            try:
                self.clip_wrapper = CLIPWrapper()
                LOGGER.info("CLIP wrapper initialized")
            except Exception as e:
                LOGGER.warning("Failed to initialize CLIP: %s", e)
                self.use_clip = False

        self.yolo_conf_threshold = yolo_conf_threshold
        self.detectron2_conf_threshold = detectron2_conf_threshold

    def extract(self, image_path: str | Path) -> dict[str, Any]:
        """
        Extract all features from an image.

        Args:
            image_path: Path to the image file.

        Returns:
            Dictionary containing all extracted features from all models.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        features = {
            "image_path": str(image_path),
            "yolo": {},
            "detectron2": {},
            "clip": {},
            "errors": [],
        }

        # Extract YOLOv8n features
        if self.use_yolo and self.yolo_detector:
            try:
                yolo_result = self.yolo_detector.detect(
                    image_path, conf_threshold=self.yolo_conf_threshold
                )
                features["yolo"] = {
                    "pedestrian_count": yolo_result["pedestrian_count"],
                    "vehicle_count": yolo_result["vehicle_count"],
                    "bike_count": yolo_result["bike_count"],
                    "total_detections": yolo_result["total_detections"],
                }
            except Exception as e:
                LOGGER.warning("YOLOv8n extraction failed for %s: %s", image_path, e)
                features["errors"].append(f"YOLOv8n: {str(e)}")

        # Extract Detectron2 features
        if self.use_detectron2 and self.detectron2_wrapper:
            try:
                detectron2_result = self.detectron2_wrapper.segment(
                    image_path, conf_threshold=self.detectron2_conf_threshold
                )
                features["detectron2"] = {
                    "pedestrian_count": detectron2_result["pedestrian_count"],
                    "vehicle_count": detectron2_result["vehicle_count"],
                    "bike_count": detectron2_result["bike_count"],
                    "crowd_density": detectron2_result["crowd_density"],
                    "total_area_covered": detectron2_result["total_area_covered"],
                    "total_instances": detectron2_result["total_instances"],
                }
            except Exception as e:
                LOGGER.warning("Detectron2 extraction failed for %s: %s", image_path, e)
                features["errors"].append(f"Detectron2: {str(e)}")

        # Extract CLIP features
        if self.use_clip and self.clip_wrapper:
            try:
                clip_result = self.clip_wrapper.understand_scene(image_path)
                features["clip"] = {
                    "top_scene": clip_result["top_scene"],
                    "top_confidence": clip_result["top_confidence"],
                    "semantic_features": clip_result["semantic_features"],
                    "scene_labels": clip_result["scene_labels"][:5],  # Top 5 scenes
                }
            except Exception as e:
                LOGGER.warning("CLIP extraction failed for %s: %s", image_path, e)
                features["errors"].append(f"CLIP: {str(e)}")

        return features

    def extract_batch(
        self, image_paths: list[str | Path], show_progress: bool = True
    ) -> list[dict[str, Any]]:
        """
        Extract features from multiple images.

        Args:
            image_paths: List of paths to image files.
            show_progress: Whether to show progress bar.

        Returns:
            List of feature dictionaries, one per image.
        """
        from tqdm import tqdm

        results = []
        iterator = tqdm(image_paths, desc="Extracting features") if show_progress else image_paths

        for image_path in iterator:
            try:
                result = self.extract(image_path)
                results.append(result)
            except Exception as e:
                LOGGER.error("Failed to extract features from %s: %s", image_path, e)
                results.append(
                    {
                        "image_path": str(image_path),
                        "yolo": {},
                        "detectron2": {},
                        "clip": {},
                        "errors": [f"Extraction failed: {str(e)}"],
                    }
                )

        return results


def extract_features(image_path: str | Path) -> dict[str, Any]:
    """
    Convenience function to extract all features from a single image.

    Args:
        image_path: Path to the image file.

    Returns:
        Dictionary containing all extracted features.
    """
    extractor = FeatureExtractor()
    return extractor.extract(image_path)

