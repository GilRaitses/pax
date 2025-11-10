"""YOLOv8n wrapper for object detection in traffic camera images."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ultralytics import YOLO

LOGGER = logging.getLogger(__name__)

# COCO class IDs for relevant objects
PERSON_CLASS_ID = 0
BICYCLE_CLASS_ID = 1
CAR_CLASS_ID = 2
MOTORCYCLE_CLASS_ID = 3
BUS_CLASS_ID = 5
TRUCK_CLASS_ID = 7

# Vehicle class IDs (car, motorcycle, bus, truck)
VEHICLE_CLASS_IDS = {CAR_CLASS_ID, MOTORCYCLE_CLASS_ID, BUS_CLASS_ID, TRUCK_CLASS_ID}


class YOLOv8nDetector:
    """YOLOv8n object detector wrapper for traffic scene analysis."""

    def __init__(self, model_path: str | None = None) -> None:
        """
        Initialize YOLOv8n detector.

        Args:
            model_path: Optional path to custom model weights. If None, uses pretrained YOLOv8n.
        """
        if model_path is None:
            model_path = "yolov8n.pt"
        self.model = YOLO(model_path)
        LOGGER.info("Initialized YOLOv8n detector with model: %s", model_path)

    def detect(self, image_path: str | Path, conf_threshold: float = 0.25) -> dict[str, Any]:
        """
        Detect objects in an image and return counts.

        Args:
            image_path: Path to the image file.
            conf_threshold: Confidence threshold for detections (default: 0.25).

        Returns:
            Dictionary with:
                - pedestrian_count: Number of detected pedestrians
                - vehicle_count: Number of detected vehicles (cars, motorcycles, buses, trucks)
                - bike_count: Number of detected bicycles
                - total_detections: Total number of detections
                - detections: List of detection dictionaries with class, confidence, bbox
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        results = self.model(str(image_path), conf=conf_threshold, verbose=False)

        pedestrian_count = 0
        vehicle_count = 0
        bike_count = 0
        detections = []

        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes

            if boxes is not None:
                for box in boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    bbox = box.xyxy[0].cpu().tolist()

                    detection = {
                        "class_id": class_id,
                        "class_name": result.names[class_id],
                        "confidence": confidence,
                        "bbox": bbox,
                    }
                    detections.append(detection)

                    # Count objects
                    if class_id == PERSON_CLASS_ID:
                        pedestrian_count += 1
                    elif class_id == BICYCLE_CLASS_ID:
                        bike_count += 1
                    elif class_id in VEHICLE_CLASS_IDS:
                        vehicle_count += 1

        return {
            "pedestrian_count": pedestrian_count,
            "vehicle_count": vehicle_count,
            "bike_count": bike_count,
            "total_detections": len(detections),
            "detections": detections,
        }

    def detect_batch(
        self, image_paths: list[str | Path], conf_threshold: float = 0.25
    ) -> list[dict[str, Any]]:
        """
        Detect objects in multiple images.

        Args:
            image_paths: List of paths to image files.
            conf_threshold: Confidence threshold for detections.

        Returns:
            List of detection dictionaries, one per image.
        """
        results = []
        for image_path in image_paths:
            try:
                result = self.detect(image_path, conf_threshold=conf_threshold)
                result["image_path"] = str(image_path)
                results.append(result)
            except Exception as exc:
                LOGGER.warning("Failed to process image %s: %s", image_path, exc)
                results.append(
                    {
                        "image_path": str(image_path),
                        "pedestrian_count": 0,
                        "vehicle_count": 0,
                        "bike_count": 0,
                        "total_detections": 0,
                        "detections": [],
                        "error": str(exc),
                    }
                )
        return results


def detect_objects(image_path: str | Path, conf_threshold: float = 0.25) -> dict[str, Any]:
    """
    Convenience function to detect objects in a single image.

    Args:
        image_path: Path to the image file.
        conf_threshold: Confidence threshold for detections.

    Returns:
        Dictionary with detection counts and details.
    """
    detector = YOLOv8nDetector()
    return detector.detect(image_path, conf_threshold=conf_threshold)

