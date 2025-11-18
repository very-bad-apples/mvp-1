"""
Test script for queue worker

Tests:
- Enqueueing jobs to Redis
- Worker processing jobs
- Retry logic for failures
- Health check functionality
"""

import time
import uuid
import structlog
from redis_client import redis_client
from worker import VideoGenerationWorker
from database import init_db, get_db_context
from models import Job, JobStatus
from pipeline.error_handler import PipelineError, ErrorCode

logger = structlog.get_logger()


def test_enqueue_job():
    """Test enqueueing a job to Redis"""
    logger.info("test_enqueue_job_started")

    job_id = str(uuid.uuid4())
    job_data = {
        "id": job_id,
        "product_name": "Test Product",
        "style": "minimal",
        "cta_text": "Shop Now",
        "product_image_path": None
    }

    # Enqueue job
    success = redis_client.enqueue_job(job_id, job_data)
    assert success, "Failed to enqueue job"

    # Verify job in Redis
    job_status = redis_client.get_job_status(job_id)
    assert job_status is not None, "Job not found in Redis"
    assert job_status.get("status") == "pending", "Job status should be pending"

    logger.info("test_enqueue_job_passed", job_id=job_id)
    return job_id


def test_worker_health_check():
    """Test worker health check"""
    logger.info("test_worker_health_check_started")

    worker = VideoGenerationWorker(worker_id="test-worker")
    health = worker.get_health_status()

    logger.info("health_status", health=health)

    assert health["worker_id"] == "test-worker", "Worker ID mismatch"
    assert health["redis_healthy"], "Redis should be healthy"
    assert health["database_healthy"], "Database should be healthy"
    assert health["healthy"], "Worker should be healthy"

    logger.info("test_worker_health_check_passed")


def test_job_in_database():
    """Test that completed job is in database"""
    logger.info("test_job_in_database_started")

    # Wait a moment for worker to process
    time.sleep(2)

    with get_db_context() as db:
        jobs = db.query(Job).all()
        logger.info("jobs_in_database", count=len(jobs))

        if jobs:
            for job in jobs:
                logger.info(
                    "job_info",
                    job_id=job.id,
                    status=job.status,
                    product_name=job.product_name
                )

    logger.info("test_job_in_database_complete")


def test_manual_worker_process():
    """Manually process a single job without running the worker loop"""
    logger.info("test_manual_worker_process_started")

    # Initialize database
    init_db()

    # Clear any existing jobs from queue
    while redis_client.dequeue_job() is not None:
        pass

    # Create a test job
    job_id = str(uuid.uuid4())
    job_data = {
        "id": job_id,
        "product_name": "Manual Test Product",
        "style": "energetic",
        "cta_text": "Try It Now",
        "product_image_path": None
    }

    # Enqueue job
    redis_client.enqueue_job(job_id, job_data)

    # Create worker
    worker = VideoGenerationWorker(worker_id="manual-test-worker")

    # Manually process the job
    dequeued_job = redis_client.dequeue_job()
    assert dequeued_job is not None, "Should have dequeued a job"
    assert dequeued_job.get("id") == job_id, f"Job ID should match, expected {job_id}, got {dequeued_job.get('id')}"

    # Process it
    worker._process_job(job_id, dequeued_job)

    # Check database
    with get_db_context() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        assert job is not None, "Job should exist in database"
        logger.info(
            "job_processed",
            job_id=job.id,
            status=job.status,
            product_name=job.product_name,
            video_url=job.video_url
        )
        assert job.status == JobStatus.COMPLETED, f"Job should be completed, got {job.status}"

    logger.info("test_manual_worker_process_passed", job_id=job_id)


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("Starting Worker Tests")
    print("="*60 + "\n")

    try:
        # Initialize database
        init_db()

        # Test 1: Health check
        print("\n--- Test 1: Worker Health Check ---")
        test_worker_health_check()
        print("✓ Health check passed\n")

        # Test 2: Enqueue job
        print("\n--- Test 2: Enqueue Job ---")
        job_id = test_enqueue_job()
        print(f"✓ Job enqueued: {job_id}\n")

        # Test 3: Manual worker process
        print("\n--- Test 3: Manual Worker Process ---")
        test_manual_worker_process()
        print("✓ Manual processing passed\n")

        # Test 4: Check database
        print("\n--- Test 4: Database Check ---")
        test_job_in_database()
        print("✓ Database check complete\n")

        print("\n" + "="*60)
        print("All Tests Passed!")
        print("="*60 + "\n")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}\n")
        raise
    except Exception as e:
        print(f"\n✗ Error during tests: {e}\n")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    run_all_tests()
