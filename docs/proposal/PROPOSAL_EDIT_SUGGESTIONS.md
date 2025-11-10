# Proposal Edit Suggestions

## Summary

Based on current project state and new methodologies developed, the following updates should be made to the proposal.

## 1. Add Fine-Grained Minimax Collection Strategy

### Location: Methodology → Data Collection Section

**Add new subsection after baseline collection:**

```markdown
### Fine-Grained Temporal Collection (Edge Case Analysis)

After establishing baseline collection (every 30 minutes), we implement a 
secondary collection system focused on edge cases—the most and least stressful 
camera zones. This fine-grained collection provides high temporal resolution 
data for measuring dynamic state transitions and pedestrian flow patterns.

**Collection Parameters:**
- **Target Zones:** Top 5 highest stress zones + Bottom 5 lowest stress zones (10 total)
- **Temporal Resolution:** 2-second intervals for 1 minute = 30 frames per camera
- **Frequency:** Every hour
- **Rotation Limit:** Maximum 3 captures per camera per 6-hour period
- **Rationale:** 
  - Edge cases provide most informative data for learning (extremes of distribution)
  - High temporal resolution enables pedestrian flow measurement
  - Dynamic state transition analysis requires temporal sequences
  - Rotation limit ensures diversity and prevents over-sampling

**Expected Output:**
- 300 images per collection (30 frames × 10 cameras)
- 6,000 images/hour from edge cases
- Enhanced feature vectors with temporal coherence metrics
- Pedestrian flow rates and state transition probabilities
```

## 2. Add Empirical Data Structure Definition

### Location: Methodology → Feature Extraction Section

**Add new subsection:**

```markdown
### Empirical Data Structure

We define a standardized empirical data structure for vision model outputs that 
can be embedded into the search algorithm. This structure enables consistent 
feature extraction and integration with learned heuristics.

**Feature Vector Components:**

1. **Spatial Features:**
   - Pedestrian count
   - Vehicle count
   - Crowd density metrics
   - Object density per unit area

2. **Visual Complexity:**
   - Scene complexity scores
   - Visual noise indicators
   - Lighting conditions (day/night/twilight)
   - Weather visibility

3. **Temporal Features:**
   - Time of day encoding (hour, minute)
   - Day of week encoding
   - Historical patterns (moving averages)

4. **Dynamic Metrics (from fine-grained collection):**
   - Pedestrian flow rates (people/second)
   - State transition probabilities
   - Temporal coherence measures
   - Frame-to-frame change metrics

**Vision Models Considered:**
- YOLOv8n (object detection, fast inference)
- Detectron2 (instance segmentation, high accuracy)
- CLIP (scene understanding, semantic features)
- Traffic flow estimation models (specialized for urban analysis)

**Integration Strategy:**
Features are extracted per camera zone and mapped to intersections via 
Voronoi tessellation: `f(intersection) = f(zone(intersection))`
```

## 3. Add Knowledge Base & Pseudocode Design Phase

### Location: Methodology → Algorithm Design Section

**Add before implementation details:**

```markdown
### Knowledge Base & Pseudocode Design

Before implementation, we design the search algorithm architecture through 
pseudocode and knowledge base specification. This design phase ensures 
correct integration of multi-scale resolution and learned heuristics.

**Graph Representation:**
- **Nodes:** 161 intersections (from DCM street centerlines)
- **Edges:** Street segments connecting adjacent intersections
- **Zone Mapping:** Each intersection inherits features from its nearest camera 
  zone via Voronoi tessellation: `zone(n) = argmin_{c} d(n, c)`

**Heuristic Design:**
- **Baseline:** `h_manhattan(n) = |x_n - x_goal| + |y_n - y_goal|`
- **Learned:** `h_learned(n) = w^T * f(zone(n))` where:
  - `f(zone(n))` is the feature vector for the zone containing intersection `n`
  - `w` are learned weights from Ridge regression
  - Feature vector includes spatial, visual, temporal, and dynamic components

**Multi-Scale Resolution:**
- **Camera Zone Level (Coarse):** Stress scores per zone, used for initial 
  heuristic estimation
- **Intersection Level (Fine):** Precise path planning between intersections
- **Combined Analysis:** Pareto front evaluation considers both scales

**Pseudocode Structure:**
```
function A_STAR_SEARCH(start, goal, heuristic):
    open_set = PriorityQueue([start])
    closed_set = Set()
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}
    
    while open_set not empty:
        current = open_set.pop()
        if current == goal:
            return reconstruct_path(came_from, current)
        
        closed_set.add(current)
        for neighbor in get_neighbors(current):
            if neighbor in closed_set:
                continue
            
            tentative_g = g_score[current] + edge_cost(current, neighbor)
            if neighbor not in open_set or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
                if neighbor not in open_set:
                    open_set.add(neighbor)
    
    return None  // No path found
```
```

## 4. Update Figures

### Figures to Add:

1. **Baseline Heatmap** (`baseline_heatmap.png`)
   - Visualization of stress scores across all 82 camera zones
   - Color-coded by stress level (low = green, high = red)
   - Shows spatial distribution of environmental complexity

2. **Fine-Grained Collection Schedule** (`finegrained_schedule.png`)
   - Diagram showing hourly collection with rotation logic
   - Timeline visualization
   - Zone selection process (top/bottom 5)

3. **A* Search Flow** (`astar_flow.png`)
   - Algorithm pseudocode visualization
   - Shows open/closed sets, path reconstruction
   - Integration with learned heuristic

4. **Pareto Front** (`pareto_front.png`)
   - Multi-objective optimization results
   - Distance vs Stress trade-off visualization
   - Non-dominated solutions highlighted

5. **Feature Vector Structure** (`feature_structure.png`)
   - Schema diagram for empirical data format
   - Shows all components (spatial, visual, temporal, dynamic)

### Figures to Update:

1. **Problem Space Map** (`problem_space.png`) - ✅ Already created
2. **Camera Corridor Map** (`camera_corridor_partition.png`) - ✅ Already created

## 5. Update Timeline

### Add Fine-Grained Collection Phase:

**Original Timeline:**
- Weeks 1-2: Baseline collection
- Weeks 3-4: Feature extraction and baseline generation
- Weeks 5-6: A* implementation
- Weeks 7-8: Testing and evaluation

**Updated Timeline:**
- Weeks 1-2: Baseline collection (every 30 min)
- Weeks 3-4: 
  - Feature extraction and baseline generation
  - Deploy fine-grained collection system
- Weeks 5-6: 
  - Process fine-grained data
  - A* implementation
- Weeks 7-8: Testing and evaluation

## 6. Update Expected Results

### Add Fine-Grained Collection Outcomes:

- Enhanced feature vectors with temporal coherence
- Pedestrian flow measurements for edge cases
- State transition probability matrices
- Validation that edge cases provide more informative data for learning

## Implementation Notes

- Fine-grained collection runs in parallel with baseline collection
- Both systems use same camera manifest (82 cameras)
- Fine-grained system dynamically selects zones based on baseline stress scores
- Collection limits prevent resource exhaustion (3 captures per 6-hour period)

