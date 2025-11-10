# Quick Start - Multi-Agent Work Tree

## Fastest Way to Start

### 1. Open Cursor Chat (Cmd/Ctrl + L)

### 2. Copy and paste this prompt:

```
I want to work on BRANCH 1: Vision Model Integration & Feature Extraction.

See agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md for full details.

Let's start with Task 1.1: Set up YOLOv8n for object detection.
- Install ultralytics package
- Create wrapper script in src/pax/vision/yolov8n.py
- Test on sample images from data/raw/images/
- Output: Pedestrian count, vehicle count, bike count
```

### 3. For parallel work, open another chat and use:

```
I want to work on BRANCH 2: Empirical Data Structure Definition.

See agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md for full details.

Let's start with Task 2.2: Design Feature Vector Schema.
- Create Pydantic model in src/pax/schemas/feature_vector.py
- Define spatial, visual, and temporal features
- Document in docs/schemas/feature_vector_spec.md
```

## Available Branches (Can Start Now)

- **BRANCH 1:** Vision Model Integration
- **BRANCH 2:** Empirical Data Structure  
- **BRANCH 4:** Visualization & Analysis

## Branches (Need Features First)

- **BRANCH 3:** Baseline Generation (needs BRANCH 1)
- **BRANCH 5:** Infrastructure (needs BRANCH 1)

## Full Guide

See `CURSOR_MULTI_AGENT_GUIDE.md` for detailed instructions.

