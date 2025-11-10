#!/usr/bin/env python3
"""Standalone Detectron2 script that runs in Python 3.12 environment.

This script is invoked by the main codebase wrapper via subprocess.
It performs instance segmentation using Detectron2 and outputs JSON results.
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog
from detectron2.engine import DefaultPredictor
from detectron2.model_zoo import model_zoo


def segment_image(image_path: str, conf_threshold: float = 0.5) -> dict:
    """
    Perform instance segmentation on an image using Detectron2.

    Args:
        image_path: Path to the image file
        conf_threshold: Confidence threshold for detections

    Returns:
        Dictionary with segmentation results
    """
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    height, width = image.shape[:2]

    # Setup Detectron2 config
    cfg = get_cfg()
    # Use COCO-InstanceSegmentation model
    cfg.merge_from_file(
        model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
    )
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = conf_threshold
    cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url(
        "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
    )
    cfg.MODEL.DEVICE = "cpu"  # Use CPU for compatibility

    # Create predictor
    predictor = DefaultPredictor(cfg)

    # Run prediction
    outputs = predictor(image)

    # Extract results
    instances = outputs["instances"]
    metadata = MetadataCatalog.get(cfg.DATASETS.TRAIN[0])

    # COCO class IDs
    PERSON_CLASS_ID = 0
    BICYCLE_CLASS_ID = 1
    CAR_CLASS_ID = 2
    MOTORCYCLE_CLASS_ID = 3
    BUS_CLASS_ID = 5
    TRUCK_CLASS_ID = 7
    VEHICLE_CLASS_IDS = {CAR_CLASS_ID, MOTORCYCLE_CLASS_ID, BUS_CLASS_ID, TRUCK_CLASS_ID}

    result_instances = []
    pedestrian_count = 0
    vehicle_count = 0
    bike_count = 0
    total_area = 0.0

    for i in range(len(instances)):
        class_id = int(instances.pred_classes[i])
        score = float(instances.scores[i])
        bbox = instances.pred_boxes[i].tensor[0].cpu().numpy().tolist()

        # Get mask
        mask = instances.pred_masks[i].cpu().numpy()
        mask_area = float(np.sum(mask))
        total_area += mask_area

        # Extract boundary points from mask
        contours, _ = cv2.findContours(
            mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        boundary_points = []
        if len(contours) > 0:
            # Use the largest contour
            largest_contour = max(contours, key=cv2.contourArea)
            boundary_points = [[float(p[0][0]), float(p[0][1])] for p in largest_contour]

        class_name = metadata.thing_classes[class_id] if class_id < len(metadata.thing_classes) else f"class_{class_id}"

        instance = {
            "class_id": class_id,
            "class_name": class_name,
            "confidence": score,
            "bbox": bbox,
            "mask_area": mask_area,
            "mask_area_normalized": mask_area / (width * height) if width * height > 0 else 0.0,
            "boundary_points": boundary_points,
            "has_mask": True,
        }
        result_instances.append(instance)

        # Count objects
        if class_id == PERSON_CLASS_ID:
            pedestrian_count += 1
        elif class_id == BICYCLE_CLASS_ID:
            bike_count += 1
        elif class_id in VEHICLE_CLASS_IDS:
            vehicle_count += 1

    # Calculate crowd density
    pedestrian_area = sum(
        inst["mask_area_normalized"]
        for inst in result_instances
        if inst["class_id"] == PERSON_CLASS_ID
    )
    crowd_density = (
        pedestrian_count / pedestrian_area if pedestrian_area > 0 else 0.0
    )

    return {
        "instances": result_instances,
        "pedestrian_count": pedestrian_count,
        "vehicle_count": vehicle_count,
        "bike_count": bike_count,
        "crowd_density": crowd_density,
        "total_area_covered": total_area / (width * height) if len(result_instances) > 0 else 0.0,
        "total_instances": len(result_instances),
    }


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: detectron2_runner.py <image_path> [conf_threshold]", file=sys.stderr)
        sys.exit(1)

    image_path = sys.argv[1]
    conf_threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5

    try:
        result = segment_image(image_path, conf_threshold)
        result["image_path"] = image_path
        print(json.dumps(result, indent=2))
    except Exception as e:
        error_result = {
            "error": str(e),
            "image_path": image_path,
            "instances": [],
            "pedestrian_count": 0,
            "vehicle_count": 0,
            "bike_count": 0,
            "crowd_density": 0.0,
            "total_area_covered": 0.0,
            "total_instances": 0,
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()

