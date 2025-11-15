# Queue Worker Documentation

## Overview

The queue worker (`worker.py`) is responsible for processing video generation jobs from the Redis queue. It's designed to be:

- **Reliable**: Exponential backoff retry logic for transient failures
- **Observable**: Real-time progress updates via Redis pub/sub
- **Scalable**: Multiple workers can run simultaneously
- **Resilient**: Graceful shutdown handling with job re-queuing
- **Maintainable**: Comprehensive logging with structlog

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   FastAPI   │─────▶│  Redis Queue │─────▶│   Worker    │
│     API     │      │   (BLPOP)    │      │  (worker.py)│
└─────────────┘      └──────────────┘      └─────────────┘
                             │                     │
                             ▼                     ▼
                     ┌──────────────┐      ┌─────────────┐
                     │  Pub/Sub     │      │  Database   │
                     │  (Progress)  │      │  (Status)   │
                     └──────────────┘      └─────────────┘
```

## Key Features

### 1. Queue Processing

- **Blocking Pop (BLPOP)**: Efficiently waits for jobs without polling
- **Sequential Processing**: Processes one job at a time per worker
- **Fair Distribution**: Multiple workers share the queue automatically

### 2. Retry Logic

```python
# Exponential backoff
Attempt 1: 2s delay
Attempt 2: 4s delay
Attempt 3: 8s delay (max retries)
```

**Retryable Errors**:
- External API failures (Claude, Replicate, ElevenLabs)
- Network timeouts
- Rate limiting
- Temporary Redis/Database connection issues

**Non-Retryable Errors**:
- Invalid input (validation errors)
- Missing required fields
- File too large
- Unsupported format

### 3. Progress Updates

Workers publish real-time progress via Redis pub/sub:

```json
{
  "job_id": "uuid",
  "stage": "script_gen",
  "progress": 25,
  "worker_id": "worker-1"
}
```

Stages:
1. `script_gen` - Script generation (0-25%)
2. `voice_gen` - Voice generation (25-50%)
3. `video_gen` - Video generation (50-75%)
4. `compositing` - Final compositing (75-100%)

### 4. Graceful Shutdown

Workers handle `SIGTERM` and `SIGINT` signals:

1. **Current Job Handling**:
   - Job in progress: Re-queue for another worker
   - No job: Clean shutdown

2. **Status Updates**:
   - Job marked as `pending` in database
   - Job re-added to Redis queue
   - Worker logs shutdown reason

### 5. Health Checks

Workers perform periodic health checks (every 30 seconds):

- Redis connection: `PING` command
- Database connection: `SELECT 1` query
- Status logging for monitoring

**Health Status Endpoint**:
```python
worker.get_health_status()
# Returns:
{
  "worker_id": "worker-1",
  "running": true,
  "current_job": "uuid or null",
  "redis_healthy": true,
  "database_healthy": true,
  "healthy": true,
  "timestamp": "2025-01-14T12:00:00Z"
}
```

## Running the Worker

### Single Worker

```bash
# Auto-generated worker ID
python worker.py

# Custom worker ID
python worker.py worker-1

# Using shell script
./run_worker.sh worker-1
```

### Multiple Workers (Horizontal Scaling)

```bash
# Terminal 1
./run_worker.sh worker-1

# Terminal 2
./run_worker.sh worker-2

# Terminal 3
./run_worker.sh worker-3
```

Or run in background:
```bash
./run_worker.sh worker-1 &
./run_worker.sh worker-2 &
./run_worker.sh worker-3 &
```

### Production Deployment

Use a process manager like **systemd** or **supervisor**:

#### systemd Example

Create `/etc/systemd/system/video-worker@.service`:

```ini
[Unit]
Description=Video Generation Worker %i
After=network.target redis.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/backend
Environment="PATH=/path/to/backend/venv/bin"
ExecStart=/path/to/backend/venv/bin/python worker.py worker-%i
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Start multiple workers:
```bash
systemctl start video-worker@1
systemctl start video-worker@2
systemctl start video-worker@3
systemctl enable video-worker@1
```

#### Supervisor Example

Create `/etc/supervisor/conf.d/video-workers.conf`:

```ini
[program:video-worker]
command=/path/to/backend/venv/bin/python worker.py worker-%(process_num)s
directory=/path/to/backend
process_name=%(program_name)s_%(process_num)s
numprocs=3
autostart=true
autorestart=true
startsecs=10
startretries=3
user=www-data
redirect_stderr=true
stdout_logfile=/var/log/video-worker-%(process_num)s.log
```

Control workers:
```bash
supervisorctl start video-worker:*
supervisorctl stop video-worker:*
supervisorctl restart video-worker:*
supervisorctl status
```

## Testing

### Run Tests

```bash
python test_worker.py
```

This will test:
- Health check functionality
- Job enqueueing
- Manual job processing
- Database persistence

