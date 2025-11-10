#!/usr/bin/env python3
"""Monitor Cloud Scheduler reliability and detect missed runs."""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

def get_recent_executions(project: str, region: str, job: str, limit: int = 50) -> list:
    """Get recent Cloud Run job executions."""
    result = subprocess.run(
        ['gcloud', 'run', 'jobs', 'executions', 'list',
         '--project', project,
         '--region', region,
         '--job', job,
         '--limit', str(limit),
         '--format', 'json'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error getting executions: {result.stderr}", file=sys.stderr)
        return []
    
    return json.loads(result.stdout)

def analyze_scheduler_reliability(executions: list, hours_to_check: int = 24) -> dict:
    """Analyze scheduler reliability over the last N hours."""
    et_tz = ZoneInfo("America/New_York")
    now = datetime.now(et_tz)
    start_time = now - timedelta(hours=hours_to_check)
    
    # Expected runs (every 30 minutes)
    expected_runs = []
    current = start_time.replace(minute=0, second=0, microsecond=0)
    while current <= now:
        expected_runs.append(current)
        current += timedelta(minutes=30)
    
    # Parse executions
    actual_runs = []
    for exec in executions:
        start_time_str = exec.get('status', {}).get('startTime', '')
        if start_time_str:
            try:
                dt = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                et_time = dt.astimezone(et_tz)
                if et_time >= start_time:
                    actual_runs.append(et_time)
            except:
                pass
    
    # Match expected vs actual
    matched_runs = []
    missed_runs = []
    
    for expected in expected_runs:
        # Look for actual run within 5 minutes of expected
        found = False
        for actual in actual_runs:
            if abs((actual - expected).total_seconds()) < 300:  # 5 minutes tolerance
                matched_runs.append(expected)
                found = True
                break
        
        if not found:
            missed_runs.append(expected)
    
    # Calculate success rate
    total_expected = len(expected_runs)
    total_matched = len(matched_runs)
    success_rate = (total_matched / total_expected * 100) if total_expected > 0 else 0
    
    return {
        'total_expected': total_expected,
        'total_matched': total_matched,
        'total_missed': len(missed_runs),
        'success_rate': success_rate,
        'matched_runs': matched_runs,
        'missed_runs': missed_runs,
        'start_time': start_time.isoformat(),
        'end_time': now.isoformat()
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor Cloud Scheduler reliability")
    parser.add_argument('--project', default='pax-nyc', help='GCP project ID')
    parser.add_argument('--region', default='us-central1', help='GCP region')
    parser.add_argument('--job', default='pax-collector', help='Cloud Run job name')
    parser.add_argument('--hours', type=int, default=24, help='Hours to analyze')
    parser.add_argument('--output', type=Path, help='Output JSON file')
    
    args = parser.parse_args()
    
    print("Fetching recent executions...")
    executions = get_recent_executions(args.project, args.region, args.job)
    
    print(f"Analyzing reliability over last {args.hours} hours...")
    analysis = analyze_scheduler_reliability(executions, args.hours)
    
    print()
    print("=" * 60)
    print("SCHEDULER RELIABILITY REPORT")
    print("=" * 60)
    print()
    print(f"Analysis Period: {analysis['start_time']} to {analysis['end_time']}")
    print(f"Expected Runs: {analysis['total_expected']}")
    print(f"Matched Runs: {analysis['total_matched']}")
    print(f"Missed Runs: {analysis['total_missed']}")
    print(f"Success Rate: {analysis['success_rate']:.1f}%")
    print()
    
    if analysis['missed_runs']:
        print("Missed Runs:")
        for missed in analysis['missed_runs']:
            print(f"  - {missed.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print()
    
    # Assessment
    if analysis['success_rate'] >= 95:
        print("✅ Reliability is acceptable (≥95%)")
    elif analysis['success_rate'] >= 90:
        print("⚠️  Reliability is marginal (90-95%)")
    else:
        print("❌ Reliability is poor (<90%)")
        print("   Consider migrating to AWS or implementing workarounds")
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"\nReport saved to: {args.output}")
    
    return 0 if analysis['success_rate'] >= 95 else 1

if __name__ == '__main__':
    sys.exit(main())
