# CIS 667 Term Project Proposal

**Title:** Adaptive Heuristic Learning for Stress-Optimized Pedestrian Navigation: An AI-Driven Approach to Urban Routing

**Student:** Gil Raitses  
**Email:** graitses@syr.edu  
**Course:** CIS 667 - Introduction to Artificial Intelligence  
**Instructor:** Prof. Andrew C. Lee  
**Date:** October 27, 2025  
**Institution:** Syracuse University

---

## 1. Introduction

### 1.1 Subject Area within Artificial Intelligence

This project operates within the **informed search and heuristic learning** domain of artificial intelligence, specifically focusing on:
- **Heuristic search algorithms** (A*, weighted A*, and variants)
- **Machine learning for heuristic optimization** (adaptive heuristic functions)
- **Multi-objective optimization** (path quality vs. computational efficiency)
- **Reinforcement learning** for dynamic environment adaptation

### 1.2 Problem Statement

Traditional pedestrian navigation systems optimize for the shortest path or fastest route, treating all streets as equivalent modulo distance and time. However, urban pedestrians experience significant variation in **psychological stress** and **safety conditions** across different routes. Factors such as:
- Sidewalk cycling violations
- Pedestrian density and bottlenecks
- Infrastructure quality
- Real-time safety violations

...create a need for **stress-optimized routing** that balances travel time against mental well-being and physical safety.

The core AI challenge is: **How can we design adaptive heuristic functions that learn to optimize for multiple conflicting objectives (speed, safety, stress-reduction) while maintaining computational tractability for real-time urban navigation?**

Existing approaches face three critical limitations:

1. **Static Heuristics**: Traditional A* implementations use fixed heuristics (Manhattan distance, straight-line distance) that cannot adapt to changing urban conditions or user preferences

2. **No Stress Modeling**: Current navigation systems lack quantitative models for pedestrian stress factors, making it impossible to optimize for mental well-being alongside traditional metrics

3. **Computational Tractability**: Multi-objective optimization in large urban graphs (900+ nodes in NYC) requires careful heuristic design to remain computationally feasible for real-time applications

---

## 2. Aim of the Project

**To develop and empirically validate an adaptive heuristic learning framework for stress-optimized pedestrian navigation that integrates:**

1. **Path sampling techniques** to explore the solution space of multi-objective urban routes
2. **Heuristic learning algorithms** that adapt to user preferences and real-time conditions
3. **Adaptive regularization mechanisms** that balance solution quality against computational efficiency

The system will be implemented and tested using the **NYC Vibe Check** infrastructure, which provides:
- 907 camera zones with Voronoi tessellation coverage across all 5 NYC boroughs
- Real-time safety violation detection via Google Cloud Vision and Gemini AI
- BigQuery ML pipeline with 103+ records of historical route analysis data
- Existing pedestrian route service with reinforcement learning pathfinding baseline

---

## 3. Objectives

### 3.1 Technical Implementation Objectives

**Objective 1: Design and Implement Path Sampling Framework**
- Implement Monte Carlo path sampling to explore diverse route options beyond greedy best-first search
- Develop systematic sampling strategies (uniform, importance-weighted, Thompson sampling)
- Create evaluation metrics to measure sample diversity and solution space coverage
- **Success Metric:** Generate 50-100 diverse candidate routes per query with measurable quality variation

**Objective 2: Develop Adaptive Heuristic Learning System**
- Implement base heuristics: Euclidean distance, Manhattan distance, learned stress-function
- Design machine learning system to combine base heuristics adaptively using:
  - Linear weighted combination with learned weights
  - Neural network approximation of complex non-linear heuristics
  - Online learning from user feedback and route selections
- **Success Metric:** Achieve 15-25% improvement in user-preferred route discovery compared to static A* baseline

**Objective 3: Implement Adaptive Regularization Mechanisms**
- Design weight parameter adaptation inspired by weighted A* (W ∈ [1.0, 2.0])
- Implement dynamic regularization that adjusts search intensity based on:
  - Query complexity (start-to-goal distance)
  - Real-time computational constraints
  - Solution quality requirements
