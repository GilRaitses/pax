# Detectron2 Setup

This project uses Detectron2 for instance segmentation through a separate Python 3.12 virtual environment, since Detectron2 is not compatible with Python 3.14.

## Setup

The Detectron2 environment is already set up at `venv_detectron2/`. If you need to recreate it:

```bash
# Create Python 3.12 virtual environment
python3.12 -m venv venv_detectron2

# Activate and install dependencies
source venv_detectron2/bin/activate
pip install --upgrade pip
pip install "torch>=2.0" "torchvision>=0.15"
pip install opencv-python
pip install 'git+https://github.com/facebookresearch/detectron2.git' --no-build-isolation
```

## Usage

The Detectron2 wrapper (`src/pax/vision/detectron2.py`) automatically invokes the separate Python environment. You don't need to manually activate `venv_detectron2` - the wrapper handles it via subprocess.

```python
from pax.vision.detectron2 import Detectron2Wrapper

wrapper = Detectron2Wrapper()
result = wrapper.segment("path/to/image.jpg")
```

## Architecture

- **Main codebase**: Python 3.14 (uses YOLOv8n, CLIP, etc.)
- **Detectron2 environment**: Python 3.12 (only for Detectron2)
- **Communication**: Subprocess invocation of `scripts/detectron2_runner.py`

The `detectron2_runner.py` script runs in the Python 3.12 environment and outputs JSON results that are parsed by the main wrapper.

