# Video Transcoding System

A distributed video transcoding service using FastAPI, Kafka, MinIO, Redis, and FFmpeg. The system splits videos into chunks, transcodes them in parallel using worker processes, and merges them back together.

## Architecture Overview

```
┌─────────────────┐
│   Frontend      │
│  (React/Vite)   │
└────────┬────────┘
         │ Upload Video
         ▼
┌─────────────────────────────────┐
│   API Server (FastAPI)          │
│  - Generate Presigned URL       │
│  - Start Transcoding Job        │
└────────┬────────────────────────┘
         │ Chunk Video & Send to Kafka
         ▼
┌─────────────────────────────────┐
│   Message Queue (Kafka)         │
│   Topic: video-chunks           │
│   Partitions: Distributed       │
└────────┬────────────────────────┘
         │ Consume Messages
         ▼
┌─────────────────────────────────┐
│   Workers (Scalable)            │
│  - Download Chunks              │
│  - Transcode to 1080p           │
│  - Upload to MinIO              │
│  - Track Progress in Redis      │
└────────┬────────────────────────┘
         │ Update Redis
         ▼
┌─────────────────────────────────┐
│   Redis (State Management)      │
│  - Track Chunk Progress         │
│  - Store Job Metadata           │
└─────────────────────────────────┘

         │ When All Chunks Done
         ▼
┌─────────────────────────────────┐
│   Video Merger (Last Worker)    │
│  - Download All Transcoded      │
│  - Merge Using FFmpeg           │
│  - Upload Final Video           │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   MinIO (Object Storage)        │
│  - Raw Videos                   │
│  - Chunks                       │
│  - Transcoded Chunks            │
│  - Final Videos                 │
└─────────────────────────────────┘
```

## Components

### 1. Frontend (React + Vite + Tailwind)

- Video file upload interface
- Progress tracking
- Real-time status updates

**Key Files:**

- `src/frontend/src/App.tsx` - Main upload component
- `src/frontend/src/main.tsx` - Entry point
- `src/frontend/package.json` - Dependencies

### 2. API Server (FastAPI)

Handles:

- Video upload requests (generates presigned URLs)
- Job launch (chunks video and publishes to Kafka)
- Status queries
- Job management

**Key Files:**

- `src/backend_services/api_transcoder/main.py` - FastAPI app
- `src/backend_services/api_transcoder/controllers/upload_controller.py` - API endpoints
- `src/backend_services/api_transcoder/services/transcoding_service.py` - Orchestration

**Endpoints:**

```
POST   /api/video-signedUrl      - Get MinIO presigned upload URL
GET    /api/videos               - List all videos
POST   /api/job-launch           - Start transcoding job
GET    /api/jobs                 - List transcoding jobs
DELETE /api/jobs/{job_id}        - Cancel a job
GET    /api/chunk-jobs           - List chunk jobs
```

### 3. Worker Service (Scalable)

Consumes chunk transcoding messages from Kafka and:

1. Downloads raw chunks from MinIO
2. Transcodes to target resolution (1080p)
3. Uploads transcoded chunks back to MinIO
4. Tracks progress in Redis
5. Triggers merge when all chunks complete

**Key Files:**

- `src/backend_services/worker/worker.py` - Main worker logic
- `src/backend_services/worker/consumer.py` - Kafka consumer
- `src/backend_services/worker/utils.py` - Helper functions

**Key Classes:**

#### TranscodingWorker

Handles individual chunk transcoding:

```python
- download_chunk()              # Download from MinIO
- transcode_to_resolution()     # FFmpeg transcoding
- upload_transcoded_chunk()     # Upload to MinIO
- cleanup_local_files()         # Clean temp files
```

#### VideoMerger

Handles final video assembly:

```python
- download_all_chunks()         # Download all transcoded chunks
- create_concat_file()          # Create FFmpeg concat manifest
- merge_chunks()                # Merge using FFmpeg
- upload_final_video()          # Upload final video
```

#### ChunkTranscodingWorker

Main orchestrator:

```python
- process_chunk()               # Process single message
- merge_and_finalize_video()    # Merge when all done
- start()                       # Start consumer loop
```

### 4. Message Queue (Kafka)

**Topic:** `video-chunks`
**Partitions:** 1 (can scale)
**Consumer Group:** `transcoding-workers`

**Message Format:**

```json
{
  "id": "chunk-uuid",
  "chunk_index": 0,
  "target_format": "mp4",
  "resolution": "1080p",
  "bitrate": 5000,
  "chunk_s3_key": "chunks/job-id/chunk_000.ts"
}
```

