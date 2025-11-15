"""
WebSocket endpoint router

Handles WebSocket connections at /ws/jobs/{job_id} for real-time progress updates.
"""

import json
import asyncio
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Path, Depends
from sqlalchemy.orm import Session
from typing import Dict, Set

from models import Job
from database import get_db
from redis_client import redis_client
from config import settings

logger = structlog.get_logger()

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    Manages WebSocket connections for real-time job progress updates.

    Maintains a registry of active connections per job and handles
    message broadcasting and cleanup.
    """

    def __init__(self):
        """Initialize connection manager."""
        # Dict[job_id, Set[WebSocket]]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, job_id: str):
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection to register
            job_id: Job ID this connection is monitoring
        """
        await websocket.accept()

        async with self._lock:
            if job_id not in self.active_connections:
                self.active_connections[job_id] = set()
            self.active_connections[job_id].add(websocket)

        logger.info(
            "websocket_connected",
            job_id=job_id,
            connection_count=len(self.active_connections[job_id])
        )

    async def disconnect(self, websocket: WebSocket, job_id: str):
        """
        Remove and cleanup a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
            job_id: Job ID this connection was monitoring
        """
        async with self._lock:
            if job_id in self.active_connections:
                self.active_connections[job_id].discard(websocket)

                # Remove job entry if no more connections
                if not self.active_connections[job_id]:
                    del self.active_connections[job_id]

        logger.info(
            "websocket_disconnected",
            job_id=job_id,
            remaining_connections=len(self.active_connections.get(job_id, set()))
        )

    async def send_message(self, job_id: str, message: dict):
        """
        Send message to all connections monitoring a job.

        Args:
            job_id: Job ID to send message to
            message: Message dictionary to send
        """
        if job_id not in self.active_connections:
            return

        # Get connections to send to (copy to avoid modification during iteration)
        async with self._lock:
            connections = list(self.active_connections.get(job_id, set()))

        # Send to all connections
        dead_connections = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(
                    "websocket_send_failed",
                    job_id=job_id,
                    error=str(e)
                )
                dead_connections.append(connection)

        # Clean up dead connections
        if dead_connections:
            async with self._lock:
                for connection in dead_connections:
                    self.active_connections[job_id].discard(connection)

                if not self.active_connections[job_id]:
                    del self.active_connections[job_id]

    def get_connection_count(self, job_id: str) -> int:
        """
        Get number of active connections for a job.

        Args:
            job_id: Job ID to check

        Returns:
            Number of active connections
        """
        return len(self.active_connections.get(job_id, set()))


# Global connection manager instance
manager = ConnectionManager()


async def subscribe_to_redis_updates(job_id: str):
    """
    Subscribe to Redis pub/sub for job progress updates.

    Listens for progress updates from Redis and broadcasts them
    to all connected WebSocket clients for the specified job.

    Args:
        job_id: Job ID to monitor
    """
    try:
        # Subtask 10.2: Subscribe to Redis pub/sub
        pubsub = redis_client.get_client().pubsub()

        # Subscribe to both status and progress channels
        pubsub.subscribe(settings.JOB_STATUS_CHANNEL, settings.JOB_PROGRESS_CHANNEL)

        logger.info("redis_pubsub_subscribed", job_id=job_id)

        # Listen for messages
        while manager.get_connection_count(job_id) > 0:
            try:
                message = pubsub.get_message(timeout=1.0)

                if message and message["type"] == "message":
                    try:
                        # Parse message data
                        data = json.loads(message["data"])

                        # Only broadcast if message is for this job
                        if data.get("job_id") == job_id:
                            logger.debug("redis_message_received", job_id=job_id, data=data)

                            # Subtask 10.3: Stream progress events to clients
                            await manager.send_message(job_id, data)

                    except json.JSONDecodeError as e:
                        logger.warning("invalid_redis_message", error=str(e))

                # Small sleep to prevent tight loop
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error("redis_message_error", job_id=job_id, error=str(e))
                await asyncio.sleep(1)  # Back off on errors

    except Exception as e:
        logger.error("redis_subscription_error", job_id=job_id, error=str(e))
    finally:
        # Cleanup subscription
        try:
            pubsub.unsubscribe()
            pubsub.close()
            logger.info("redis_pubsub_unsubscribed", job_id=job_id)
        except Exception as e:
            logger.warning("redis_pubsub_cleanup_error", error=str(e))


