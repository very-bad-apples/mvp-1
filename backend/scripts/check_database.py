#!/usr/bin/env python3
"""
Script to inspect database contents.

Supports both:
- DynamoDB (MV projects and scenes)
- SQLite (Jobs and Stages)

Usage:
    # DynamoDB
    python scripts/check_database.py dynamodb --list              # List all projects
    python scripts/check_database.py dynamodb --recent 5           # Show 5 most recent projects
    python scripts/check_database.py dynamodb <project_id>         # Check specific project
    python scripts/check_database.py dynamodb <project_id> --scenes # Show project with scenes
    
    # SQLite
    python scripts/check_database.py sqlite --list                 # List all jobs
    python scripts/check_database.py sqlite --recent 5             # Show 5 most recent jobs
    python scripts/check_database.py sqlite <job_id>               # Check specific job
    python scripts/check_database.py sqlite --status pending        # Filter by status
"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path so we can import backend modules
script_dir = Path(__file__).parent
backend_dir = script_dir.parent
sys.path.insert(0, str(backend_dir))

import argparse
import json
from datetime import datetime
from typing import Optional

# DynamoDB imports
from mv_models import MVProjectItem
from dynamodb_config import init_dynamodb_tables

# SQLite imports
from database import get_db_context
from models import Job, Stage


def format_datetime(dt):
    """Format datetime for display."""
    if dt is None:
        return "N/A"
    if isinstance(dt, str):
        return dt
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def check_dynamodb_project(project_id: str, show_scenes: bool = False):
    """Check a specific DynamoDB project."""
    pk = f"PROJECT#{project_id}"
    
    try:
        project = MVProjectItem.get(pk, "METADATA")
        print(f"\n✅ Project: {project_id}")
        print(f"   Status: {project.status}")
        print(f"   Created: {format_datetime(project.createdAt)}")
        print(f"   Updated: {format_datetime(project.updatedAt)}")
        print(f"   Concept Prompt: {project.conceptPrompt[:80]}...")
        if project.characterDescription:
            print(f"   Character: {project.characterDescription[:60]}...")
        if project.productDescription:
            print(f"   Product: {project.productDescription[:60]}...")
        print(f"   Scene Count: {project.sceneCount or 0}")
        print(f"   Completed Scenes: {project.completedScenes or 0}")
        print(f"   Failed Scenes: {project.failedScenes or 0}")
        
        if show_scenes:
            # Query all scenes for this project
            scenes = list(MVProjectItem.query(
                pk,
                MVProjectItem.SK.begins_with("SCENE#")
            ))
            scenes.sort(key=lambda x: x.sequence or 0)
            
            print(f"\n   📹 Scenes ({len(scenes)}):")
            for scene in scenes:
                print(f"      Scene {scene.sequence}: {scene.status}")
                print(f"         Prompt: {scene.prompt[:60]}...")
                if scene.errorMessage:
                    print(f"         Error: {scene.errorMessage[:60]}...")
        
        return True
    except Exception as e:
        print(f"❌ Project not found: {project_id}")
        print(f"   Error: {e}")
        return False


def list_dynamodb_projects():
    """List all DynamoDB projects."""
    projects = []
    for status in ["pending", "processing", "completed", "failed"]:
        projects.extend(list(MVProjectItem.status_index.query(status)))
    
    # Filter to project metadata only
    project_items = [p for p in projects if p.entityType == "project"]
    
    print(f"\n📊 DynamoDB Projects: {len(project_items)}\n")
    
    for project in project_items:
        print(f"  {project.projectId}")
        print(f"    Status: {project.status}")
        print(f"    Created: {format_datetime(project.createdAt)}")
        print(f"    Prompt: {project.conceptPrompt[:60]}...")
        print()


def show_recent_dynamodb_projects(count: int = 10):
    """Show most recent DynamoDB projects."""
    all_projects = []
    for status in ["pending", "processing", "completed", "failed"]:
        all_projects.extend(list(MVProjectItem.status_index.query(status)))
    
    project_items = [p for p in all_projects if p.entityType == "project"]
    project_items.sort(key=lambda x: x.createdAt, reverse=True)
    
    print(f"\n📊 Most Recent {min(count, len(project_items))} DynamoDB Projects:\n")
    
    for project in project_items[:count]:
        print(f"  {project.projectId}")
        print(f"    Status: {project.status}")
        print(f"    Created: {format_datetime(project.createdAt)}")
        print(f"    Prompt: {project.conceptPrompt[:60]}...")
        print()


def check_sqlite_job(job_id: str):
    """Check a specific SQLite job."""
    with get_db_context() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        
        if not job:
            print(f"❌ Job not found: {job_id}")
            return False
        
        print(f"\n✅ Job: {job_id}")
        print(f"   Status: {job.status}")
        print(f"   Created: {format_datetime(job.created_at)}")
        print(f"   Updated: {format_datetime(job.updated_at)}")
        print(f"   Product: {job.product_name}")
        print(f"   Style: {job.style}")
        print(f"   CTA: {job.cta_text}")
        print(f"   Version: {job.version}")
        print(f"   Cost: ${job.cost_usd or 0:.2f}")
        if job.video_url:
            print(f"   Video URL: {job.video_url}")
        if job.error_message:
            print(f"   Error: {job.error_message[:100]}...")
        
        # Show stages
        stages = db.query(Stage).filter(Stage.job_id == job_id).order_by(Stage.id).all()
        if stages:
            print(f"\n   📋 Stages ({len(stages)}):")
            for stage in stages:
                print(f"      {stage.stage_name}: {stage.status} ({stage.progress}%)")
                if stage.error_message:
                    print(f"         Error: {stage.error_message[:60]}...")
        
        return True


def list_sqlite_jobs(status_filter: Optional[str] = None):
    """List all SQLite jobs."""
    with get_db_context() as db:
        query = db.query(Job)
        if status_filter:
            query = query.filter(Job.status == status_filter)
        jobs = query.order_by(Job.created_at.desc()).all()
        
        print(f"\n📊 SQLite Jobs: {len(jobs)}")
        if status_filter:
            print(f"   Filtered by status: {status_filter}")
        print()
        
        for job in jobs:
            print(f"  {job.id}")
            print(f"    Status: {job.status}")
            print(f"    Created: {format_datetime(job.created_at)}")
            print(f"    Product: {job.product_name}")
            print(f"    Cost: ${job.cost_usd or 0:.2f}")
            print()


def show_recent_sqlite_jobs(count: int = 10):
    """Show most recent SQLite jobs."""
    with get_db_context() as db:
        jobs = db.query(Job).order_by(Job.created_at.desc()).limit(count).all()
        
        print(f"\n📊 Most Recent {len(jobs)} SQLite Jobs:\n")
        
        for job in jobs:
            print(f"  {job.id}")
            print(f"    Status: {job.status}")
            print(f"    Created: {format_datetime(job.created_at)}")
            print(f"    Product: {job.product_name}")
            print(f"    Cost: ${job.cost_usd or 0:.2f}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="Inspect database contents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest="database", help="Database to query")
    
    # DynamoDB subparser
    dynamodb_parser = subparsers.add_parser("dynamodb", help="Query DynamoDB (MV projects)")
    dynamodb_parser.add_argument("project_id", nargs="?", help="Project ID to check")
    dynamodb_parser.add_argument("--list", action="store_true", help="List all projects")
    dynamodb_parser.add_argument("--recent", type=int, metavar="N", help="Show N most recent projects")
    dynamodb_parser.add_argument("--scenes", action="store_true", help="Show scenes for a project")
    
    # SQLite subparser
    sqlite_parser = subparsers.add_parser("sqlite", help="Query SQLite (Jobs and Stages)")
    sqlite_parser.add_argument("job_id", nargs="?", help="Job ID to check")
    sqlite_parser.add_argument("--list", action="store_true", help="List all jobs")
    sqlite_parser.add_argument("--recent", type=int, metavar="N", help="Show N most recent jobs")
    sqlite_parser.add_argument("--status", choices=["pending", "processing", "completed", "failed"], 
                              help="Filter jobs by status")
    
    args = parser.parse_args()
    
    if not args.database:
        parser.print_help()
        return
    
    if args.database == "dynamodb":
        # Initialize DynamoDB tables
        try:
            init_dynamodb_tables()
        except Exception as e:
            print(f"Warning: Could not initialize DynamoDB tables: {e}")
        
        if args.list:
            list_dynamodb_projects()
        elif args.recent:
            show_recent_dynamodb_projects(args.recent)
        elif args.project_id:
            check_dynamodb_project(args.project_id, show_scenes=args.scenes)
        else:
            dynamodb_parser.print_help()
    
    elif args.database == "sqlite":
        if args.list:
            list_sqlite_jobs(status_filter=args.status)
        elif args.recent:
            show_recent_sqlite_jobs(args.recent)
        elif args.job_id:
            check_sqlite_job(args.job_id)
        else:
            sqlite_parser.print_help()


if __name__ == "__main__":
    main()

