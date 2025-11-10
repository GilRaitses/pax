#!/usr/bin/env python3
"""Health check script: Detects missed collections and triggers manual execution."""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

def check_recent_collection(project: str, region: str, job: str, minutes: int = 35) -> bool:
    """Check if collection happened in the last N minutes."""
    result = subprocess.run(
        ['gcloud', 'run', 'jobs', 'executions', 'list',
         '--project', project,
         '--region', region,
         '--job', job,
         '--limit', '1',
         '--format', 'json'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error checking executions: {result.stderr}", file=sys.stderr)
        return False
    
    executions = json.loads(result.stdout)
    if not executions:
        print("No executions found")
        return False
    
    latest_exec = executions[0]
    start_time_str = latest_exec.get('status', {}).get('startTime', '')
    
    if not start_time_str:
        print("Latest execution has no start time")
        return False
    
    try:
        exec_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        now = datetime.now(ZoneInfo("UTC"))
        age = (now - exec_time).total_seconds() / 60  # minutes
        
        print(f"Latest execution: {exec_time.isoformat()} ({age:.1f} minutes ago)")
        
        return age < minutes
    except Exception as e:
        print(f"Error parsing time: {e}", file=sys.stderr)
        return False

def trigger_manual_execution(project: str, region: str, job: str) -> bool:
    """Trigger manual Cloud Run job execution."""
    print(f"Triggering manual execution of {job}...")
    
    result = subprocess.run(
        ['gcloud', 'run', 'jobs', 'execute', job,
         '--project', project,
         '--region', region,
         '--format', 'json'],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Manual execution triggered successfully")
        exec_data = json.loads(result.stdout)
        print(f"Execution: {exec_data.get('metadata', {}).get('name', 'unknown')}")
        return True
    else:
        print(f"❌ Failed to trigger execution: {result.stderr}", file=sys.stderr)
        return False

def main() -> int:
    parser = argparse.ArgumentParser(description="Health check for collection system")
    parser.add_argument('--project', default='pax-nyc', help='GCP project')
    parser.add_argument('--region', default='us-central1', help='GCP region')
    parser.add_argument('--job', default='pax-collector', help='Cloud Run job name')
    parser.add_argument('--check-window', type=int, default=35,
                       help='Minutes to check for recent collection (default: 35)')
    parser.add_argument('--trigger', action='store_true',
                       help='Trigger manual execution if collection missed')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode (do not trigger execution)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("COLLECTION HEALTH CHECK")
    print("=" * 60)
    print()
    
    print(f"Checking for collections in last {args.check_window} minutes...")
    has_recent_collection = check_recent_collection(
        args.project, args.region, args.job, args.check_window
    )
    
    print()
    if has_recent_collection:
        print("✅ Recent collection found - system is healthy")
        return 0
    else:
        print("⚠️  No recent collection found - collection may have been missed")
        
        if args.trigger and not args.dry_run:
            print()
            success = trigger_manual_execution(args.project, args.region, args.job)
            return 0 if success else 1
        elif args.dry_run:
            print()
            print("DRY RUN: Would trigger manual execution")
            return 1
        else:
            print()
            print("Use --trigger to automatically trigger manual execution")
            return 1

if __name__ == '__main__':
    sys.exit(main())

