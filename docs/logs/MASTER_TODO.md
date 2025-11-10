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

**Tasks:**
- [ ] Research leading ML models for vision analysis in urban camera networks
  - YOLOv8n (object detection)
  - Detectron2 (instance segmentation)
  - CLIP (scene understanding)
  - Traffic flow estimation models
- [ ] Define feature vector structure:
  - Pedestrian count
  - Vehicle count
  - Crowd density metrics
  - Visual complexity scores
  - Lighting conditions
  - Weather indicators
  - Temporal features (time of day, day of week)
- [ ] Create schema/documentation for empirical data format
- [ ] Design embedding strategy for search algorithm integration

**Deliverables:**
- Empirical data structure specification document
- Example feature vectors for each camera zone
- Schema validation code

### 1.2 Generate Baselines for Camera Zones

**Objective:** Compute baseline stress/complexity scores for each of the 82 camera zones.

**Tasks:**
- [ ] Collect sufficient data (target: 2 weeks = 672 images/camera)
- [ ] Set up feature extraction pipeline:
  - Vision model integration
  - Batch processing for collected images
  - Feature vector generation
- [ ] Compute baseline metrics per zone:
  - Mean stress score
  - Variance/std deviation
  - Temporal patterns (hourly, daily)
  - Peak/off-peak characteristics
- [ ] Generate baseline report/visualization

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

**Concept:**
- Identify top 5 highest stress score zones (busiest)
- Identify bottom 5 lowest stress score zones (least busy)
- Collect 1 minute of images every 2 seconds = 30 frames per camera
- Run this collection every hour
- Limit: Maximum 3 captures per camera per 6-hour period (prevents over-sampling same zones)

**Rationale:**
- Edge cases provide most informative data for learning
- High temporal resolution (2-second intervals) enables:
  - Pedestrian flow measurement
  - Dynamic state transition metrics
  - Temporal pattern analysis
- Hourly collection captures diurnal patterns
- 6-hour limit ensures diversity across zones

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

**Tasks:**
- [ ] Create pseudocode for:
  - Baseline A* with Manhattan distance heuristic
  - Learned heuristic A* (using Ridge regression weights)
  - Pareto front evaluation
  - Multi-scale resolution handling
- [ ] Design knowledge base structure:
  - How to represent camera zones in search space
  - How to map intersections to zones
  - How to compute edge costs
  - How to apply learned heuristics
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

**Tasks:**
- [ ] Train Ridge regression model:
  - Features: Camera zone feature vectors
  - Target: Stress/complexity scores
  - Cross-validation
- [ ] Implement learned heuristic:
  - `h(n) = w^T * f(zone(n))`
  - Integration with A* search
- [ ] Test learned heuristic A*
- [ ] Compare with baseline

**Deliverables:**
- Learned heuristic implementation
- Trained model weights
- Comparison analysis

### 3.4 Pareto Front Evaluation

**Tasks:**
- [ ] Implement Pareto front computation:
  - Multiple objectives (distance, stress, complexity)
  - Non-dominated solutions
  - Front visualization
- [ ] Evaluate multi-scale resolution:
  - Camera zone level
  - Intersection level
  - Combined analysis
- [ ] Generate Pareto front report

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

