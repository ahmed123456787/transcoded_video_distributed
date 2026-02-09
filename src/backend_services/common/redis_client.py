import redis


class RedisClient:
    def __init__(self, host='redis_video', port=6379, db=0):
        self.client = redis.Redis(host=host, port=port, db=db)

    async def set_total_chunks(self, job_id: str, total_chunks: int):
        self.client.hset(f"job:{job_id}", "total_chunks", total_chunks)
        self.client.hset(f"job:{job_id}", "completed_chunks", 0)

    async def increment_completed_chunks(self, job_id: str) -> int:
        return self.client.hincrby(f"job:{job_id}", "completed_chunks", 1)

    async def is_job_complete(self, job_id: str) -> bool:
        job_data = self.client.hgetall(f"job:{job_id}")
        if not job_data:
            return False
        total_chunks = int(job_data[b'total_chunks'])
        completed_chunks = int(job_data[b'completed_chunks'])
        return completed_chunks >= total_chunks
    


redis_client = RedisClient()