@router.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    job_id: str = Path(..., description="Unique job identifier (UUID)")
):
    """
    WebSocket endpoint for real-time job progress updates.

    Establishes a persistent WebSocket connection that streams real-time
    updates about a video generation job's progress.

    **Path Parameters:**
    - **job_id**: The unique identifier of the job to monitor

    **Connection Flow:**
    1. Client connects to `/ws/jobs/{job_id}`
    2. Server validates job exists and accepts connection
    3. Server subscribes to Redis pub/sub for job updates
    4. Server streams progress updates to client in real-time
    5. Connection remains open until client disconnects or job completes

    **Message Format:**
    ```json
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "stage": "video_gen",
      "progress": 75,
      "status": "processing",
      "message": "Generating video scenes...",
      "timestamp": "2025-01-14T10:05:00"
    }
    ```

    **JavaScript Client Example:**
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws/jobs/' + jobId);

    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      console.log(`Progress: ${update.progress}% - ${update.message}`);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('Connection closed');
    };
    ```

    **Python Client Example:**
    ```python
    import asyncio
    import websockets
    import json

    async def monitor_job(job_id):
        uri = f"ws://localhost:8000/ws/jobs/{job_id}"
        async with websockets.connect(uri) as websocket:
            async for message in websocket:
                update = json.loads(message)
                print(f"Progress: {update['progress']}%")
    ```
    """
    # Get database session for validation
    db = next(get_db())

    try:
        logger.info("websocket_connection_attempt", job_id=job_id)

        # Validate job exists in database
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.warning("websocket_job_not_found", job_id=job_id)
            await websocket.close(code=1008, reason=f"Job '{job_id}' not found")
            return

        # Subtask 10.1: Establish WebSocket connection
        await manager.connect(websocket, job_id)

        # Send initial status message
        initial_message = {
            "type": "connected",
            "job_id": job_id,
            "status": job.status,
            "message": f"Connected to job {job_id}"
        }
        await websocket.send_json(initial_message)

        # Start Redis subscription in background task
        # This will run until all connections for this job are closed
        subscription_task = None
        if manager.get_connection_count(job_id) == 1:
            # Only start subscription if this is the first connection
            subscription_task = asyncio.create_task(subscribe_to_redis_updates(job_id))
            logger.info("redis_subscription_started", job_id=job_id)

        try:
            # Keep connection alive and handle client messages
            while True:
                # Receive messages from client (mostly for keepalive)
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    logger.debug("websocket_message_received", job_id=job_id, data=data)

                    # Echo back or handle client commands if needed
                    try:
                        client_msg = json.loads(data)
                        if client_msg.get("type") == "ping":
                            await websocket.send_json({"type": "pong"})
                    except json.JSONDecodeError:
                        pass

                except asyncio.TimeoutError:
                    # Send keepalive ping
                    try:
                        await websocket.send_json({"type": "ping"})
                    except Exception:
                        break  # Connection dead

        except WebSocketDisconnect:
            logger.info("websocket_client_disconnected", job_id=job_id)

    except Exception as e:
        logger.error("websocket_error", job_id=job_id, error=str(e), exc_info=True)

    finally:
        # Subtask 10.4: Manage connection cleanup
        await manager.disconnect(websocket, job_id)

        # Cancel subscription task if this was the last connection
        if manager.get_connection_count(job_id) == 0 and subscription_task:
            subscription_task.cancel()
            try:
                await subscription_task
            except asyncio.CancelledError:
                pass
            logger.info("redis_subscription_cancelled", job_id=job_id)

        db.close()
        logger.info("websocket_cleanup_completed", job_id=job_id)


# Health check endpoint for WebSocket server
@router.get("/ws/health", tags=["Health"])
async def websocket_health():
    """
    WebSocket server health check.

    Returns:
        dict: Health status and active connection count
    """
    total_connections = sum(
        len(connections) for connections in manager.active_connections.values()
    )

    return {
        "status": "healthy",
        "websocket_server": "running",
        "active_jobs": len(manager.active_connections),
        "total_connections": total_connections
    }
