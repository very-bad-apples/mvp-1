"""
Worker process for Music Video jobs.

Processes async jobs from Redis queues:
- Scene generation
- Video composition
"""

import asyncio
import json
import structlog
from redis_client import redis_client
from workers.scene_worker import process_scene_generation_job
from workers.compose_worker import process_composition_job

logger = structlog.get_logger()


async def main_worker_loop():
    """
    Main worker loop to process jobs from Redis queues.
    """
    logger.info("mv_worker_start")

    # Queue names
    SCENE_QUEUE = "scene_generation_queue"
    COMPOSE_QUEUE = "video_composition_queue"

    redis_conn = redis_client.get_client()

    while True:
        try:
            # Check scene generation queue
            job_data = redis_conn.brpop(SCENE_QUEUE, timeout=1)
            if job_data:
                _, job_json = job_data
                job = json.loads(job_json)

                logger.info("scene_job_received", job_id=job.get("job_id"))

                result = await process_scene_generation_job(job["project_id"])

                logger.info("scene_job_complete", result=result)
                continue

            # Check composition queue
            job_data = redis_conn.brpop(COMPOSE_QUEUE, timeout=1)
            if job_data:
                _, job_json = job_data
                job = json.loads(job_json)

                logger.info("compose_job_received", job_id=job.get("job_id"))

                result = await process_composition_job(job["project_id"])

                logger.info("compose_job_complete", result=result)
                continue

            # No jobs, sleep briefly
            await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("mv_worker_shutdown")
            break
        except Exception as e:
            logger.error("worker_error", error=str(e), exc_info=True)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main_worker_loop())

