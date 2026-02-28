import os
import logging
from datetime import datetime, timezone, timedelta

from fastapi import Request
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Redis Connection setup
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    logger.error(f"Failed to initialize Redis client: {e}")
    redis_client = None

# Rate Limit Config
DAILY_LIMIT = 50
HOURLY_LIMIT = 10
IP_MIN_LIMIT = 20
IP_BLOCK_SECONDS = 600  # 10 minutes

class RateLimitException(Exception):
    def __init__(self, message: str, reset_time: str):
        self.message = message
        self.reset_time = reset_time

async def check_rate_limit(request: Request):
    """
    FastAPI Dependency for rate limiting based on Session ID and IP address.
    """
    if not redis_client:
        logger.warning("Redis client not available, skipping rate limit check.")
        return True

    # Get IP address
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else "unknown_ip"

    # Get Session ID from header or generate a fallback one based on IP (to apply some limit)
    session_id = request.headers.get("X-Session-ID", f"fallback_{ip_address}")
    
    now = datetime.now(timezone.utc)
    kst = timezone(timedelta(hours=9))
    now_kst = now.astimezone(kst)
    today_str = now_kst.strftime("%Y%m%d")
    current_hour_str = now_kst.strftime("%Y%m%d%H")
    
    # 1. IP-level Bot protection
    ip_key = f"rate_limit:ip:{ip_address}:{today_str}"
    block_key = f"block:ip:{ip_address}"
    
    try:
        # Check if already blocked
        is_blocked = await redis_client.exists(block_key)
        if is_blocked:
            raise RateLimitException(
                message="비정상적인 트래픽이 감지되어 일시적으로 이용이 제한되었습니다.",
                reset_time=(now_kst + timedelta(seconds=IP_BLOCK_SECONDS)).isoformat()
            )
            
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.incr(ip_key)
            pipe.expire(ip_key, 60, nx=True)  # Count in 1 min window
            res = await pipe.execute()
            ip_count = res[0]
            
        if ip_count > IP_MIN_LIMIT:
            await redis_client.setex(block_key, IP_BLOCK_SECONDS, "1")
            raise RateLimitException(
                message="비정상적인 트래픽이 감지되어 일시적으로 이용이 제한되었습니다.",
                reset_time=(now_kst + timedelta(seconds=IP_BLOCK_SECONDS)).isoformat()
            )
            
        # 2. Session-level throttling
        daily_key = f"rate_limit:session:{session_id}:daily:{today_str}"
        hourly_key = f"rate_limit:session:{session_id}:hourly:{current_hour_str}"
        
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.incr(daily_key)
            pipe.expire(daily_key, 86400, nx=True)
            pipe.incr(hourly_key)
            pipe.expire(hourly_key, 3600, nx=True)
            session_counts = await pipe.execute()
            
            daily_count = session_counts[0]
            hourly_count = session_counts[2]
            
        if daily_count > DAILY_LIMIT:
            next_day_reset = (now_kst + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            raise RateLimitException(
                message=f"일일 무료 분석 횟수({DAILY_LIMIT}회)를 모두 소진했습니다. 내일 다시 이용해주세요!",
                reset_time=next_day_reset.isoformat()
            )
            
        if hourly_count > HOURLY_LIMIT:
            next_hour_reset = (now_kst + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            raise RateLimitException(
                message=f"단기 분석 요청이 너무 많습니다. 잠시 후 1시간 뒤에 다시 시도해주세요. (제한: {HOURLY_LIMIT}회/h)",
                reset_time=next_hour_reset.isoformat()
            )

    except redis.RedisError as e:
        logger.error(f"Redis error during rate limiting: {e}")
        # Fail open
        pass

    return True
