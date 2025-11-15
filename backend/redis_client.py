"""
Redis client for job queue and pub/sub operations
"""

import json
import structlog
from typing import Optional, Dict, Any
from redis import Redis, ConnectionPool
from redis.exceptions import RedisError, ConnectionError
from config import settings

logger = structlog.get_logger()


class RedisClient:
    """Redis client with connection pooling and helper methods"""

    def __init__(self):
        """Initialize Redis client with connection pool"""
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
        self._connect()

    def _connect(self):
        """Establish Redis connection with connection pool"""
        try:
            self._pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
                health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
                decode_responses=True
            )
            self._client = Redis(connection_pool=self._pool)

            # Test connection
            self._client.ping()
            logger.info("redis_connected", url=settings.REDIS_URL)

        except ConnectionError as e:
            logger.error("redis_connection_failed", error=str(e))
            raise

    def get_client(self) -> Redis:
        """Get Redis client instance"""
        if self._client is None:
            self._connect()
        return self._client

    def ping(self) -> bool:
        """Check if Redis is connected"""
        try:
            return self._client.ping()
        except RedisError as e:
            logger.error("redis_ping_failed", error=str(e))
            return False

    def close(self):
        """Close Redis connection"""
        if self._client:
            self._client.close()
            logger.info("redis_connection_closed")

    # ===== Job Queue Operations =====

    def enqueue_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """
        Add a job to the processing queue

        Args:
            job_id: Unique job identifier
            job_data: Job data dictionary

        Returns:
            bool: Success status
        """
        try:
            job_data_json = json.dumps(job_data)
            self._client.rpush(settings.JOB_QUEUE_NAME, job_data_json)

            # Store job metadata
            self._client.hset(f"job:{job_id}", mapping={
                "id": job_id,
                "status": "pending",
                "data": job_data_json
            })

            # Set TTL for job data
            self._client.expire(f"job:{job_id}", settings.JOB_RESULT_TTL)

            logger.info("job_enqueued", job_id=job_id)
            return True

        except RedisError as e:
            logger.error("job_enqueue_failed", job_id=job_id, error=str(e))
            return False

    def dequeue_job(self) -> Optional[Dict[str, Any]]:
        """
        Get next job from the queue

        Returns:
            Optional[Dict]: Job data or None if queue is empty
        """
        try:
            result = self._client.blpop(settings.JOB_QUEUE_NAME, timeout=1)
            if result:
                _, job_data_json = result
                return json.loads(job_data_json)
            return None

        except RedisError as e:
            logger.error("job_dequeue_failed", error=str(e))
            return None

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status and metadata

        Args:
            job_id: Job identifier

        Returns:
            Optional[Dict]: Job data or None if not found
        """
        try:
            job_data = self._client.hgetall(f"job:{job_id}")
            if job_data:
                return job_data
            return None

        except RedisError as e:
            logger.error("get_job_status_failed", job_id=job_id, error=str(e))
            return None

    def update_job_status(self, job_id: str, status: str, **kwargs) -> bool:
        """
        Update job status and additional fields

        Args:
            job_id: Job identifier
            status: New status value
            **kwargs: Additional fields to update

        Returns:
            bool: Success status
        """
        try:
            update_data = {"status": status, **kwargs}
            self._client.hset(f"job:{job_id}", mapping=update_data)

            logger.info("job_status_updated", job_id=job_id, status=status)
            return True

        except RedisError as e:
            logger.error("update_job_status_failed", job_id=job_id, error=str(e))
            return False

    # ===== Pub/Sub Operations =====

    def publish_status(self, job_id: str, status: str, **kwargs) -> bool:
        """
        Publish job status update to subscribers

        Args:
            job_id: Job identifier
            status: Status value
            **kwargs: Additional metadata

        Returns:
            bool: Success status
        """
        try:
            message = json.dumps({
                "job_id": job_id,
                "status": status,
                **kwargs
            })

            self._client.publish(settings.JOB_STATUS_CHANNEL, message)
            logger.info("status_published", job_id=job_id, status=status)
            return True

        except RedisError as e:
            logger.error("publish_status_failed", job_id=job_id, error=str(e))
            return False

    def publish_progress(self, job_id: str, stage: str, progress: int, **kwargs) -> bool:
        """
        Publish job progress update to subscribers

        Args:
            job_id: Job identifier
            stage: Current processing stage
            progress: Progress percentage (0-100)
            **kwargs: Additional metadata

        Returns:
            bool: Success status
        """
        try:
            message = json.dumps({
                "job_id": job_id,
                "stage": stage,
                "progress": progress,
                **kwargs
            })

            self._client.publish(settings.JOB_PROGRESS_CHANNEL, message)
            logger.info("progress_published", job_id=job_id, stage=stage, progress=progress)
            return True

        except RedisError as e:
            logger.error("publish_progress_failed", job_id=job_id, error=str(e))
            return False

    def subscribe_to_status(self):
        """
        Subscribe to job status updates

        Returns:
            PubSub: Redis PubSub instance
        """
        pubsub = self._client.pubsub()
        pubsub.subscribe(settings.JOB_STATUS_CHANNEL)
        return pubsub

    def subscribe_to_progress(self):
        """
        Subscribe to job progress updates

        Returns:
            PubSub: Redis PubSub instance
        """
        pubsub = self._client.pubsub()
        pubsub.subscribe(settings.JOB_PROGRESS_CHANNEL)
        return pubsub


# Global Redis client instance
redis_client = RedisClient()