- **Success Metric:** Reduce computation time by 30-60% while maintaining 90%+ solution quality

**Objective 4: Integration with NYC Vibe Check Infrastructure**
- Integrate with existing 939-camera monitoring system for real-time stress factor data
- Leverage BigQuery ML infrastructure for heuristic function training
- Deploy through Firebase Cloud Functions for scalable real-time routing
- **Success Metric:** Successfully process routing queries with <3-second response time

### 3.2 Empirical Evaluation Objectives

**Objective 5: Comparative Algorithm Analysis**
- Compare performance across algorithms:
  - Baseline: Standard A* with Euclidean heuristic
  - Weighted A* (W = 1.0, 1.2, 1.5, 2.0) - following Programming Problem 3 methodology
  - Adaptive heuristic A* (learned weights)
  - Path sampling with adaptive regularization (proposed system)
- Metrics: Solution quality, nodes expanded, computation time, user satisfaction
- **Success Metric:** Statistical significance (p < 0.05) in at least 3 of 4 metrics

**Objective 6: Real-World Validation**
- Test on actual NYC pedestrian routing scenarios using live camera data
- Validate stress predictions against crowdsourced safety reports
- Measure system performance across different times of day and weather conditions
- **Success Metric:** 75%+ agreement between predicted stress levels and user reports

### 3.3 Theoretical Analysis Objectives

**Objective 7: Admissibility and Consistency Analysis**
- Prove or establish empirical bounds on heuristic admissibility for learned functions
- Analyze trade-offs between heuristic informativeness and admissibility
- Study optimality guarantees under adaptive regularization
- **Success Metric:** Formal characterization of optimality conditions for proposed algorithms

**Objective 8: Scalability Analysis**
- Measure algorithm performance across graph sizes (100, 500, 907 nodes)
- Analyze computational complexity as function of sampling parameters
- Identify bottlenecks and optimization opportunities
- **Success Metric:** Establish O(·) complexity bounds and validate empirically

---

## 4. Methodology

### 4.1 Algorithm Design

#### 4.1.1 Path Sampling Framework

**Monte Carlo Path Sampling:**
```python
def sample_paths(start, goal, num_samples, sampling_strategy):
    """
    Generate diverse path samples using stochastic search
    
    Sampling Strategies:
    - Uniform: Random walk with goal-directed bias
    - Importance-weighted: Sample proportional to heuristic promise
    - Thompson sampling: Balance exploration/exploitation
    """
    samples = []
    for i in range(num_samples):
        path = stochastic_search(start, goal, strategy=sampling_strategy)
        score = evaluate_path(path, objectives=['distance', 'stress', 'safety'])
        samples.append((path, score))
    return pareto_optimal_subset(samples)
```

**Diversity Mechanism:**
- Introduce controlled randomness in action selection
- Penalize paths that overlap with previously sampled routes
- Use temperature parameter to control exploration-exploitation tradeoff

#### 4.1.2 Heuristic Learning System

**Base Heuristics:**
1. **Geometric Heuristic**: h_geo(n) = Euclidean_distance(n, goal)
2. **Stress Heuristic**: h_stress(n) = ∑(zone_stress_scores along estimated path)
3. **Safety Heuristic**: h_safety(n) = violation_count(n, goal)

**Learned Combination:**
```python
h_learned(n, goal, user_prefs) = w1·h_geo(n) + w2·h_stress(n) + w3·h_safety(n)
```

Where weights {w1, w2, w3} are learned through:
- **Offline Training**: BigQuery ML models trained on historical route preferences
- **Online Adaptation**: Gradient descent updates based on user feedback
- **Regularization**: L2 penalty to prevent overfitting to individual preferences

**Neural Network Heuristic (Advanced):**
```python
h_nn(n, goal, context) = NeuralNet(
    inputs=[position(n), position(goal), time_of_day, 
            weather, recent_violations, user_history],
    architecture=[64, 32, 16, 1],
    activation='ReLU'
)
```

#### 4.1.3 Adaptive Regularization

