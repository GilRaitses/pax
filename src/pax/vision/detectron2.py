"""Detectron2 wrapper for instance segmentation.

This module provides a wrapper that invokes Detectron2 through a separate
Python 3.12 environment, since Detectron2 is not compatible with Python 3.14.
The actual Detectron2 processing happens in scripts/detectron2_runner.py
which runs in venv_detectron2 (Python 3.12).
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


class Detectron2Wrapper:
    """
    Instance segmentation wrapper using Detectron2.

    This wrapper invokes Detectron2 through a separate Python 3.12 environment
    to handle compatibility issues. The actual processing happens in a
    subprocess running scripts/detectron2_runner.py.
    """

    def __init__(self, venv_path: Path | None = None, runner_script: Path | None = None) -> None:
        """
        Initialize Detectron2 wrapper.

        Args:
            venv_path: Path to the Detectron2 virtual environment.
                      Defaults to project_root/venv_detectron2
            runner_script: Path to the detectron2_runner.py script.
                          Defaults to project_root/scripts/detectron2_runner.py
        """
        # Find project root (assuming this file is in src/pax/vision/)
        project_root = Path(__file__).parent.parent.parent.parent
        self.venv_path = venv_path or (project_root / "venv_detectron2")
        self.runner_script = runner_script or (project_root / "scripts" / "detectron2_runner.py")
        self.python_executable = self.venv_path / "bin" / "python"

        if not self.python_executable.exists():
            raise RuntimeError(
                f"Detectron2 Python environment not found at {self.python_executable}. "
                f"Please ensure venv_detectron2 is set up with Python 3.12."
            )

        if not self.runner_script.exists():
            raise RuntimeError(
                f"Detectron2 runner script not found at {self.runner_script}"
            )

        LOGGER.info(
            "Initialized Detectron2 wrapper (Python: %s, Script: %s)",
            self.python_executable,
            self.runner_script,
        )

    def segment(
        self, image_path: str | Path, conf_threshold: float = 0.5
    ) -> dict[str, Any]:
        """
        Perform instance segmentation on an image.

        Args:
            image_path: Path to the image file.
            conf_threshold: Confidence threshold for detections (default: 0.5).

        Returns:
            Dictionary with:
                - instances: List of instance dictionaries with masks, boundaries, area
                - pedestrian_count: Number of detected pedestrians
                - vehicle_count: Number of detected vehicles
                - bike_count: Number of detected bicycles
                - crowd_density: Estimated crowd density metric
                - total_area_covered: Total area covered by all instances (normalized)
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Invoke Detectron2 through subprocess
        try:
            result = subprocess.run(
                [
                    str(self.python_executable),
                    str(self.runner_script),
                    str(image_path),
                    str(conf_threshold),
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=300,  # 5 minute timeout
            )

            # Parse JSON output
            output_data = json.loads(result.stdout)
            return output_data

        except subprocess.TimeoutExpired:
            LOGGER.error("Detectron2 processing timed out for %s", image_path)
            raise RuntimeError(f"Detectron2 processing timed out for {image_path}")
        except subprocess.CalledProcessError as e:
            LOGGER.error(
                "Detectron2 processing failed for %s: %s", image_path, e.stderr
            )
            # Try to parse error output as JSON
            try:
                error_data = json.loads(e.stdout)
                if "error" in error_data:
                    raise RuntimeError(f"Detectron2 error: {error_data['error']}")
            except json.JSONDecodeError:
                pass
            raise RuntimeError(f"Detectron2 processing failed: {e.stderr}")
        except json.JSONDecodeError as e:
            LOGGER.error("Failed to parse Detectron2 output: %s", e)
            raise RuntimeError(f"Failed to parse Detectron2 output: {e}")

    def segment_batch(
        self, image_paths: list[str | Path], conf_threshold: float = 0.5
    ) -> list[dict[str, Any]]:
        """
        Perform instance segmentation on multiple images.

        Args:
            image_paths: List of paths to image files.
            conf_threshold: Confidence threshold for detections.

        Returns:
            List of segmentation dictionaries, one per image.
        """
        results = []
        for image_path in image_paths:
            try:
                result = self.segment(image_path, conf_threshold=conf_threshold)
                result["image_path"] = str(image_path)
                results.append(result)
            except Exception as exc:
                LOGGER.warning("Failed to process image %s: %s", image_path, exc)
                results.append(
                    {
                        "image_path": str(image_path),
                        "instances": [],
                        "pedestrian_count": 0,
                        "vehicle_count": 0,
                        "bike_count": 0,
                        "crowd_density": 0.0,
                        "total_area_covered": 0.0,
                        "total_instances": 0,
                        "error": str(exc),
                    }
                )
        return results


def segment_instances(image_path: str | Path, conf_threshold: float = 0.5) -> dict[str, Any]:
    """
    Convenience function to perform instance segmentation on a single image.

    Args:
        image_path: Path to the image file.
        conf_threshold: Confidence threshold for detections.

    Returns:
        Dictionary with segmentation results.
    """
    segmenter = Detectron2Wrapper()
    return segmenter.segment(image_path, conf_threshold=conf_threshold)