### 5. State Management (Redis)

**Key Pattern:** `job:{job_id}`

**Hash Structure:**

```
job:uuid
├── total_chunks: <int>          # Total chunks for this job
└── completed_chunks: <int>      # Chunks completed so far
```

**Operations:**

```python
set_total_chunks(job_id, count)        # Initialize job
increment_completed_chunks(job_id)     # Track progress
is_job_complete(job_id)                # Check if done
```

### 6. Object Storage (MinIO)

**Bucket:** `videos`

**Directory Structure:**

```
videos/
├── raw/                         # Original uploaded videos
│   └── {uuid}.mp4
├── chunks/                      # Raw video chunks
│   └── {job_id}/
│       ├── chunk_000.ts
│       ├── chunk_001.ts
│       └── ...
└── transcoded/                  # Transcoded output
    └── {job_id}/
        ├── chunk_000.mp4        # Transcoded chunks
        ├── chunk_001.mp4
        └── output_1080p.mp4     # Final merged video
```

## Data Flow

### 1. Upload Phase

```
User uploads video via Frontend
    ↓
Frontend → API: /api/video-signedUrl
    ↓
API generates presigned MinIO URL
    ↓
Frontend uploads to MinIO directly
    ↓
Video stored in MinIO at: raw/{uuid}.mp4
```

### 2. Transcoding Job Launch

```
Frontend → API: /api/job-launch?video_id=xxx
    ↓
API creates TranscodingJob in DB
    ↓
API chunks video:
  - Downloads raw from MinIO
  - Splits into 60-second segments
  - Uploads chunks to MinIO at: chunks/{job_id}/chunk_000.ts, etc.
    ↓
API publishes to Kafka:
  - One message per chunk
  - Messages distributed across partitions
    ↓
Redis stores:
  - job:{job_id} → {total_chunks: N, completed_chunks: 0}
```

### 3. Worker Processing

```
Worker consumes Kafka message
    ↓
Worker extracts job_id from chunk path
    ↓
Worker downloads chunk from MinIO
    ↓
Worker transcodes with FFmpeg:
  - Resolution: 1080p
  - Bitrate: 5000 kbps
  - Codec: libx264 (H.264)
  - Audio: AAC 128kbps
    ↓
Worker uploads to MinIO: transcoded/{job_id}/chunk_000.mp4
    ↓
Worker updates Redis:
  - HINCRBY job:{job_id} completed_chunks 1
    ↓
Worker checks: is_job_complete(job_id)?
    ├─ No  → Continue processing next chunk
    └─ Yes → Trigger merge
```

### 4. Merge Phase

```
Last worker finishes chunk
    ↓
Worker checks Redis: all chunks done?
    ↓
Worker downloads all transcoded chunks from MinIO
    ↓
Worker creates FFmpeg concat manifest:
  file 'chunk_000.mp4'
  file 'chunk_001.mp4'
  file 'chunk_002.mp4'
    ↓
Worker runs FFmpeg concat:
  - Input: concat.txt manifest
  - Output: final_video.mp4
  - Codec copy (no re-encoding)
    ↓
Worker uploads final video:
  - MinIO: transcoded/{job_id}/output_1080p.mp4
    ↓
Worker cleans up temp files
    ↓
Job complete! ✓
```

## Setup & Running

### Prerequisites

- Docker & Docker Compose
- Python 3.11
- FFmpeg (in Docker)
- Node.js 18+ (for frontend)

### 1. Backend Setup

```bash
cd src/backend_services
cp .env.example .env
# Edit .env with your settings
```

### 2. Frontend Setup

```bash
cd src/frontend
npm install
npm run dev
```

### 3. Start All Services

```bash
docker-compose up -d
```

**Services:**

- API: http://localhost:8000
- Minio Console: http://localhost:9001
- Frontend: http://localhost:5173 (if running locally)
- Redis: localhost:6378

### 4. Scale Workers

```bash
# Run multiple worker instances
docker-compose up -d --scale worker=4
```

## API Usage Examples

### 1. Get Upload URL

```bash
curl -X POST http://localhost:8000/api/video-signedUrl \
  -H "Content-Type: application/json" \
  -d '{"filename": "video.mp4"}'
```

Response:

```json
{
  "video_id": "uuid",
  "upload_url": "http://localhost:9000/...",
  "message": "Upload URL generated"
}
```

### 2. Upload Video

