#!/usr/bin/env python3
"""
Quick script to check if a project exists in DynamoDB.

Usage:
    python scripts/check_project.py <project_id>    # Check specific project
    python scripts/check_project.py --list          # List all projects
    python scripts/check_project.py --recent 5      # Show 5 most recent projects
"""

import sys
import argparse
from mv_models import MVProjectItem
from dynamodb_config import init_dynamodb_tables

def check_project(project_id: str):
    """Check if a specific project exists."""
    pk = f"PROJECT#{project_id}"
    
    try:
        project = MVProjectItem.get(pk, "METADATA")
        print(f"✅ Project found: {project_id}")
        print(f"   Status: {project.status}")
        print(f"   Prompt: {project.conceptPrompt[:50]}...")
        print(f"   Created: {project.createdAt}")
        print(f"   Updated: {project.updatedAt}")
        return True
    except Exception as e:
        print(f"❌ Project not found: {project_id}")
        print(f"   Error: {e}")
        return False

def list_all_projects():
    """List all projects in the database."""
    # Query by status using GSI
    projects = list(MVProjectItem.status_index.query("pending"))
    projects.extend(list(MVProjectItem.status_index.query("processing")))
    projects.extend(list(MVProjectItem.status_index.query("completed")))
    projects.extend(list(MVProjectItem.status_index.query("failed")))
    
    # Filter to only project metadata items
    project_items = [p for p in projects if p.entityType == "project"]
    
    print(f"\n📊 Total projects: {len(project_items)}\n")
    
    for project in project_items:
        print(f"  {project.projectId}")
        print(f"    Status: {project.status}")
        print(f"    Created: {project.createdAt}")
        print(f"    Prompt: {project.conceptPrompt[:60]}...")
        print()

def show_recent(count: int = 10):
    """Show most recent projects."""
    # Get all projects
    all_projects = []
    for status in ["pending", "processing", "completed", "failed"]:
        all_projects.extend(list(MVProjectItem.status_index.query(status)))
    
    # Filter to project metadata only
    project_items = [p for p in all_projects if p.entityType == "project"]
    
    # Sort by creation date (most recent first)
    project_items.sort(key=lambda x: x.createdAt, reverse=True)
    
    print(f"\n📊 Most recent {min(count, len(project_items))} projects:\n")
    
    for project in project_items[:count]:
        print(f"  {project.projectId}")
        print(f"    Status: {project.status}")
        print(f"    Created: {project.createdAt}")
        print(f"    Prompt: {project.conceptPrompt[:60]}...")
        print()

def main():
    parser = argparse.ArgumentParser(description="Check DynamoDB projects")
    parser.add_argument("project_id", nargs="?", help="Project ID to check")
    parser.add_argument("--list", action="store_true", help="List all projects")
    parser.add_argument("--recent", type=int, metavar="N", help="Show N most recent projects")
    
    args = parser.parse_args()
    
    # Initialize tables (idempotent)
    try:
        init_dynamodb_tables()
    except Exception as e:
        print(f"Warning: Could not initialize tables: {e}")
    
    if args.list:
        list_all_projects()
    elif args.recent:
        show_recent(args.recent)
    elif args.project_id:
        check_project(args.project_id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