### Manual Testing

1. **Start Redis** (if not running):
   ```bash
   redis-server
   ```

2. **Start Worker**:
   ```bash
   python worker.py test-worker
   ```

3. **Enqueue Test Job** (in another terminal):
   ```python
   from redis_client import redis_client
   import uuid

   job_id = str(uuid.uuid4())
   job_data = {
       "id": job_id,
       "product_name": "Test Product",
       "style": "minimal",
       "cta_text": "Buy Now"
   }
   redis_client.enqueue_job(job_id, job_data)
   ```

4. **Monitor Logs**: Watch worker terminal for processing logs

5. **Check Status**:
   ```python
   from redis_client import redis_client
   status = redis_client.get_job_status(job_id)
   print(status)
   ```

## Monitoring

### Logs

Workers use **structlog** for structured logging:

```json
{
  "event": "job_processing_started",
  "job_id": "uuid",
  "worker_id": "worker-1",
  "timestamp": "2025-01-14T12:00:00Z"
}
```

Key events to monitor:
- `worker_started` - Worker initialization
- `job_processing_started` - Job picked up
- `stage_started` - Stage processing
- `job_retry_scheduled` - Retry attempt
- `job_completed` - Success
- `job_failed` - Failure
- `worker_shutdown_complete` - Graceful shutdown

### Metrics to Track

1. **Job Throughput**:
   - Jobs processed per minute
   - Average processing time

2. **Error Rates**:
   - Failed jobs vs total jobs
   - Retry frequency

3. **Queue Depth**:
   ```python
   redis_client.get_client().llen("video_generation_queue")
   ```

4. **Worker Health**:
   - Number of active workers
   - Health check failures

## Scaling Guidelines

### When to Add Workers

- **Queue Depth**: If queue consistently has >10 pending jobs
- **Processing Time**: If average job time >5 minutes
- **Peak Hours**: Add workers during high-traffic periods

### Resource Requirements Per Worker

- **CPU**: ~1 core (AI API calls are I/O bound)
- **Memory**: ~512MB (mostly for FFmpeg operations)
- **Network**: Stable connection for API calls

### Optimal Configuration

For **100 jobs/hour**:
- 2-3 workers (assuming 3-5 min per job)

For **1000 jobs/hour**:
- 20-30 workers with load balancing

## Troubleshooting

### Worker Won't Start

1. **Check Redis Connection**:
   ```bash
   redis-cli ping
   ```

2. **Check Environment Variables**:
   ```bash
   env | grep REDIS_URL
   ```

3. **Check Database**:
   ```bash
   python -c "from database import init_db; init_db()"
   ```

### Jobs Not Processing

1. **Check Queue**:
   ```bash
   redis-cli llen video_generation_queue
   ```

2. **Check Worker Logs** for errors

3. **Verify Worker is Running**:
   ```bash
   ps aux | grep worker.py
   ```

### High Error Rate

1. **Check External APIs**:
   - OpenAI/Claude API status
   - Replicate API status
   - ElevenLabs API status

2. **Review Error Logs**:
   ```bash
   grep "job_failed" worker.log
   ```

3. **Check API Keys** in `.env`

### Memory Issues

1. **Monitor Memory Usage**:
   ```bash
   top -p $(pgrep -f worker.py)
   ```

2. **Reduce Concurrent Workers**

3. **Add Memory Limits** (systemd):
   ```ini
   MemoryMax=1G
   ```

## Integration with Pipeline Orchestrator

The worker is a placeholder for **Task 19: Pipeline Orchestrator**. Once implemented, the `_execute_job` method will be replaced with:

```python
def _execute_job(self, job_id: str, job_data: Dict[str, Any]):
    from pipeline.orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator(
        job_id=job_id,
        redis_client=redis_client,
        db_session=db
    )

    orchestrator.execute_pipeline(job_data)
```

## Security Considerations

1. **API Keys**: Never log API keys
2. **Job Data**: Sanitize user input before processing
3. **File Paths**: Validate all file paths to prevent directory traversal
4. **Resource Limits**: Implement timeouts to prevent infinite loops
5. **Error Messages**: Don't expose internal details to users

## Performance Optimization

1. **Connection Pooling**: Redis and Database already use connection pools
2. **Batch Operations**: Process multiple stages efficiently
3. **Caching**: Cache frequently accessed data
4. **Async I/O**: Consider asyncio for I/O-bound operations (future enhancement)

## Future Enhancements

- [ ] Priority queue support (high/normal/low priority jobs)
- [ ] Job cancellation support
- [ ] Dead letter queue for permanently failed jobs
- [ ] Metrics dashboard (Prometheus/Grafana)
- [ ] Auto-scaling based on queue depth
- [ ] Job scheduling (delayed/scheduled jobs)
- [ ] Worker pool management
