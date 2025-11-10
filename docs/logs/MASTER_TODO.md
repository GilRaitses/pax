# Master TODO - Multi-Scale Signal Processing for Learned Heuristic Pathfinding

**Last Updated:** November 10, 2025  
**Project Status:** Data Collection Phase → Baseline Generation Phase

## Current State

### ✅ Completed Infrastructure

1. **Data Collection System**
   - Cloud Run job deployed (`pax-collector`)
   - Scheduler configured (`pax-collector-schedule`, every 30 minutes)
   - 82 cameras in purple corridor (34th-66th St, 3rd-9th/Amsterdam)
   - Collection rate: 48 images/camera/day
   - IAM permissions configured correctly
   - Timestamps in Eastern Time

2. **Problem Space Definition**
   - Voronoi tessellation complete (82 camera zones)
   - Intersection network: 161 intersections
   - Problem space boundaries: 40th-61st St, Lex-8th/CPW
   - START: Grand Central (42nd & Park)
   - GOAL: Carnegie Hall (57th & 7th Ave)

3. **Visualization**
   - Problem space map (`problem_space.png`)
   - Camera corridor partition map (`camera_corridor_partition.png`)
   - Dashboard with collection statistics

### 📊 Current Collection Status

- **Total Images Collected:** 495 images
- **Average per Camera:** 5.3 images
- **Collection Started:** November 5, 2025
- **Status:** Limited due to initial deployment issues (now resolved)

## Phase 1: Baseline Generation & Empirical Structure

### 1.1 Define Empirical Data Structure

**Objective:** Establish standardized format for vision model outputs that can be embedded into the search algorithm.

**What this means:** When we analyze camera images with computer vision models, we need a consistent way to represent what the models detect (like "5 pedestrians, 2 cars, high crowd density") so the pathfinding algorithm can use this information.

**Tasks:**
- [ ] Research leading ML models for vision analysis in urban camera networks
  - **YOLOv8n:** Fast object detection model that can identify people, cars, bikes in images
  - **Detectron2:** More detailed model that can identify individual objects and their boundaries
  - **CLIP:** Model that understands scene context (e.g., "busy intersection", "quiet street")
  - **Traffic flow estimation models:** Specialized models for measuring how many people/vehicles are moving
- [ ] Define feature vector structure (a list of numbers representing what we see):
  - **Pedestrian count:** How many people are visible
  - **Vehicle count:** How many cars/trucks/bikes
  - **Crowd density metrics:** How crowded the area is (people per square meter)
  - **Visual complexity scores:** How visually "busy" or "noisy" the scene is
  - **Lighting conditions:** Bright, dim, nighttime, etc.
  - **Weather indicators:** Clear, rainy, foggy, etc.
  - **Temporal features:** Time of day (morning rush hour vs. late night), day of week (weekday vs. weekend)
- [ ] Create schema/documentation for empirical data format
- [ ] Design embedding strategy for search algorithm integration (how to convert these features into numbers the pathfinding algorithm can use)

**Deliverables:**
- Empirical data structure specification document
- Example feature vectors for each camera zone
- Schema validation code

### 1.2 Generate Baselines for Camera Zones

**Objective:** Compute baseline stress/complexity scores for each of the 82 camera zones.

**What this means:** For each camera zone, we calculate an average "stress score" that represents how difficult/complex it is to navigate through that area. This becomes our baseline (starting point) for comparison.

**Tasks:**
- [ ] Collect sufficient data (target: 2 weeks = 672 images/camera)
- [ ] Set up feature extraction pipeline:
  - **Vision model integration:** Connect computer vision models to analyze images
  - **Batch processing:** Process many images at once efficiently
  - **Feature vector generation:** Extract the list of numbers (features) from each image
- [ ] Compute baseline metrics per zone:
  - **Mean stress score:** Average difficulty/complexity for this zone
  - **Variance/std deviation:** How much the stress varies (is it consistently busy or sometimes quiet?)
  - **Temporal patterns:** How stress changes throughout the day (rush hour vs. off-peak)
  - **Peak/off-peak characteristics:** When is this zone most/least stressful?
- [ ] Generate baseline report/visualization (heatmap showing stress levels across all zones)

**Deliverables:**
- Baseline scores for all 82 camera zones
- Baseline visualization (heatmap, time series)
- Baseline data file (JSON/YAML)

**Dependencies:**
- Empirical data structure defined (1.1)
- Sufficient collection data (2 weeks)

## Phase 2: Fine-Grained Temporal Collection (Minimax Edge Cases)

### 2.1 Design Minimax Collection Strategy

**Objective:** Collect high temporal resolution data from edge cases (most/least stressful zones) to measure dynamic state transitions.

