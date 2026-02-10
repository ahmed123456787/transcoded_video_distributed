# Video Transcoding System - Worker Troubleshooting Guide

## Issue: Worker Hangs After Job Completion

### Problem

The worker successfully transcodes all chunks and merges them, but then hangs instead of gracefully exiting or continuing to the next job. The logs show a `CommitFailedError` due to Kafka rebalance timeout.

### Root Cause

The Kafka consumer has a `max_poll_interval_ms` setting that times out when message processing takes too long. Since video transcoding can take several minutes per chunk, the consumer rebalances before the commit is sent, causing a `CommitFailedError`.

### Solution Implemented

#### 1. **Increased Kafka Timeouts** (`worker/consumer.py`)

```python
self.consumer = aiokafka.AIOKafkaConsumer(
    self.topic,
    bootstrap_servers=self.bootstrap_servers,
    group_id=self.group_id,
    auto_offset_reset="earliest",
    enable_auto_commit=False,
    max_poll_interval_ms=600000,      # 10 minutes (was default 300s)
    session_timeout_ms=120000,         # 2 minutes
    heartbeat_interval_ms=30000,       # 30 seconds
    max_poll_records=1,                # Process one message at a time
    connections_max_idle_ms=540000,    # 9 minutes
)
```

**Explanation:**

- `max_poll_interval_ms=600000`: Allows up to 10 minutes between polls for long transcoding
- `session_timeout_ms=120000`: Session timeout of 2 minutes (detected by broker if worker dies)
- `heartbeat_interval_ms=30000`: Sends heartbeat every 30 seconds to stay alive
- `max_poll_records=1`: Process one chunk at a time for better control
- `connections_max_idle_ms=540000`: Keep connections alive during processing

#### 2. **Better State Tracking** (`worker/worker.py`)

```python
self.processing_job = None  # Track current job being processed

# Set during processing
self.processing_job = job_id

# Clear after completion or error
self.processing_job = None
```

#### 3. **Graceful Shutdown** (`worker/worker.py`)

```python
async def start(self):
    logger.info("Starting chunk transcoding worker...")
    await self.consumer.start()
    try:
        await self.consumer.consume(self.process_chunk)
    except KeyboardInterrupt:
        logger.info("Worker shutting down...")
    finally:
        # Give a moment to ensure commit is processed
        if self.processing_job:
            logger.info(f"Waiting for job {self.processing_job} to complete...")
            await asyncio.sleep(2)
        await self.consumer.stop()
        logger.info("Worker stopped")
```

#### 4. **Redis Job Completion Tracking** (`common/redis_client.py`)

```python
async def mark_job_complete(self, job_id: str):
    """Mark a job as complete in Redis."""
    self.client.hset(f"job:{job_id}", "status", "completed")
    self.client.expire(f"job:{job_id}", 86400)  # Expire after 24 hours
```

---

## Expected Behavior After Fix

### Successful Processing Flow

```
1. Worker receives message from Kafka
   ↓
2. Worker transcodes chunk (can take 1-10 minutes)
   ↓
3. Worker uploads to MinIO
   ↓
4. Worker updates Redis (completed_chunks++)
   ↓
5. Worker checks if all chunks done
   ├─ No  → Commits offset to Kafka → Ready for next message
   └─ Yes → Triggers merge → Uploads final video → Marks job complete → Commits offset
   ↓
6. Worker continues listening for new messages
```

### Logs Should Show

