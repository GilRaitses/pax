# Vision Model Output Formats

**Created:** November 10, 2025  
**Purpose:** Document standard output formats for vision models used in urban scene analysis

## Overview

This document describes the output formats of three computer vision models used for extracting features from traffic camera images:

1. **YOLOv8n** - Fast object detection for counting pedestrians, vehicles, and bicycles
2. **Detectron2** - Instance segmentation for detailed object boundaries and density analysis
3. **CLIP** - Scene understanding for semantic features and context

## YOLOv8n Output Format

### Model Overview

YOLOv8n (You Only Look Once version 8 nano) is an ultralight object detection model developed by Ultralytics. It provides fast inference suitable for real-time traffic camera analysis.

### Output Structure

When processing an image, YOLOv8n returns a `Results` object containing:

#### Detection Results (`result.boxes`)

- **`boxes.cls`**: Tensor of class IDs (shape: `[N]`) where N is the number of detections
- **`boxes.conf`**: Tensor of confidence scores (shape: `[N]`) ranging from 0.0 to 1.0
- **`boxes.xyxy`**: Tensor of bounding box coordinates (shape: `[N, 4]`) in format `[x1, y1, x2, y2]`
- **`boxes.xywh`**: Tensor of bounding box coordinates (shape: `[N, 4]`) in format `[x_center, y_center, width, height]`

#### Class Names (`result.names`)

Dictionary mapping class IDs to class names (e.g., `{0: 'person', 1: 'bicycle', 2: 'car'}`)

### COCO Class IDs (Relevant for Urban Scenes)

- `0`: person (pedestrian)
- `1`: bicycle
- `2`: car
- `3`: motorcycle
- `5`: bus
- `7`: truck

### Example Output Structure

```python
{
    "pedestrian_count": 5,
    "vehicle_count": 12,
    "bike_count": 2,
    "total_detections": 19,
    "detections": [
        {
            "class_id": 0,
            "class_name": "person",
            "confidence": 0.87,
            "bbox": [120, 45, 180, 200]  # [x1, y1, x2, y2]
        },
        # ... more detections
    ]
}
```

### Implementation Notes

- Confidence threshold typically set to 0.25 (configurable)
- Bounding boxes are in pixel coordinates relative to image dimensions
- Model supports batch processing for multiple images
- Export formats: PyTorch, ONNX, TensorRT, CoreML, TensorFlow

## Detectron2 Output Format

### Model Overview

Detectron2 is Facebook AI Research's modular object detection and segmentation framework. It provides instance segmentation capabilities, enabling pixel-level object boundaries and density analysis.

### Output Structure

During inference, Detectron2 models output a **list of dictionaries**, one per image:

#### Instance Detection (`output['instances']`)

An `Instances` object containing:

- **`pred_boxes`**: `Boxes` object storing N bounding boxes
  - Format: `[x1, y1, x2, y2]` in absolute coordinates
  - Shape: `(N, 4)` tensor
  
- **`pred_classes`**: Tensor of predicted class indices
  - Shape: `(N,)` tensor
  - Values correspond to COCO class IDs
  
- **`scores`**: Tensor of confidence scores
  - Shape: `(N,)` tensor
  - Range: [0.0, 1.0]
  
- **`pred_masks`**: Tensor of binary segmentation masks (if segmentation enabled)
  - Shape: `(N, H, W)` tensor where H, W are image dimensions
  - Each mask is a binary array indicating object pixels

#### Semantic Segmentation (`output['sem_seg']`)

- Tensor of shape `(num_classes, H, W)` for semantic segmentation tasks
- Each channel represents a class probability map

#### Region Proposals (`output['proposals']`)

- `Instances` object containing region proposals (used in two-stage detectors)

### Example Output Structure

```python
[
    {
        "instances": {
            "pred_boxes": tensor([[120, 45, 180, 200], ...]),  # Shape: (N, 4)
            "pred_classes": tensor([0, 2, 0, ...]),  # Shape: (N,)
            "scores": tensor([0.95, 0.87, 0.92, ...]),  # Shape: (N,)
            "pred_masks": tensor([[[0, 0, 1, ...], ...], ...])  # Shape: (N, H, W)
        },
        "sem_seg": tensor([...]),  # Optional: (num_classes, H, W)
        "proposals": {...}  # Optional: region proposals
    }
]
```

### Implementation Notes

- Supports both detection and instance segmentation modes
- Masks enable precise density calculations (pixels per object)
- More computationally intensive than YOLOv8n but provides higher accuracy
- Commonly used models: R50-FPN, R101-FPN, X101-FPN