**What "minimax" means:** We focus on the extremes (minimum and maximum stress zones) because these provide the most useful information for learning. The busiest zones show us what makes navigation difficult, and the quietest zones show us what makes it easy.

**What "dynamic state transitions" means:** How the scene changes over time - for example, watching how many people enter/exit an intersection over 1 minute tells us about pedestrian flow patterns.

**Concept:**
- Identify top 5 highest stress score zones (busiest/most complex)
- Identify bottom 5 lowest stress score zones (least busy/quietest)
- Collect 1 minute of images every 2 seconds = 30 frames per camera (like a short video)
- Run this collection every hour
- Limit: Maximum 3 captures per camera per 6-hour period (prevents over-sampling same zones)

**Rationale:**
- Edge cases provide most informative data for learning (extremes teach us more than averages)
- High temporal resolution (2-second intervals) enables:
  - **Pedestrian flow measurement:** Count how many people move through an area per second
  - **Dynamic state transition metrics:** Measure how the scene changes (e.g., "crowd builds up, then disperses")
  - **Temporal pattern analysis:** Understand how conditions evolve over time
- Hourly collection captures diurnal patterns (how conditions change throughout the day)
- 6-hour limit ensures diversity across zones (we don't keep collecting from the same 5 cameras all day)

**Tasks:**
- [ ] Implement stress score calculation from baseline data
- [ ] Create zone ranking system (top/bottom 5)
- [ ] Design collection schedule:
  - Hourly trigger
  - 2-second interval capture (30 frames over 1 minute)
  - 6-hour rotation logic
- [ ] Create secondary Cloud Run job for fine-grained collection
- [ ] Deploy and test collection system

**Deliverables:**
- Secondary collection job (`pax-collector-finegrained`)
- Collection scheduler with rotation logic
- Edge case dataset (300 images per collection × 2 collections/hour × 10 cameras = 6,000 images/hour)

**Dependencies:**
- Baseline generation complete (Phase 1.2)
- Stress score calculation implemented

### 2.2 Process Fine-Grained Data

**Tasks:**
- [ ] Extract features from 30-frame sequences
- [ ] Compute dynamic metrics:
  - Pedestrian flow rates
  - State transition probabilities
  - Temporal coherence measures
- [ ] Integrate with baseline scores
- [ ] Create enhanced feature vectors

**Deliverables:**
- Enhanced feature dataset
- Dynamic metrics per edge case zone
- Integration with baseline data

## Phase 3: A* Search Implementation

### 3.1 Pseudocode & Knowledge Base Design

**Objective:** Design the search algorithm architecture before implementation.

**What "pseudocode" means:** Step-by-step description of the algorithm in plain language (not actual code), like a recipe for how the pathfinding will work.

**What "knowledge base" means:** A structured way to store and access information about the map - which intersections connect to which, which camera zones cover which areas, etc.

**Tasks:**
- [ ] Create pseudocode for:
  - **Baseline A* with Manhattan distance heuristic:** Standard pathfinding using only distance (like "how many blocks away?")
  - **Learned heuristic A* (using Ridge regression weights):** Pathfinding that uses learned patterns from camera data (like "this area is usually stressful, avoid it")
  - **Pareto front evaluation:** Finding paths that balance multiple goals (shortest distance vs. lowest stress)
  - **Multi-scale resolution handling:** Using both camera zones (coarse) and intersections (fine) in the search
- [ ] Design knowledge base structure:
  - How to represent camera zones in search space (each zone = a region with a stress score)
  - How to map intersections to zones (which camera zone covers which intersection?)
  - How to compute edge costs (how "expensive" is it to move from one intersection to another?)
  - How to apply learned heuristics (use stress scores to guide pathfinding)
- [ ] Document algorithm flow and decision points

**Deliverables:**
- Pseudocode document
- Knowledge base schema
- Algorithm design document

### 3.2 Implement Baseline A* Search

**Tasks:**
- [ ] Implement graph structure:
  - Nodes: 161 intersections
  - Edges: Street segments between intersections
  - Edge weights: Manhattan distance
- [ ] Implement A* algorithm:
  - Open/closed sets
  - Priority queue
  - Path reconstruction
- [ ] Test with Grand Central → Carnegie Hall
- [ ] Generate baseline path and metrics

**Deliverables:**
- Baseline A* implementation
- Baseline path visualization
- Performance metrics

### 3.3 Implement Learned Heuristic A*

**What "Ridge regression" means:** A machine learning technique that learns to predict stress scores from camera features. It's like teaching a computer: "when you see these features (many pedestrians, high visual complexity), predict a high stress score."

**How Ridge Regression Works:**
1. **Training data:** We have many examples of camera images with known stress scores (or we compute stress from features)
2. **Learning:** The model finds weights (numbers) that best predict stress from features
3. **Formula:** `predicted_stress = weight₁ × pedestrian_count + weight₂ × vehicle_count + weight₃ × complexity + ... + bias`
4. **Ridge part:** Prevents overfitting (memorizing training data instead of learning patterns) by penalizing very large weights

**Tasks:**
- [ ] Train Ridge regression model:
  - **Features:** Camera zone feature vectors (the numbers we extract from images)
  - **Target:** Stress/complexity scores (what we're trying to predict)
  - **Cross-validation:** Test the model on data it hasn't seen to make sure it generalizes well
- [ ] Implement learned heuristic:
  - **Formula:** `h(n) = w^T * f(zone(n))` 
    - `h(n)` = predicted stress for intersection `n`
    - `w^T` = learned weights (from Ridge regression)
    - `f(zone(n))` = feature vector for the camera zone containing intersection `n`
  - **Integration with A* search:** Use this predicted stress to guide pathfinding (avoid high-stress zones)
- [ ] Test learned heuristic A*
- [ ] Compare with baseline (does learned heuristic find better paths than distance-only?)

**Deliverables:**
- Learned heuristic implementation
- Trained model weights
- Comparison analysis

### 3.4 Pareto Front Evaluation

**What "Pareto front" means:** When you have multiple goals (like "shortest distance" AND "lowest stress"), you can't always optimize both at once. The Pareto front is the set of paths where you can't improve one goal without making the other worse. These are the "best compromise" solutions.

**Example:** 
- Path A: 10 blocks, stress score 8 (short but stressful)
- Path B: 12 blocks, stress score 3 (longer but calm)
- Path C: 11 blocks, stress score 4 (compromise)

Path C is on the Pareto front if there's no other path that's both shorter AND less stressful.

**What "non-dominated solutions" means:** Solutions where you can't find another solution that's better in ALL objectives. If Path A is shorter but Path B is less stressful, neither "dominates" the other - they're both valid options.

**Tasks:**
- [ ] Implement Pareto front computation:
  - **Multiple objectives:** Balance distance (shorter is better) vs. stress (lower is better) vs. complexity (simpler is better)
  - **Non-dominated solutions:** Find all paths where you can't improve one objective without hurting another
  - **Front visualization:** Plot showing the trade-off curve (distance vs. stress)
- [ ] Evaluate multi-scale resolution:
  - **Camera zone level:** Coarse analysis using zone-level stress scores
  - **Intersection level:** Fine-grained analysis at individual intersections
  - **Combined analysis:** Use both scales together for Pareto front
- [ ] Generate Pareto front report (showing all optimal compromise paths)

**Deliverables:**
- Pareto front implementation
- Multi-scale analysis results
- Visualization and report

## Phase 4: AI Agent Design & Testing

### 4.1 Agent Architecture

**Tasks:**
- [ ] Design agent decision-making framework
- [ ] Integrate learned heuristics
- [ ] Implement path selection logic
- [ ] Design evaluation metrics

**Deliverables:**
- Agent architecture document
- Implementation code
- Test suite

### 4.2 Testing & Evaluation

**Tasks:**
- [ ] Run comprehensive tests:
  - Multiple start/goal pairs
  - Different time periods
  - Edge cases
- [ ] Compare performance:
  - Baseline A* vs Learned A*
  - Different heuristic weights
  - Multi-scale vs single-scale
- [ ] Generate evaluation report

**Deliverables:**
- Test results
- Performance comparison
- Evaluation report

## Implementation Priority

### Immediate (Next 1-2 Weeks)
1. ✅ Complete data collection (2 weeks of baseline data)
2. Define empirical data structure (1.1)
3. Research vision models for urban analysis
4. Design pseudocode and knowledge base (3.1)

### Short Term (Weeks 3-4)
1. Generate baselines for camera zones (1.2)
2. Implement baseline A* search (3.2)
3. Set up fine-grained collection system (2.1)

### Medium Term (Weeks 5-6)
1. Process fine-grained data (2.2)
2. Train learned heuristic model
3. Implement learned heuristic A* (3.3)

### Long Term (Weeks 7-8)
1. Implement Pareto front evaluation (3.4)
2. Design and test AI agent (4.1, 4.2)
3. Final evaluation and report

## Notes

### Fine-Grained Collection Rationale

The minimax edge case collection strategy addresses a key limitation: baseline collection (every 30 minutes) provides good coverage but limited temporal resolution. By focusing on the most and least stressful zones with high temporal resolution (2-second intervals), we can:

1. **Measure Dynamic State Transitions:** 30-frame sequences enable flow analysis
2. **Capture Edge Cases:** Most informative for learning (extremes of the distribution)
3. **Maintain Diversity:** 6-hour rotation prevents over-sampling
4. **Efficient Resource Use:** Only 10 cameras per hour (vs 82 every 30 min)

This approach is not in the original proposal but emerged as a natural extension once baseline collection was established. It should be documented as an enhancement to the methodology.

### Knowledge Base Approach

The pseudocode and knowledge base design phase is critical because:
- The problem involves multiple scales (zones vs intersections)
- Learned heuristics need careful integration
- Pareto front evaluation requires clear objective definitions
- The agent needs a structured decision framework

This design phase should precede implementation to avoid architectural issues.

## Dependencies Graph

```
Data Collection (2 weeks)
    ↓
Empirical Structure Definition (1.1)
    ↓
Baseline Generation (1.2)
    ↓
    ├─→ Fine-Grained Collection (2.1)
    │       ↓
    │   Fine-Grained Processing (2.2)
    │
    └─→ Pseudocode & Knowledge Base (3.1)
            ↓
        Baseline A* (3.2)
            ↓
        Learned Heuristic Training
            ↓
        Learned A* (3.3)
            ↓
        Pareto Front (3.4)
            ↓
        Agent Design (4.1)
            ↓
        Testing (4.2)
```

## Detailed Explanations

### Ridge Regression Explained

**What it is:** A machine learning technique that learns to predict a number (stress score) from multiple inputs (features like pedestrian count, vehicle count, etc.).

**How it works:**
1. **Training phase:** We feed the model many examples: "This image has 10 pedestrians, 5 cars, high complexity → stress score 7.5"
2. **Learning:** The model finds weights (coefficients) that best fit the data
3. **Prediction:** For a new image, multiply features by weights and sum: `stress = 0.3×pedestrians + 0.2×vehicles + 0.5×complexity + ...`
4. **Ridge regularization:** Prevents overfitting by keeping weights small (penalizes extreme values)

**Why Ridge (not other methods):**
- Simple and interpretable (you can see which features matter most)
- Works well with many features
- Prevents overfitting (memorizing training data)
- Fast to train and use

**In our context:**
- **Input:** Feature vector from camera zone (pedestrian count, vehicle count, complexity, etc.)
- **Output:** Predicted stress score for that zone
- **Use:** Guide A* search to avoid high-stress zones

### Pareto Front Explained

**The Problem:** We want paths that are BOTH short AND low-stress, but these goals conflict. A direct route might be stressful (busy streets), while a calm route might be longer.

**Pareto Optimality:** A solution is "Pareto optimal" if you can't improve one objective without making another worse.

**Example with 3 paths:**
- Path 1: 10 blocks, stress 8 → Not Pareto optimal (Path 3 is better in both)
- Path 2: 15 blocks, stress 2 → Not Pareto optimal (Path 3 is better in both)  
- Path 3: 12 blocks, stress 4 → Pareto optimal (no other path is both shorter AND less stressful)

**The Pareto Front:** The set of all Pareto optimal solutions. It shows the trade-off curve: "If you want lower stress, you must accept longer distance (and vice versa)."

**Visualization:** A scatter plot where:
- X-axis = distance
- Y-axis = stress
- Each point = a path
- Pareto front = the "lower-left boundary" (shortest distance for each stress level)

**Multi-Objective:** We can have more than 2 objectives:
- Distance (minimize)
- Stress (minimize)
- Complexity (minimize)
- Time (minimize)

The Pareto front becomes a multi-dimensional surface showing all optimal trade-offs.

**In our context:**
- Find all paths from Grand Central to Carnegie Hall
- Score each path on multiple objectives
- Identify Pareto optimal paths (the "best compromises")
- Present user with options: "Do you prefer shortest distance or lowest stress?"

## Open Questions

1. **Vision Model Selection:** Which models provide best features for urban stress estimation?
2. **Feature Engineering:** What temporal features are most predictive?
3. **Heuristic Weighting:** How to balance distance vs stress in learned heuristic?
4. **Pareto Objectives:** What are the exact objectives for Pareto front (distance, stress, time, complexity)?
5. **Evaluation Metrics:** How to measure "better" paths (user studies? simulation? proxy metrics?)

## References

- Original Proposal: `docs/proposal/CIS667_TermProject_Proposal_Final.qmd`
- Problem Space Visualization: `docs/figures/problem_space.png`
- Camera Corridor Visualization: `docs/figures/camera_corridor_partition.png`
- Daily Logs: `docs/logs/YYYY-MM-DD.md`