```
INFO:__main__:Processing chunk 0 for job dd938dc6-f2b6-4742-b217-85f125d6d7ee
INFO:__main__:Downloaded chunk
INFO:__main__:Transcoded: /tmp/transcoding_worker/.../transcoded_000.mp4
INFO:__main__:Uploading transcoded chunk to transcoded/dd938dc6.../chunk_000.mp4
INFO:__main__:Job dd938dc6...: 1 chunks completed
INFO:__main__:Processing chunk 1 for job dd938dc6...
...
INFO:__main__:Job dd938dc6...: 9 chunks completed
INFO:__main__:All chunks completed for job dd938dc6.... Starting merge...
INFO:__main__:Starting merge for job dd938dc6...
INFO:__main__:Downloading chunk 0 from transcoded/dd938dc6.../chunk_000.mp4
...
INFO:__main__:Successfully merged chunks: /tmp/video_merge/.../final_video_dd938dc6....mp4
INFO:__main__:Uploading final video to transcoded/dd938dc6.../output_1080p.mp4
INFO:__main__:Successfully completed job dd938dc6.... Final video: transcoded/dd938dc6.../output_1080p.mp4
INFO:__main__:Job dd938dc6.... merge completed successfully!
INFO:worker.consumer:Committing offset for message at partition 0, offset 0
INFO:worker.consumer:Successfully committed offset
INFO:worker.consumer:Received message on partition 0, offset 1  # Ready for next message
```

---

## Monitoring Worker Status

### 1. Check Worker Logs

```bash
# Follow all worker logs
docker-compose logs -f worker

# Follow specific worker instance
docker-compose logs -f worker_1

# View last 100 lines
docker-compose logs --tail=100 worker
```

### 2. Check Redis Job Status

```bash
# Connect to Redis
redis-cli -p 6378

# View job progress
HGETALL job:dd938dc6-f2b6-4742-b217-85f125d6d7ee

# Output should show:
# "total_chunks" => "9"
# "completed_chunks" => "9"
# "status" => "completed"

# View all jobs
KEYS job:*

# Delete a job (cleanup)
DEL job:uuid
```

### 3. Check MinIO for Output Files

```bash
# Login to MinIO console: http://localhost:9001
# Username: minioadmin
# Password: minioadmin

# Check paths:
# raw/{uuid}.mp4                           # Original upload
# chunks/{job_id}/chunk_000.ts             # Raw chunks
# transcoded/{job_id}/chunk_000.mp4        # Transcoded chunks
# transcoded/{job_id}/output_1080p.mp4     # Final merged video
```

### 4. Check Kafka Messages

```bash
# Connect to Kafka container
docker exec kafka_video /bin/bash

# List topics
/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list

# View messages in topic
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic video-chunks \
  --from-beginning

# View consumer group status
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group transcoding-workers \
  --describe
```

---

## Performance Tuning

### Adjust Transcoding Speed vs Quality

Edit `worker/worker.py`:

**For Faster Processing:**

```python
cmd = [
    "ffmpeg",
    "-y",
    "-i", str(input_path),
    "-vf", f"scale=-1:{height}",
    "-c:v", "libx264",
    "-preset", "ultrafast",  # Fastest but lowest quality
    "-b:v", f"{bitrate}k",
    ...
]
```

**For Better Quality:**

```python
cmd = [
    ...
    "-preset", "slow",  # Slower but highest quality
    ...
]
```

**Preset Options (fastest → slowest):**

- `ultrafast` - 2-3x faster, lowest quality
- `superfast` - 1.5-2x faster, low quality
- `veryfast` - fastest reasonable quality
- `faster` - good speed, good quality
- `fast` - default balance (current)
- `medium` - slower, better quality
- `slow` - much slower, very good quality

### Adjust Bitrate

Lower bitrate = faster processing + smaller files, but lower quality:

```python
# In worker.py process_chunk():
self.transcoder.transcode_to_resolution(
    input_path=chunk_path,
    output_path=output_path,
    resolution=chunk_msg.resolution,
    bitrate=chunk_msg.bitrate  # Controlled by message from API
)
```

**Recommended Bitrates:**

- 2500 kbps - Fast, small, low quality
- 5000 kbps - Balanced (current)
- 8000 kbps - Slower, larger, high quality
- 12000 kbps - Very slow, very large, very high quality

### Scale Workers

Run multiple worker instances for parallel processing:

```bash
# Start 4 workers (instead of default 2)
docker-compose up -d --scale worker=4

# View all running workers
docker-compose ps

# Scale down to 2
docker-compose up -d --scale worker=2
```

---

## Common Issues & Fixes

### Issue: Worker crashes with "Connection refused"

**Cause:** MinIO or Kafka not running
**Fix:**

```bash
docker-compose ps  # Check all services
docker-compose up -d  # Restart all
docker-compose logs minio
docker-compose logs kafka
```

