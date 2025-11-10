# CIS 667 Term Project Proposal - Versions Summary

**Student:** Gil Raitses  
**Date:** October 27, 2025  
**Status:** Complete - Multiple versions ready

---

## 📄 Available Proposal Versions

### Version 1: NSF-Style Proposal (RECOMMENDED)
**File:** `CIS667_TermProject_Proposal_NSF_Style.qmd` (source)  
**PDF:** `CIS667_TermProject_Proposal_NSF_Style.pdf` (21 pages, 142KB)

**Style:**
- ✅ NSF CAREER-inspired structure with Project Summary, Intellectual Merit, Broader Impacts
- ✅ Dense paragraph form throughout (NO lists except tables)
- ✅ Elegant typography: Avenir Next UltraLight body, Didot headings
- ✅ Custom commands: `\num{}` for numbers, `\tech{}` for technical terms
- ✅ NO section/subsection numbering in document body
- ✅ TOC shows main sections only (depth 1)
- ✅ All code moved to Appendix
- ✅ Abstract follows MAE600 scientific writing principles (hourglass structure)

**Sections:**
- Project Summary (Overview, Intellectual Merit, Broader Impacts)
- Introduction and Background
- Research Plan (Tasks 1-4)
- Work Plan and Student Information
- Intellectual Merit and Broader Impacts (expanded)
- Conclusion
- References
- Appendix (Algorithm specs, data augmentation, evaluation metrics, success criteria table)

**Key Features:**
- Research question clearly stated in abstract
- Discussion of impact integrated throughout
- Paragraph-based narrative (no bulleted lists)
- Professional NSF proposal aesthetics

---

### Version 2: Original Academic Style
**File:** `CIS667_TermProject_Proposal.qmd` (source)  
**PDF:** `CIS667_TermProject_Proposal.pdf` (28 pages, 164KB)

**Style:**
- Traditional academic proposal with numbered sections
- Mix of paragraphs and lists
- Some code inline
- TOC with subsections (depth 3)

**Use Case:**
- Fallback if NSF style doesn't meet course requirements
- More detailed technical specifications
- Traditional computer science proposal format

---

### Version 3: Markdown Reference
**File:** `CIS667_TermProject_Proposal_RaitsesGil.md` (602 lines)

**Style:**
- Plain markdown for easy editing
- Includes Firebase Cloud Functions (needs removal if using)
- Comprehensive 20-page content

**Use Case:**
- Quick reference without rendering
- Easy text searching
- Starting point for further customization

---

## 📊 Supporting Materials

### Data Analysis
- `BigQuery_Dataset_Summary.md` - Comprehensive EDA of your 5 BigQuery records
- `bigquery_data/` - Exported data directory
  - `zone_analyses.json` (2 records, 4KB)
  - `realtime_violations.json` (1 record, 288B)
  - `traffic_predictions.json` (2 records, 529B)
  - `eda_analysis.py` - Python analysis script

### Project Documentation
- `README.md` - Project navigation and quick start
- `references.bib` - Bibliography for Quarto
- `termprojectProposal.md` - Original course guidelines

---

## ✅ What You Have

### Active Google Cloud Resources
- Account: ACTIVE ✅
- Project: `vibe-check-463816`
- Datasets: 3 (vibecheck_analytics, ml_models, billing_export)
- Tables: 11 tables with proper schemas
- Cost: $0/month (expensive functions deleted July 22)

### Training Data
- Real samples: 5 records from BigQuery
- Feature vectors: 17-dimensional with Vision AI encoding
- Temperature scores: 5.0 - 24.0 (stress/safety proxy)
- Augmentation pipeline: Will generate 455 total samples

### Implementation Plan
- Pure Python (NO Firebase Cloud Functions)
- Local execution with scikit-learn
- Standard libraries: NumPy, pandas, NetworkX
- 907-node NYC graph for validation

---

## 🎯 Recommended Next Steps

1. **Review NSF-Style Proposal**
   - Open `CIS667_TermProject_Proposal_NSF_Style.pdf`
   - Verify it meets course requirements
   - Check that abstract satisfies research question + impact

2. **Submit for Approval**
   - Use NSF-style version (best formatting)
   - Meets all guidelines from `termprojectProposal.md`
   - 21 pages of comprehensive content

3. **Begin Implementation**
   - Follow Week 1-2 timeline (lit review + design)
   - Set up Python environment
   - Start baseline algorithm implementation

---

## 📋 Proposal Checklist (from termprojectProposal.md)

| Requirement | Status | Location |
|:------------|:------:|:---------|
| 1. Title | ✅ | Title page |
| 2. Introduction | ✅ | Section 1 |
| 3. Aim of the project | ✅ | Section 2 |
| 4. Objectives | ✅ | Section 3 (8 objectives) |
| 5. Team member info | ✅ | Work Plan section |
| 6. Initial work plan | ✅ | Work Plan section |
| 7. Work plan details | ✅ | Detailed Timeline subsection |
| 8. References | ✅ | References section |

**Project Classification:** Applied Project (Category d)  
**Secondary:** Comparison Study (Category c) + Theoretical Analysis (Category b)

---

## 🎨 Typography Features

**Fonts:**
- Body: Avenir Next UltraLight (elegant, readable)
- Headings: Didot (classic serif, authoritative)
- Numbers: Avenir Next Regular with gray color
- Tech terms: Avenir Next Medium with muted brown

**Custom Commands:**
- `\num{907}` - Renders numbers in gray
- `\tech{A* search}` - Renders technical terms in medium weight

**Layout:**
- Prevents orphaned headings (needspace package)
- Beautiful spacing (1.5em around floats)
- Professional margins (1 inch all sides)

---

## 📈 Project Scope

**8 Comprehensive Objectives:**
1. Path Sampling (70% diversity, <1s for 50 samples)
2. Heuristic Learning (15-25% improvement, MAE <15%)
3. Adaptive Regularization (30-60% speedup, 90% quality)
4. NYC Data Integration (907 nodes, 100% coverage)
5. Algorithm Comparison (6 baselines, p<0.05)
6. Real-World Validation (75% preference match)
7. Theoretical Analysis (formal proofs, complexity bounds)
8. Scalability (α < 0.8 scaling exponent)

**Success:** 6 out of 8 objectives meeting targets

---

**All Files Created:** October 27, 2025  
**Ready for Submission:** YES ✅  
**Recommended Version:** NSF-Style (21 pages, elegant formatting, meets all requirements)

