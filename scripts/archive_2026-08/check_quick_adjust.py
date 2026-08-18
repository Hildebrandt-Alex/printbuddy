#!/usr/bin/env python
"""
Check Jobs with quick_adjust steps.
"""
from jobs.models import Job, JobStep

print("\n=== Jobs mit Quick Adjust Steps ===\n")

# Find all jobs that have at least one quick_adjust step
jobs_with_qa = Job.objects.filter(steps__step_type='quick_adjust').distinct().order_by('-created_at')[:10]

print(f"Total Jobs: {jobs_with_qa.count()}\n")

for job in jobs_with_qa:
    print(f"Job {job.id}")
    print(f"  Title: {job.title}")
    print(f"  Status: {job.status}")
    
    # Get ALL quick_adjust steps for this job
    qa_steps = job.steps.filter(step_type='quick_adjust').order_by('-created_at')
    print(f"  Quick Adjust Steps: {qa_steps.count()}")
    
    for step in qa_steps:
        print(f"    Step {step.id}")
        print(f"      Status: {step.status}")
        print(f"      output_asset_id: {step.output_asset_id}")
        print(f"      Created: {step.created_at}")
        print(f"      Completed: {step.completed_at}")
        
        # Check if file exists on NAS
        if step.output_asset_id:
            import os
            from pathlib import Path
            from datetime import datetime
            
            # Try different file patterns
            raw_dir = Path("/mnt/agency_nas/raw")
            
            # Pattern 1: UUID_adjusted_timestamp.png (new format)
            timestamp_str = step.completed_at.strftime("%Y%m%d_%H%M%S") if step.completed_at else "unknown"
            new_path = raw_dir / f"{step.output_asset_id}_adjusted_{timestamp_str}.png"
            
            # Pattern 2: UUID_adjusted.png (old format)
            old_path = raw_dir / f"{step.output_asset_id}_adjusted.png"
            
            exists_new = new_path.exists() if new_path else False
            exists_old = old_path.exists() if old_path else False
            
            print(f"      File (new format): {'✅ EXISTS' if exists_new else '❌ NOT FOUND'}")
            print(f"      File (old format): {'✅ EXISTS' if exists_old else '❌ NOT FOUND'}")
        else:
            print(f"      File: ⚠️ NO ASSET ID YET")
    print()
