#!/usr/bin/env python3
"""Compare manual vs scheduler Cloud Run job invocations to find differences."""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def get_recent_executions(project: str, region: str, job: str, limit: int = 20) -> list:
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

def get_scheduler_logs(project: str, location: str, job_id: str, hours: int = 24) -> list:
    """Get Cloud Scheduler logs."""
    start_time = (datetime.now() - timedelta(hours=hours)).isoformat() + 'Z'
    
    result = subprocess.run(
        ['gcloud', 'logging', 'read',
         f'resource.type="cloud_scheduler_job"',
         f'resource.labels.job_id="{job_id}"',
         f'timestamp>="{start_time}"',
         '--limit', '50',
         '--format', 'json',
         '--project', project],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error getting scheduler logs: {result.stderr}", file=sys.stderr)
        return []
    
    return json.loads(result.stdout) if result.stdout.strip() else []

def get_cloud_run_logs(project: str, job_name: str, hours: int = 24) -> list:
    """Get Cloud Run job logs."""
    start_time = (datetime.now() - timedelta(hours=hours)).isoformat() + 'Z'
    
    result = subprocess.run(
        ['gcloud', 'logging', 'read',
         f'resource.type="cloud_run_job"',
         f'resource.labels.job_name="{job_name}"',
         f'timestamp>="{start_time}"',
         '--limit', '100',
         '--format', 'json',
         '--project', project],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error getting Cloud Run logs: {result.stderr}", file=sys.stderr)
        return []
    
    return json.loads(result.stdout) if result.stdout.strip() else []

def analyze_invocations(executions: list, scheduler_logs: list, cloud_run_logs: list) -> dict:
    """Analyze manual vs scheduler invocations."""
    
    et_tz = ZoneInfo("America/New_York")
    
    # Categorize executions
    manual_executions = []
    scheduler_executions = []
    
    for exec in executions:
        start_time = exec.get('status', {}).get('startTime', '')
        succeeded = exec.get('status', {}).get('succeededCount', 0)
        failed = exec.get('status', {}).get('failedCount', 0)
        
        # Check if this was triggered by scheduler or manual
        # Manual executions typically have immediate start after creation
        # Scheduler executions may have delays or different patterns
        
        # For now, categorize by success
        if succeeded > 0:
            manual_executions.append(exec)
        else:
            scheduler_executions.append(exec)
    
    # Analyze scheduler logs
    scheduler_attempts = []
    for log in scheduler_logs:
        timestamp = log.get('timestamp', '')
        text = log.get('textPayload', '')
        json_payload = log.get('jsonPayload', {})
        
        scheduler_attempts.append({
            'timestamp': timestamp,
            'text': text,
            'json': json_payload
        })
    
    # Analyze Cloud Run logs for errors
    cloud_run_errors = []
    for log in cloud_run_logs:
        severity = log.get('severity', '')
        text = log.get('textPayload', '')
        json_payload = log.get('jsonPayload', {})
        
        if severity in ['ERROR', 'WARNING'] or 'error' in str(text).lower():
            cloud_run_errors.append({
                'timestamp': log.get('timestamp', ''),
                'severity': severity,
                'text': text,
                'json': json_payload
            })
    
    return {
        'manual_executions': len(manual_executions),
        'scheduler_executions': len(scheduler_executions),
        'scheduler_attempts': len(scheduler_attempts),
        'cloud_run_errors': len(cloud_run_errors),
        'scheduler_attempts_detail': scheduler_attempts[:10],
        'cloud_run_errors_detail': cloud_run_errors[:10]
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Compare manual vs scheduler invocations")
    parser.add_argument('--project', default='pax-nyc', help='GCP project')
    parser.add_argument('--region', default='us-central1', help='GCP region')
    parser.add_argument('--job', default='pax-collector', help='Cloud Run job name')
    parser.add_argument('--scheduler', default='pax-collector-schedule', help='Scheduler job ID')
    parser.add_argument('--hours', type=int, default=24, help='Hours to analyze')
    parser.add_argument('--output', type=Path, help='Output JSON file')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("INVOCATION COMPARISON ANALYSIS")
    print("=" * 60)
    print()
    
    print("Fetching executions...")
    executions = get_recent_executions(args.project, args.region, args.job)
    print(f"Found {len(executions)} executions")
    
    print("Fetching scheduler logs...")
    scheduler_logs = get_scheduler_logs(args.project, args.region, args.scheduler, args.hours)
    print(f"Found {len(scheduler_logs)} scheduler log entries")
    
    print("Fetching Cloud Run logs...")
    cloud_run_logs = get_cloud_run_logs(args.project, args.job, args.hours)
    print(f"Found {len(cloud_run_logs)} Cloud Run log entries")
    print()
    
    analysis = analyze_invocations(executions, scheduler_logs, cloud_run_logs)
    
    print("=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)
    print()
    print(f"Manual Executions (Successful): {analysis['manual_executions']}")
    print(f"Scheduler Executions (Failed): {analysis['scheduler_executions']}")
    print(f"Scheduler Attempts: {analysis['scheduler_attempts']}")
    print(f"Cloud Run Errors: {analysis['cloud_run_errors']}")
    print()
    
    if analysis['scheduler_attempts_detail']:
        print("Recent Scheduler Attempts:")
        for attempt in analysis['scheduler_attempts_detail'][:5]:
            print(f"  {attempt['timestamp']}: {attempt['text'][:100]}")
        print()
    
    if analysis['cloud_run_errors_detail']:
        print("Recent Cloud Run Errors:")
        for error in analysis['cloud_run_errors_detail'][:5]:
            print(f"  {error['timestamp']} [{error['severity']}]: {error['text'][:100]}")
        print()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"Analysis saved to: {args.output}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

