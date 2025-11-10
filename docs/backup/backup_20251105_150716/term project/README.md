# CIS 667 Term Project - Adaptive Heuristic Learning for Urban Navigation

**Student:** Gil Raitses  
**Course:** CIS 667 - Introduction to Artificial Intelligence  
**Institution:** Syracuse University  
**Semester:** Fall 2025

---

## Project Files

### Core Proposal
- **`CIS667_TermProject_Proposal_RaitsesGil.md`** - Complete 20-page term project proposal
  - Integrates path sampling, heuristic learning, and adaptive regularization
  - Builds on weighted A* experience from Programming Problem 3
  - Uses NYC Vibe Check infrastructure (907 camera zones)

### Data & Analysis
- **`BigQuery_Dataset_Summary.md`** - Comprehensive EDA summary of your BigQuery data
  - Inventory of 5 training records across 3 tables
  - 17-dimensional feature vector analysis
  - Local model training guide
  - Integration instructions

- **`bigquery_data/`** - Exported data directory
  - `zone_analyses.json` - 2 records with Vision AI encoding
  - `realtime_violations.json` - 1 violation record
  - `traffic_predictions.json` - 2 ARIMA prediction records
  - `eda_analysis.py` - Python script for exploratory analysis

### Reference Materials
- **`termprojectProposal.md`** - Original proposal template/guidelines

---

## Quick Start

### 1. Review Your Data
```bash
cd "/Users/gilraitses/cis667/term project"
python3 bigquery_data/eda_analysis.py
```

### 2. Read the Analysis
```bash
open "BigQuery_Dataset_Summary.md"
```

### 3. Review the Proposal
```bash
open "CIS667_TermProject_Proposal_RaitsesGil.md"
```

---

## Key Findings

✅ **Your Google Cloud account is ACTIVE**
- BigQuery datasets intact with 11 tables
- Vision AI-encoded feature vectors ready
- No charges (expensive functions deleted July 22)

✅ **You have usable training data**
- 17-dimensional numerical feature vectors
- Temperature/stress scores as targets
- Google Cloud Vision labels for validation

⚠️ **Limited sample size**
- Only 5 records total
- Requires synthetic data generation
- SMOTE/bootstrap recommended

---

## Project Status

| Component | Status |
|-----------|--------|
| Proposal | ✅ Complete (20 pages) |
| Data Export | ✅ Complete (5 records) |
| EDA Analysis | ✅ Complete |
| Local Training Guide | ✅ Complete |
| Baseline Implementation | 🔄 TODO |
| Synthetic Data Generation | 🔄 TODO |
| Integration | 🔄 TODO |

---

## Next Steps

### Week 1-2 (Nov 1-14)
- [ ] Review proposal and get instructor approval
- [ ] Set up Python environment for local training
- [ ] Implement synthetic data generation (SMOTE/bootstrap)
- [ ] Train baseline Ridge regression model

### Week 3-4 (Nov 15-28)
- [ ] Implement weighted A* variants (W = 1.0, 1.2, 1.5)
- [ ] Develop path sampling framework
- [ ] Create adaptive regularization mechanism
- [ ] Test on NYC Vibe Check graph

### Week 5-6 (Nov 29 - Dec 12)
- [ ] Integrate with Firebase/TypeScript backend
- [ ] Collect additional camera data if possible
- [ ] Run comprehensive experiments
- [ ] Statistical analysis

### Week 7-10 (Dec 13 - Jan 9)
- [ ] Write final report
- [ ] Create presentation
- [ ] Document code and release
- [ ] Submit final deliverables

---

## Resources

### Your Infrastructure
- **NYC Vibe Check**: 907 camera zones, Voronoi tessellation, BigQuery ML
- **Firebase Project**: `vibe-check-463816`
- **Dataset**: `vibecheck_analytics`

### Key Technologies
- Python: pandas, numpy, scikit-learn
- TypeScript: Firebase Functions, Firestore
- BigQuery: Data storage and (optional) ML training
- Google Cloud Vision: Object detection and scene analysis

---

## Contact

**Instructor:** Prof. Andrew C. Lee  
**Email:** graitses@syr.edu  
**Project Workspace:** `/Users/gilraitses/cis667/term project/`

---

**Last Updated:** October 27, 2025  
**Proposal Status:** Ready for submission