**Dynamic Weight Parameter (inspired by Weighted A*):**
```python
def adaptive_weight(query_context):
    """
    Dynamically adjust heuristic weight based on query characteristics
    W = 1.0: Optimal solution guaranteed (when heuristic is admissible)
    W > 1.0: Faster search, potential optimality loss
    """
    base_weight = 1.2  # Sweet spot from Programming Problem 3
    
    # Adjust based on urgency
    if query_context['urgency'] == 'high':
        weight = 1.5  # Faster computation
    
    # Adjust based on graph complexity
    if query_context['path_length_estimate'] > 10:
        weight = 1.3  # More aggressive pruning for long paths
    
    # Adjust based on solution quality requirements
    if query_context['quality_threshold'] > 0.95:
        weight = 1.0  # Near-optimal required
    
    return weight
```

**Computational Budget Management:**
- Set maximum nodes expanded based on real-time constraints
- Implement anytime algorithm properties: return best solution found when budget exhausted
- Use iterative deepening with progressively relaxed heuristics

### 4.2 Integration with NYC Vibe Check System

**Data Sources:**
1. **Camera Network**: 939 zones with Voronoi tessellation
2. **Violation Detection**: Real-time sidewalk cycling, pedestrian safety violations
3. **BigQuery ML**: Historical route analysis, violation patterns
4. **Weather API**: Real-time conditions affecting route stress
5. **User Reports**: Crowdsourced safety and stress feedback

**System Architecture:**
```
User Query → Firebase Cloud Function → Adaptive Heuristic Router
                                              ↓
                    ← Route Options ← Path Sampling Engine
                                              ↓
                                     Heuristic Learning Module
                                              ↓
                                    BigQuery ML (training data)
                                              ↓
                                    Real-time Violation Data (939 cameras)
```

### 4.3 Experimental Design

**Dataset:**
- **Training Set**: 75 historical route queries from BigQuery ML database
- **Test Set**: 25 new route queries with ground truth user preferences
- **Validation**: 50 synthetic scenarios spanning all 5 NYC boroughs

**Baseline Algorithms:**
1. Standard A* with Euclidean distance
2. Standard A* with Manhattan distance
3. Weighted A* (W = 1.2) - best from Programming Problem 3
4. Greedy Best-First Search
5. Dijkstra's algorithm (optimal baseline)

**Performance Metrics:**
1. **Solution Quality**: Path length, stress score, safety score, user preference match
2. **Computational Efficiency**: Nodes expanded, CPU time, memory usage
3. **Optimality Gap**: Comparison to Dijkstra's optimal solution
4. **User Satisfaction**: Survey ratings on deployed routes (if time permits)

