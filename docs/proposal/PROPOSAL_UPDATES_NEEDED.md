# Proposal Updates Needed

## New Methods to Add

### 1. Fine-Grained Minimax Collection Strategy

**Section:** Methodology → Data Collection

**Content:**
After establishing baseline collection (every 30 minutes), we implement a secondary collection system focused on edge cases (most and least stressful camera zones). This fine-grained collection provides high temporal resolution data for measuring dynamic state transitions.

**Collection Parameters:**
- **Target Zones:** Top 5 highest stress zones + Bottom 5 lowest stress zones (10 total)
- **Temporal Resolution:** 2-second intervals for 1 minute = 30 frames per camera
- **Frequency:** Every hour
- **Rotation Limit:** Maximum 3 captures per camera per 6-hour period
- **Rationale:** Edge cases provide most informative data for learning, high temporal resolution enables pedestrian flow measurement and dynamic state transition analysis

**Expected Output:**
- 300 images per collection (30 frames × 10 cameras)
- 6,000 images/hour from edge cases
- Enhanced feature vectors with temporal coherence metrics

### 2. Empirical Data Structure Definition

**Section:** Methodology → Feature Extraction

**Content:**
We define a standardized empirical data structure for vision model outputs that can be embedded into the search algorithm. This structure includes:

- **Spatial Features:**
  - Pedestrian count
  - Vehicle count
  - Crowd density metrics
  
- **Visual Complexity:**
  - Scene complexity scores
  - Visual noise indicators
  - Lighting conditions
  
- **Temporal Features:**
  - Time of day encoding
  - Day of week encoding
  - Historical patterns

- **Dynamic Metrics (from fine-grained collection):**
  - Pedestrian flow rates
  - State transition probabilities
  - Temporal coherence measures

**Vision Models Considered:**
- YOLOv8n (object detection)
- Detectron2 (instance segmentation)
- CLIP (scene understanding)
- Traffic flow estimation models

### 3. Knowledge Base & Pseudocode Design Phase

**Section:** Methodology → Algorithm Design

**Content:**
Before implementation, we design the search algorithm architecture through pseudocode and knowledge base specification. This includes:

- **Graph Representation:**
  - Nodes: 161 intersections
  - Edges: Street segments
  - Zone mapping: Intersections → Camera zones
  
- **Heuristic Design:**
  - Baseline: Manhattan distance
  - Learned: `h(n) = w^T * f(zone(n))` where `f(zone(n))` is the feature vector for the zone containing intersection `n`
  
- **Multi-Scale Resolution:**
  - Camera zone level (coarse)
  - Intersection level (fine)
  - Combined analysis for Pareto front

## Figures to Add

1. **Baseline Heatmap:** Visualization of stress scores across all 82 camera zones
2. **Fine-Grained Collection Schedule:** Diagram showing hourly collection with rotation logic
3. **A* Search Flow:** Algorithm pseudocode visualization
4. **Pareto Front:** Multi-objective optimization results visualization
5. **Feature Vector Structure:** Schema diagram for empirical data format

## Sections to Update

1. **Data Collection:** Add fine-grained collection methodology
2. **Feature Extraction:** Add empirical structure definition
3. **Algorithm Design:** Add knowledge base and pseudocode phase
4. **Expected Results:** Update with fine-grained collection outcomes
5. **Timeline:** Adjust for new collection phase