## CLIP Output Format

### Model Overview

CLIP (Contrastive Language-Image Pre-training) is OpenAI's multimodal model that learns joint representations of images and text. It enables zero-shot scene understanding and semantic feature extraction.

### Output Structure

CLIP consists of two encoders that produce fixed-length embeddings:

#### Image Encoder Output

- **Image Embeddings**: Tensor of shape `(batch_size, embedding_dim)`
  - Default embedding dimension: 512 or 768 (model-dependent)
  - Normalized vectors in shared latent space
  
#### Text Encoder Output

- **Text Embeddings**: Tensor of shape `(batch_size, embedding_dim)`
  - Same dimension as image embeddings
  - Normalized vectors aligned with image embeddings

#### Similarity Scores

- **Image-Text Similarity**: Cosine similarity between image and text embeddings
  - Range: [-1, 1] (after normalization)
  - Higher values indicate better semantic match

### Example Output Structure

```python
{
    "image_embedding": tensor([0.123, -0.456, 0.789, ...]),  # Shape: (512,)
    "text_embeddings": {
        "busy_intersection": tensor([0.234, -0.345, 0.567, ...]),
        "quiet_street": tensor([-0.123, 0.456, -0.789, ...]),
        "rush_hour": tensor([0.345, -0.234, 0.678, ...])
    },
    "similarity_scores": {
        "busy_intersection": 0.85,
        "quiet_street": 0.12,
        "rush_hour": 0.78
    }
}
```

### Implementation Notes

- Zero-shot classification: Compare image embedding to text prompts
- Scene understanding: Use semantic prompts like "busy intersection", "pedestrian crossing", "traffic jam"
- Embeddings can be used for similarity search and clustering
- Common models: `openai/clip-vit-base-patch32`, `openai/clip-vit-large-patch14`

## Standard Formats in Urban Vision Research

### COCO Format

The Common Objects in Context (COCO) format is widely used for object detection and segmentation:

```json
{
    "info": {...},
    "licenses": [...],
    "categories": [
        {"id": 1, "name": "person", "supercategory": "person"},
        {"id": 2, "name": "bicycle", "supercategory": "vehicle"},
        ...
    ],
    "images": [
        {
            "id": 1,
            "width": 1920,
            "height": 1080,
            "file_name": "image.jpg"
        }
    ],
    "annotations": [
        {
            "id": 1,
            "image_id": 1,
            "category_id": 1,
            "bbox": [x, y, width, height],
            "area": 1234.5,
            "segmentation": [[x1, y1, x2, y2, ...]],
            "iscrowd": 0
        }
    ]
}
```

### PASCAL VOC Format

XML-based format for object detection annotations:

```xml
<annotation>
    <filename>image.jpg</filename>
    <size>
        <width>1920</width>
        <height>1080</height>
    </size>
    <object>
        <name>person</name>
        <bndbox>
            <xmin>120</xmin>
            <ymin>45</ymin>
            <xmax>180</xmax>
            <ymax>200</ymax>
        </bndbox>
    </object>
</annotation>
```

### KITTI Format

Commonly used in autonomous driving research:

- Object detection: Text files with format `[class, truncated, occluded, alpha, bbox, dimensions, location, rotation_y, score]`
- Tracking: Additional frame and track IDs
- Scene segmentation: Semantic label maps

## Integration Strategy

### Feature Extraction Pipeline

1. **YOLOv8n**: Fast object counting (pedestrians, vehicles, bicycles)
2. **Detectron2**: Detailed density analysis (pixel-level segmentation)
3. **CLIP**: Semantic scene understanding (context, complexity, conditions)

### Unified Feature Vector

All model outputs are normalized and combined into a standardized feature vector:

- **Spatial Features**: From YOLOv8n and Detectron2 (counts, densities)
- **Visual Complexity**: From Detectron2 masks and CLIP embeddings
- **Semantic Context**: From CLIP similarity scores
- **Temporal Features**: From image metadata (time, day of week)

## References

- Ultralytics YOLOv8 Documentation: https://docs.ultralytics.com
- Detectron2 Documentation: https://detectron2.readthedocs.io
- CLIP Paper: Radford et al., "Learning Transferable Visual Models From Natural Language Supervision" (2021)
- COCO Dataset: https://cocodataset.org
- PASCAL VOC: http://host.robots.ox.ac.uk/pascal/VOC
- KITTI Dataset: http://www.cvlibs.net/datasets/kitti