**Statistical Analysis:**
- Paired t-tests comparing proposed system to each baseline
- ANOVA across all algorithms
- Effect size calculations (Cohen's d)
- Significance threshold: p < 0.05

### 4.4 Implementation Technologies

**Programming Languages:**
- Python 3.11+ for algorithm implementation and ML training
- TypeScript for Firebase Cloud Functions integration
- SQL for BigQuery ML model training

**Key Libraries:**
- **Search Algorithms**: Custom implementation (following AIMA patterns from course)
- **ML Framework**: scikit-learn for baseline models, TensorFlow for neural network heuristics
- **Data Processing**: pandas, numpy for analysis
- **Visualization**: matplotlib, seaborn for results presentation
- **Graph Structures**: networkx for route graph representation

**Infrastructure:**
- Firebase Cloud Functions (existing vibe-check deployment)
- BigQuery ML (existing 103+ route records)
- Google Cloud Vision (existing 939-camera integration)
- Firestore (real-time violation data storage)

---

## 5. Expected Outcomes and Contributions

### 5.1 Practical Contributions

1. **Working System**: Deployed pedestrian routing service on NYC Vibe Check platform
2. **Real-World Impact**: Help pedestrians avoid high-stress routes in actual NYC navigation
3. **Scalable Architecture**: Framework applicable to other cities with camera infrastructure
4. **Open Source**: Code and models released for community use and research

### 5.2 Theoretical Contributions

1. **Novel Algorithm**: Adaptive heuristic learning framework combining path sampling and regularization
2. **Empirical Analysis**: Comprehensive comparison of heuristic adaptation strategies
3. **Trade-off Characterization**: Formal analysis of optimality vs. efficiency trade-offs
4. **Admissibility Bounds**: Theoretical results on learned heuristic properties

### 5.3 Educational Outcomes

1. **Course Concepts Application**: Direct application of A*, heuristics, informed search from CIS 667
2. **Extension Beyond Coursework**: Novel integration of ML and classical AI search
3. **Real-World Problem Solving**: Addressing practical urban navigation challenges
4. **Research Skills Development**: Experimental design, statistical analysis, technical writing

---

## 6. Project Timeline and Milestones

### Week 1-2: Literature Review and System Design (Nov 1-14)
- Review relevant papers on heuristic learning and path sampling
- Finalize algorithm designs and implementation specifications
- Set up development environment and testing framework
- **Deliverable**: Detailed design document

### Week 3-4: Core Algorithm Implementation (Nov 15-28)
- Implement path sampling framework with 3 sampling strategies
- Develop base heuristic functions (geometric, stress, safety)
- Create heuristic learning module with weight adaptation
- **Deliverable**: Working prototype with basic functionality

### Week 5-6: Integration and Testing (Nov 29 - Dec 12)
- Integrate with NYC Vibe Check infrastructure (939 cameras, BigQuery ML)
- Implement adaptive regularization mechanisms
- Conduct preliminary testing on synthetic scenarios
- **Deliverable**: Integrated system ready for evaluation

### Week 7-8: Experiments and Analysis (Dec 13-26)
- Run comprehensive experiments comparing all algorithms
- Collect performance data across all metrics
- Perform statistical analysis of results
- **Deliverable**: Complete experimental results dataset

### Week 9-10: Final Report and Documentation (Dec 27 - Jan 9)
- Write final project report following academic standards
- Create presentation materials
- Document code and release open source
- **Deliverable**: Final report, presentation, and code repository

**Key Milestones:**
- ✅ **Proposal Approved** (Nov 1)
- 🎯 **Design Complete** (Nov 14)
- 🎯 **Prototype Working** (Nov 28)
- 🎯 **Integration Complete** (Dec 12)
- 🎯 **Experiments Complete** (Dec 26)
- 🎯 **Final Report Submitted** (Jan 9)

---

## 7. Risk Management

### Potential Challenges and Mitigation Strategies

**Challenge 1: Heuristic Learning May Not Improve Performance**
- **Risk**: Learned heuristics perform worse than static baselines
- **Mitigation**: Start with proven weighted A* approach from Programming Problem 3; incremental improvements

**Challenge 2: Computational Complexity Too High**
- **Risk**: Path sampling too expensive for real-time use
- **Mitigation**: Implement aggressive pruning; use precomputed route templates; fallback to faster algorithms

**Challenge 3: Limited Training Data**
- **Risk**: 103 route records insufficient for ML training
- **Mitigation**: Generate synthetic training data; use transfer learning; simulate user preferences

**Challenge 4: Integration Difficulties**
- **Risk**: NYC Vibe Check API changes or unavailable
- **Mitigation**: Fallback to synthetic graph data; use cached violation data; standalone implementation

**Challenge 5: Time Constraints**
- **Risk**: Cannot complete all objectives in 10 weeks
- **Mitigation**: Prioritize core objectives 1-3; advanced features (neural nets) as stretch goals

---

## 8. References

### Core Course Materials
1. Russell, S., & Norvig, P. (2020). *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson. 
   - Chapters 3 (Solving Problems by Searching) and 4 (Search in Complex Environments)

### Heuristic Learning
2. Samadi, M., Felner, A., & Schaeffer, J. (2008). Learning from multiple heuristics. *AAAI*, 8, 357-362.
3. Thayer, J. T., & Ruml, W. (2011). Bounded suboptimal search: A direct approach using inadmissible estimates. *IJCAI*, 11, 674-679.

### Path Sampling and Monte Carlo Methods
4. Kocsis, L., & Szepesvári, C. (2006). Bandit based monte-carlo planning. *European Conference on Machine Learning*, 282-293.
5. Silver, D., et al. (2016). Mastering the game of Go with deep neural networks and tree search. *Nature*, 529(7587), 484-489.

### Multi-Objective Routing
6. Geisberger, R., & Sanders, P. (2010). Engineering multilevel overlay graphs for shortest-path queries. *Journal of Experimental Algorithmics*, 15, 2-5.
7. Delling, D., Goldberg, A. V., & Werneck, R. F. (2015). Hub labeling (preprint). In *Encyclopedia of Algorithms*, 1-6.

### Urban Navigation and Stress Modeling
8. Quercia, D., Schifanella, R., & Aiello, L. M. (2014). The shortest path to happiness: Recommending beautiful, quiet, and happy routes in the city. *ACM HyperText*, 116-125.
9. Galbrun, E., Pelechrinis, K., & Terzi, E. (2016). Urban navigation beyond shortest route. *Information Systems*, 57, 160-171.

### Weighted A* and Suboptimal Search
10. Pohl, I. (1970). Heuristic search viewed as path finding in a graph. *Artificial Intelligence*, 1(3-4), 193-204.
11. Hansen, E. A., & Zhou, R. (2007). Anytime heuristic search. *Journal of Artificial Intelligence Research*, 28, 267-297.

### Machine Learning for Route Optimization
12. Duan, Y., Lv, Y., & Wang, F. Y. (2016). Travel time prediction with LSTM neural network. *IEEE ITSC*, 1053-1058.
13. Dai, H., Khalil, E. B., Zhang, Y., Dilkina, B., & Song, L. (2017). Learning combinatorial optimization algorithms over graphs. *NeurIPS*, 6348-6358.

---

## 9. Project Classification

**Primary Category:** Applied Project (Category d from proposal guidelines)

This project aims to gain experience from learning and applying known methods (A*, weighted A*, heuristic search) to a realistic situation (NYC pedestrian navigation), while also incorporating machine learning techniques for heuristic adaptation. The project will:

1. Apply established search algorithms to real NYC camera network data
2. Analyze and summarize experiences with different heuristic strategies
3. Identify refinements and optimizations specific to urban navigation
4. Validate approaches through empirical testing on actual city infrastructure

**Secondary Aspects:**
- **Comparison Study** (Category c): Comparative analysis of multiple heuristic adaptation approaches
- **Theoretical Analysis** (Category b): Admissibility and optimality analysis of learned heuristics

---

## 10. Alignment with Course Learning Objectives

This project directly addresses multiple CIS 667 learning objectives:

### Problem Solving Agent (Goal-based Agent) ✅
- **Method**: Uninformed and informed search (DFS, A*, weighted A*)
- **Application**: Finding optimal paths in NYC route graph
- **Extension**: Adaptive heuristics and multi-objective optimization

### Intelligent Agent Types ✅
- **Simple Reflex**: Base violation detection (if bike_violation then flag_unsafe)
- **Model-based**: Maintain belief state about current safety conditions
- **Goal-based**: Path planning to reach destination
- **Utility-based**: Multi-objective optimization (speed + safety + stress)

### Learning Agent ✅
- **Performance Element**: Heuristic function for route quality
- **Learning Element**: Weight adaptation from user feedback
- **Critic**: User satisfaction ratings
- **Problem Generator**: Exploration vs. exploitation in route sampling

### Course Topics Integrated
1. **Uninformed Search**: Baseline Dijkstra's algorithm
2. **Informed Search**: A*, weighted A*, greedy best-first
3. **Heuristic Design**: Multiple admissible and inadmissible heuristics
4. **Optimization**: Balancing solution quality and computational cost
5. **Real-World Application**: Addressing actual urban navigation challenges

---

## Appendix A: Technical Specifications

### A.1 NYC Vibe Check Infrastructure Details

**Camera Network:**
- 907 active camera zones across all 5 NYC boroughs
- Complete Voronoi tessellation coverage (3,626 km²)
- Real-time violation detection via Google Cloud Vision API
- Update frequency: 24-hour baseline with adaptive escalation

**Data Infrastructure:**
- Firebase Cloud Functions (TypeScript backend)
- Firestore database (real-time NoSQL storage)
- BigQuery ML (training and analytics)
- 103+ route analysis records with ground truth

**AI Processing Pipeline:**
- Gemini AI for contextual scene understanding
- Google Cloud Vision for object detection
- Adaptive monitoring engine for escalation
- Redis caching for performance optimization

### A.2 Graph Representation

**Nodes:** 907 camera zones (Voronoi cells)

**Edges:** Adjacency based on Voronoi neighbor relationships

**Node Attributes:**
- `position`: (latitude, longitude) coordinates
- `safety_score`: Real-time safety rating (1-10 scale)
- `stress_factors`: [pedestrian_density, violations, infrastructure_quality]
- `recent_violations`: Time-series of detected violations

**Edge Attributes:**
- `distance`: Euclidean distance between zone centers
- `estimated_time`: Walking time estimate
- `stress_score`: Accumulated stress along segment

### A.3 Heuristic Function Details

**Euclidean Distance (Admissible):**
```python
def h_euclidean(node, goal):
    return sqrt((node.lat - goal.lat)^2 + (node.lng - goal.lng)^2)
```

**Manhattan Distance (Admissible in grid):**
```python
def h_manhattan(node, goal):
    return abs(node.lat - goal.lat) + abs(node.lng - goal.lng)
```

**Stress-Aware Distance (Learned):**
```python
def h_stress(node, goal, learned_weights):
    geometric_distance = h_euclidean(node, goal)
    estimated_stress = predict_path_stress(node, goal)
    return w1 * geometric_distance + w2 * estimated_stress
```

### A.4 Evaluation Metrics Formulas

**Solution Quality Score:**
```
Q(path) = w1·normalized_distance(path) + 
          w2·normalized_stress(path) + 
          w3·normalized_safety(path)
```

**Efficiency Score:**
```
E(algorithm) = nodes_expanded / graph_size
```

**Optimality Gap:**
```
Gap(path) = (cost(path) - cost(optimal_path)) / cost(optimal_path) × 100%
```

---

## Appendix B: Sample Code Structure

```python
class AdaptiveHeuristicRouter:
    def __init__(self, graph, camera_data, ml_model):
        self.graph = graph  # NYC camera zone graph (907 nodes)
        self.camera_data = camera_data  # Real-time violation data
        self.ml_model = ml_model  # Learned heuristic weights
        self.path_sampler = PathSampler(strategy='thompson')
        
    def find_route(self, start, goal, user_prefs):
        """Main routing function with adaptive heuristics"""
        
        # Step 1: Sample diverse candidate paths
        candidate_paths = self.path_sampler.sample(
            start, goal, 
            num_samples=50,
            diversity_weight=0.3
        )
        
        # Step 2: Evaluate paths with learned heuristics
        scored_paths = []
        for path in candidate_paths:
            h_learned = self.ml_model.predict(path, user_prefs)
            score = self.evaluate_path(path, h_learned)
            scored_paths.append((path, score))
        
        # Step 3: Select Pareto-optimal routes
        pareto_routes = self.pareto_filter(scored_paths)
        
        # Step 4: Adaptive regularization for refinement
        weight = self.adaptive_weight(start, goal, user_prefs)
        best_route = self.weighted_astar(
            start, goal, 
            heuristic=h_learned, 
            weight=weight
        )
        
        return {
            'recommended': best_route,
            'alternatives': pareto_routes[:3],
            'computation_time': time.elapsed(),
            'nodes_expanded': self.stats['nodes']
        }
    
    def weighted_astar(self, start, goal, heuristic, weight=1.0):
        """Weighted A* implementation (from Programming Problem 3)"""
        # Implementation following course materials...
        pass
```

---

**End of Proposal**

---

**Student Signature:** Gil Raitses  
**Date:** October 27, 2025

**Note:** This proposal is submitted for approval in accordance with CIS 667 course requirements. The project will be completed individually with code, documentation, and final report delivered by the announced deadline.

