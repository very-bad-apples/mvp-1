# Utility Scripts

This directory contains utility scripts for database inspection and maintenance.

## Scripts

### `check_database.py`

Inspect database contents for both DynamoDB (MV projects) and SQLite (Jobs).

**Usage:**

```bash
# DynamoDB - MV Projects
python scripts/check_database.py dynamodb --list              # List all projects
python scripts/check_database.py dynamodb --recent 5          # Show 5 most recent projects
python scripts/check_database.py dynamodb <project_id>        # Check specific project
python scripts/check_database.py dynamodb <project_id> --scenes # Show project with scenes

# SQLite - Jobs
python scripts/check_database.py sqlite --list                 # List all jobs
python scripts/check_database.py sqlite --recent 5             # Show 5 most recent jobs
python scripts/check_database.py sqlite <job_id>               # Check specific job
python scripts/check_database.py sqlite --status pending       # Filter by status
```

### `check_project.py`

Quick script to check if a DynamoDB project exists.

**Usage:**

```bash
python scripts/check_project.py <project_id>    # Check specific project
python scripts/check_project.py --list          # List all projects
python scripts/check_project.py --recent 5      # Show 5 most recent projects
```

## Running Scripts

All scripts should be run from the `backend/` directory:

```bash
cd backend
python scripts/check_database.py dynamodb --list
python scripts/check_project.py --recent 10
```

## Requirements

- DynamoDB Local must be running (via Docker Compose) for DynamoDB queries
- SQLite database file must exist for SQLite queries
- All backend dependencies must be installed