```bash
curl -X PUT "http://localhost:9000/videos/raw/uuid.mp4" \
  --data-binary @video.mp4 \
  -H "Content-Type: video/mp4"
```

### 3. Launch Transcoding Job

```bash
curl -X POST http://localhost:8000/api/job-launch?video_id=uuid
```

Response:

```json
{
  "message": "Transcoding started",
  "video_id": "uuid",
  "job_id": "job-uuid",
  "chunks": 3
}
```

### 4. Check Job Status

```bash
curl http://localhost:8000/api/jobs
```

## Configuration

### Environment Variables (.env)

```properties
# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_EXTERNAL_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=videos

# Kafka
KAFKA_BROKER=kafka:9093

# Database
DATABASE_URL=sqlite:///./test.db
```

### Worker Configuration

Edit in `src/backend_services/worker/worker.py`:

- `chunk_duration`: Target chunk length (default: 60 seconds)
- `resolution`: Output resolution (default: 1080p)
- `bitrate`: Video bitrate (default: 5000 kbps)
- `preset`: FFmpeg preset: ultrafast, superfast, veryfast, faster, fast, medium (default: fast)

### Docker Compose

Edit in `docker-compose.yml`:

- `worker.deploy.replicas`: Number of worker instances (default: 2)
- Memory/CPU limits for workers
- Volume sizes

## Monitoring

### Worker Logs

```bash
docker-compose logs -f worker
```

### Redis Progress

```bash
redis-cli -p 6378
> HGETALL job:uuid
```

### Kafka Topics

```bash
docker exec kafka_video /opt/kafka/bin/kafka-topics.sh --list
```

### MinIO Browser

Visit: http://localhost:9001

- Username: minioadmin
- Password: minioadmin

## Performance Tuning

### 1. Parallel Workers

Increase `docker-compose.yml`:

```yaml
deploy:
  replicas: 8 # More workers = faster processing
```

### 2. FFmpeg Preset

Faster preset = lower quality but faster:

- `ultrafast` - fastest, lowest quality
- `fast` - good balance (current)
- `medium` - slower, better quality
- `slow` - much slower, best quality

### 3. Bitrate

Lower bitrate = smaller files, lower quality:

- 2500 kbps - low quality
- 5000 kbps - medium quality (current)
- 8000 kbps - high quality

### 4. Chunk Duration

Smaller chunks = better parallelism but more overhead:

- 30 seconds - high parallelism, more overhead
- 60 seconds - balanced (current)
- 120 seconds - lower overhead, less parallelism

## Error Handling

### Chunk Processing Failures

- Worker logs error
- Message NOT committed to Kafka
- Message reprocessed by another worker
- Automatic retry (Kafka consumer group)

### Merge Failures

- Logged with job_id
- Merge can be manually retried
- Chunks remain in MinIO

### Storage Issues

- Automatic cleanup of temp files
- Graceful handling if MinIO unavailable
- Queue accumulates until MinIO returns

## Database Schema

### Videos Table

```sql
CREATE TABLE videos (
  id UUID PRIMARY KEY,
  original_filename VARCHAR,
  s3_bucket VARCHAR,
  presigned_url TEXT,
  status VARCHAR,
  created_at TIMESTAMP
);
```

### TranscodingJobs Table

```sql
CREATE TABLE transcoding_jobs (
  id UUID PRIMARY KEY,
  video_id UUID FOREIGN KEY,
  resolution VARCHAR,
  s3_output_key VARCHAR,
  status VARCHAR,
  error_message TEXT
);
```

### JobChunks Table

```sql
CREATE TABLE job_chunks (
  id UUID PRIMARY KEY,
  job_id UUID FOREIGN KEY,
  chunk_s3_key VARCHAR,
  created_at TIMESTAMP
);
```

## Troubleshooting

### Workers not consuming messages

```bash
# Check Kafka is running
docker-compose logs kafka
# Check worker is connected
docker-compose logs worker
```

### Videos not merging

```bash
# Check Redis has job data
redis-cli -p 6378
HGETALL job:uuid
# Check transcoded chunks exist in MinIO
```

### Out of disk space

```bash
# Clear temp directories
rm -rf /tmp/transcoding_worker/*
rm -rf /tmp/video_merge/*
```

### FFmpeg issues

```bash
# Check FFmpeg is available in container
docker exec video_transcoding_worker ffmpeg -version
```

## License

MIT

## Support

For issues, check:

1. Docker logs: `docker-compose logs [service]`
2. MinIO browser for uploaded files
3. Redis for job tracking
4. Kafka topics for message flow