### Issue: "max_poll_interval_ms" timeout still occurs

**Cause:** Single chunk takes longer than 10 minutes
**Fix:** Increase timeout further in `worker/consumer.py`:

```python
max_poll_interval_ms=1200000,  # 20 minutes instead of 10
```

### Issue: Worker processes message twice

**Cause:** Commit failed and message was reprocessed
**Solution:** This is expected behavior - you can make processing idempotent by checking if chunk was already uploaded:

```python
# In upload_transcoded_chunk(), check if file exists first
try:
    self.minio_client.stat_object("videos", s3_key)
    logger.info(f"Chunk already exists: {s3_key}")
    return s3_key
except:
    # File doesn't exist, upload it
    self.minio_client.upload_file(str(local_path), s3_key)
```

### Issue: Merge fails with "chunk not found"

**Cause:** Not all chunks were transcoded before merge started
**Fix:** Ensure Redis tracking is correct:

```bash
redis-cli -p 6378
HGETALL job:uuid
# Verify total_chunks matches actual transcoded chunks
ls /tmp/video_merge/uuid/chunk_*.mp4 | wc -l
```

### Issue: Disk space runs out

**Cause:** Temporary files not cleaned up
**Fix:**

```bash
# Clear temp directories
rm -rf /tmp/transcoding_worker/*
rm -rf /tmp/video_merge/*

# Check disk usage
du -sh /tmp/transcoding_worker
du -sh /tmp/video_merge
```

---

## Docker Compose Configuration

To adjust worker configuration, edit `docker-compose.yml`:

```yaml
worker:
  build:
    context: .
    dockerfile: src/backend_services/Dockerfile
  container_name: video_transcoding_worker
  env_file:
    - src/backend_services/.env
  environment:
    - KAFKA_BROKER=kafka:9093
  command: python -m worker.worker
  depends_on:
    - kafka
    - minio
    - redis
  networks:
    - app-net
  volumes:
    - ./src/backend_services:/app/src
    - worker_temp:/tmp/transcoding_worker
    - worker_merge:/tmp/video_merge
  working_dir: /app/src
  restart: unless-stopped
  deploy:
    replicas: 2 # Change this to scale workers
```

### Adjust Resource Limits

```yaml
worker:
  deploy:
    replicas: 2
    resources:
      limits:
        cpus: "2" # Max 2 CPU cores
        memory: 4G # Max 4GB RAM
      reservations:
        cpus: "1"
        memory: 2G
```

---

## Monitoring Dashboard

Create a simple monitoring script to track progress:

```bash
#!/bin/bash
# save as: monitor.sh

while true; do
    clear
    echo "=== Video Transcoding System Status ==="
    echo ""
    echo "--- Worker Instances ---"
    docker-compose ps | grep worker
    echo ""
    echo "--- Active Redis Jobs ---"
    redis-cli -p 6378 KEYS "job:*" | while read key; do
        echo "$key:"
        redis-cli -p 6378 HGETALL "$key"
        echo ""
    done
    echo ""
    echo "--- Temp Directory Sizes ---"
    echo "Transcoding: $(du -sh /tmp/transcoding_worker 2>/dev/null || echo '0')"
    echo "Merge: $(du -sh /tmp/video_merge 2>/dev/null || echo '0')"
    echo ""
    echo "Press Ctrl+C to exit"
    sleep 5
done
```

Usage:

```bash
chmod +x monitor.sh
./monitor.sh
```

---

## Deployment Checklist

Before going to production:

- [ ] Test with actual video files (not just small test files)
- [ ] Verify FFmpeg is installed in Docker image
- [ ] Set appropriate worker replicas for your hardware
- [ ] Configure Kafka replication factor > 1
- [ ] Enable MinIO versioning for backups
- [ ] Set up Redis persistence
- [ ] Configure database backups
- [ ] Set up log aggregation (ELK, Splunk, etc.)
- [ ] Test worker scaling up/down
- [ ] Test with network failures
- [ ] Monitor CPU, memory, and disk usage
- [ ] Set up alerts for job failures
- [ ] Document recovery procedures
