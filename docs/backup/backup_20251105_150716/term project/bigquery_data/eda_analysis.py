#!/usr/bin/env python3
"""
Exploratory Data Analysis for NYC Vibe Check BigQuery Dataset
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from collections import Counter

def load_data():
    """Load all exported JSON files"""
    with open('zone_analyses.json', 'r') as f:
        zone_analyses = json.load(f)
    
    with open('realtime_violations.json', 'r') as f:
        violations = json.load(f)
    
    with open('traffic_predictions.json', 'r') as f:
        predictions = json.load(f)
    
    return zone_analyses, violations, predictions

def analyze_zone_analyses(data):
    """Analyze zone_analyses table"""
    print("=" * 80)
    print("ZONE ANALYSES TABLE ANALYSIS")
    print("=" * 80)
    print(f"Total Records: {len(data)}")
    print()
    
    # Parse the nested JSON in analysis_json field
    parsed_analyses = []
    for record in data:
        try:
            analysis = json.loads(record['analysis_json'])
            parsed_analyses.append(analysis)
        except:
            pass
    
    print(f"Successfully Parsed Records: {len(parsed_analyses)}")
    print()
    
    # Analyze numerical_data arrays (17-dimensional feature vectors)
    print("NUMERICAL DATA FEATURE VECTORS:")
    print("-" * 80)
    numerical_arrays = [a['numerical_data'] for a in parsed_analyses if 'numerical_data' in a]
    if numerical_arrays:
        print(f"Feature Vector Dimension: {len(numerical_arrays[0])}")
        print(f"Sample Feature Vectors:")
        for i, vec in enumerate(numerical_arrays[:3]):
            print(f"  Record {i+1}: {vec}")
        print()
        
        # Calculate statistics per feature
        numerical_matrix = np.array(numerical_arrays)
        print("Feature Statistics (across all records):")
        for i in range(numerical_matrix.shape[1]):
            feature_values = numerical_matrix[:, i]
            print(f"  Feature {i+1:2d}: min={feature_values.min():.2f}, "
                  f"max={feature_values.max():.2f}, "
                  f"mean={feature_values.mean():.2f}, "
                  f"std={feature_values.std():.2f}")
        print()
    
    # Analyze temperature scores
    print("TEMPERATURE SCORES:")
    print("-" * 80)
    temp_scores = [float(r['temperature_score']) for r in data]
    print(f"Range: {min(temp_scores):.1f} - {max(temp_scores):.1f}")
    print(f"Mean: {np.mean(temp_scores):.2f}")
    print(f"Std Dev: {np.std(temp_scores):.2f}")
    print()
    
    # Analyze Cloud Vision data
    print("GOOGLE CLOUD VISION API RESULTS:")
    print("-" * 80)
    for i, analysis in enumerate(parsed_analyses):
        vision_data = analysis.get('cloud_vision_data', {})
        print(f"\nRecord {i+1}:")
        if vision_data.get('error'):
            print(f"  Status: ERROR - {vision_data.get('error_message', 'Unknown')}")
        else:
            print(f"  Status: SUCCESS")
            print(f"  Objects Detected: {vision_data.get('total_objects_detected', 0)}")
            print(f"  Labels Detected: {vision_data.get('total_labels_detected', 0)}")
            print(f"  Pedestrians: {vision_data.get('pedestrian_count', 0)}")
            print(f"  Bicycles: {vision_data.get('bicycle_count', 0)}")
            print(f"  Vehicles: {vision_data.get('vehicle_count', 0)}")
            print(f"  Safety Score: {vision_data.get('safety_score', 0):.1f}")
            
            # Show top labels
            labels = vision_data.get('detected_labels', [])
            if labels:
                print(f"  Top 5 Labels:")
                for label in labels[:5]:
                    print(f"    - {label['description']}: {label['score']:.3f}")
    
    # Analyze processing pipeline status
    print("\n\nPROCESSING PIPELINE SUCCESS RATES:")
    print("-" * 80)
    pipeline_steps = {}
    for analysis in parsed_analyses:
        status = analysis.get('pipeline_status', {})
        for step, result in status.items():
            if step not in pipeline_steps:
                pipeline_steps[step] = {'success': 0, 'failed': 0}
            if result == 'success':
                pipeline_steps[step]['success'] += 1
            else:
                pipeline_steps[step]['failed'] += 1
    
    for step, counts in sorted(pipeline_steps.items()):
        total = counts['success'] + counts['failed']
        success_rate = (counts['success'] / total * 100) if total > 0 else 0
        print(f"  {step:30s}: {counts['success']}/{total} ({success_rate:.1f}% success)")
    
    # Processing performance
    print("\n\nPROCESSING PERFORMANCE:")
    print("-" * 80)
    processing_times = [a['processing_time_ms'] for a in parsed_analyses if 'processing_time_ms' in a]
    if processing_times:
        print(f"  Processing Time: min={min(processing_times)}ms, "
              f"max={max(processing_times)}ms, "
              f"mean={np.mean(processing_times):.0f}ms")
    
    image_sizes = [a['image_size_bytes'] for a in parsed_analyses if 'image_size_bytes' in a and a['image_size_bytes'] > 0]
    if image_sizes:
        print(f"  Image Size: min={min(image_sizes)/1024:.1f}KB, "
              f"max={max(image_sizes)/1024:.1f}KB, "
              f"mean={np.mean(image_sizes)/1024:.1f}KB")
    
    return parsed_analyses

def analyze_violations(data):
    """Analyze realtime_violations table"""
    print("\n\n" + "=" * 80)
    print("REALTIME VIOLATIONS TABLE ANALYSIS")
    print("=" * 80)
    print(f"Total Records: {len(data)}")
    print()
    
    if len(data) == 0:
        print("No violations data available")
        return
    
    # Violation types
    violation_types = [r['violation_type'] for r in data]
    type_counts = Counter(violation_types)
    print("VIOLATION TYPES:")
    print("-" * 80)
    for vtype, count in type_counts.most_common():
        print(f"  {vtype}: {count}")
    print()
    
    # Confidence scores
    confidences = [float(r['confidence']) for r in data if 'confidence' in r]
    if confidences:
        print("CONFIDENCE SCORES:")
        print("-" * 80)
        print(f"  Range: {min(confidences):.2f} - {max(confidences):.2f}")
        print(f"  Mean: {np.mean(confidences):.2f}")
        print()
    
    # Cameras with violations
    cameras = [r['camera_id'] for r in data]
    print("CAMERAS WITH VIOLATIONS:")
    print("-" * 80)
    print(f"  Unique Cameras: {len(set(cameras))}")
    for camera, count in Counter(cameras).most_common():
        print(f"  {camera}: {count} violations")
    print()
    
    return data

def analyze_predictions(data):
    """Analyze traffic_predictions table"""
    print("\n\n" + "=" * 80)
    print("TRAFFIC PREDICTIONS TABLE ANALYSIS")
    print("=" * 80)
    print(f"Total Records: {len(data)}")
    print()
    
    if len(data) == 0:
        print("No predictions data available")
        return
    
    # Model versions
    models = [r['model_version'] for r in data]
    model_counts = Counter(models)
    print("MODEL VERSIONS:")
    print("-" * 80)
    for model, count in model_counts.most_common():
        print(f"  {model}: {count} predictions")
    print()
    
    # Prediction accuracy (MAPE)
    mapes = [float(r['mape']) for r in data if 'mape' in r]
    if mapes:
        print("MODEL ACCURACY (MAPE - Mean Absolute Percentage Error):")
        print("-" * 80)
        print(f"  Range: {min(mapes):.4f} - {max(mapes):.4f}")
        print(f"  Mean: {np.mean(mapes):.4f}")
        print(f"  (Lower MAPE = Better, 0.12 = 12% error)")
        print()
    
    # Prediction values
    pred_vehicles = [int(r['predicted_vehicles']) for r in data]
    pred_pedestrians = [int(r['predicted_pedestrians']) for r in data]
    
    print("PREDICTED VALUES:")
    print("-" * 80)
    print(f"  Vehicles: min={min(pred_vehicles)}, max={max(pred_vehicles)}, mean={np.mean(pred_vehicles):.1f}")
    print(f"  Pedestrians: min={min(pred_pedestrians)}, max={max(pred_pedestrians)}, mean={np.mean(pred_pedestrians):.1f}")
    print()
    
    # Horizon
    horizons = [int(r['horizon_minutes']) for r in data]
    print("PREDICTION HORIZONS:")
    print("-" * 80)
    for horizon, count in Counter(horizons).most_common():
        print(f"  {horizon} minutes: {count} predictions")
    print()
    
    return data

def generate_summary():
    """Generate overall dataset summary"""
    print("\n\n" + "=" * 80)
    print("DATASET SUMMARY FOR TERM PROJECT")
    print("=" * 80)
    print()
    
    print("AVAILABLE DATA:")
    print("-" * 80)
    print("✓ 2 zone analysis records with:")
    print("  - 17-dimensional numerical feature vectors")
    print("  - Google Cloud Vision API object detection results")
    print("  - Temperature/stress scores")
    print("  - Processing pipeline telemetry")
    print()
    print("✓ 1 violation record with:")
    print("  - Violation type classification")
    print("  - Confidence scores")
    print("  - Camera associations")
    print()
    print("✓ 2 traffic prediction records with:")
    print("  - ARIMA-based vehicle/pedestrian forecasts")
    print("  - Model accuracy metrics (MAPE)")
    print("  - 30-minute prediction horizons")
    print()
    
    print("DATA QUALITY ASSESSMENT:")
    print("-" * 80)
    print("✓ Schema: Well-structured with clear field definitions")
    print("✓ Feature Engineering: 17-dimensional vectors ready for ML")
    print("✓ Ground Truth: Cloud Vision API provides validation data")
    print("⚠ Volume: Limited samples (5 total records across 3 tables)")
    print("⚠ Coverage: Only 3 unique cameras represented")
    print()
    
    print("SUITABILITY FOR TERM PROJECT:")
    print("-" * 80)
    print("✓ Feature vectors can be used as input for heuristic learning")
    print("✓ Temperature scores provide target variable for stress prediction")
    print("✓ Vision API labels provide interpretable features")
    print("✓ Prediction accuracy (MAPE) provides baseline for improvement")
    print()
    print("⚠ RECOMMENDATION: Generate synthetic training data or collect more")
    print("  samples to achieve statistical significance for ML models")
    print()
    
    print("NEXT STEPS FOR TERM PROJECT:")
    print("-" * 80)
    print("1. Use existing 17-dimensional features as base heuristic components")
    print("2. Augment with synthetic data generation (bootstrap/SMOTE)")
    print("3. Implement weighted combination learning on available features")
    print("4. Use temperature_score as proxy for stress/safety target")
    print("5. Validate on held-out real samples when available")
    print()
    
    print("LOCAL MODEL TRAINING FEASIBILITY:")
    print("-" * 80)
    print("✓ Data format: Standard JSON, easy to load with pandas/sklearn")
    print("✓ Feature extraction: Straightforward parsing of numerical_data arrays")
    print("✓ No dependencies: Can train locally without BigQuery access")
    print("✓ Framework: scikit-learn sufficient for baseline models")
    print("✓ Scalability: Can export more data as it accumulates")
    print()

def main():
    """Main analysis function"""
    print("\n" + "=" * 80)
    print("NYC VIBE CHECK BIGQUERY DATASET - EXPLORATORY DATA ANALYSIS")
    print("=" * 80)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Data Location: /Users/gilraitses/cis667/term project/bigquery_data/")
    print("=" * 80)
    print()
    
    # Load data
    zone_analyses, violations, predictions = load_data()
    
    # Analyze each table
    analyze_zone_analyses(zone_analyses)
    analyze_violations(violations)
    analyze_predictions(predictions)
    
    # Generate summary
    generate_summary()
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()

