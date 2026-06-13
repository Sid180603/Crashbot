"""
LLM Response Caching
Cache expensive LLM API calls using Redis
"""
import json
import hashlib
from typing import Dict, Any, Optional
import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global Redis client
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """Get or create Redis client"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return _redis_client


def generate_cache_key(crash_data: Dict[str, Any]) -> str:
    """
    Generate cache key from crash data signature
    
    Uses exception code, faulting module, and first few stack frames
    to create a unique hash for similar crashes
    """
    # Extract key identifying features
    signature = {
        "exception_code": crash_data.get("exception_code"),
        "faulting_module": crash_data.get("faulting_module"),
        "platform": crash_data.get("platform"),
        "architecture": crash_data.get("architecture"),
    }
    
    # Include first 5 stack frames (most relevant)
    stack_trace = crash_data.get("stack_trace", [])
    if stack_trace:
        signature["stack_trace_top5"] = [
            {
                "module": frame.get("module"),
                "function": frame.get("function"),
                "address": frame.get("address")
            }
            for frame in stack_trace[:5]
        ]
    
    # Create hash
    signature_str = json.dumps(signature, sort_keys=True)
    hash_obj = hashlib.sha256(signature_str.encode())
    return f"llm:crash:{hash_obj.hexdigest()[:16]}"


async def get_cached_analysis(crash_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached LLM analysis if available
    
    Returns:
        Cached analysis dict or None if not found
    """
    try:
        client = await get_redis_client()
        cache_key = generate_cache_key(crash_data)
        
        cached = await client.get(cache_key)
        if cached:
            logger.info(f"Cache HIT for key: {cache_key}")
            return json.loads(cached)
        
        logger.info(f"Cache MISS for key: {cache_key}")
        return None
        
    except Exception as e:
        logger.warning(f"Redis cache read failed: {e}")
        return None


async def cache_analysis(crash_data: Dict[str, Any], analysis: Dict[str, Any], ttl: int = 3600) -> bool:
    """
    Cache LLM analysis result
    
    Args:
        crash_data: Original crash data
        analysis: LLM analysis result
        ttl: Time to live in seconds (default 1 hour)
        
    Returns:
        True if cached successfully, False otherwise
    """
    try:
        client = await get_redis_client()
        cache_key = generate_cache_key(crash_data)
        
        # Store with TTL
        await client.setex(
            cache_key,
            ttl,
            json.dumps(analysis)
        )
        
        logger.info(f"Cached analysis for key: {cache_key} (TTL: {ttl}s)")
        return True
        
    except Exception as e:
        logger.warning(f"Redis cache write failed: {e}")
        return False


async def invalidate_cache(crash_data: Dict[str, Any]) -> bool:
    """
    Invalidate cached analysis for specific crash signature
    
    Returns:
        True if invalidated, False otherwise
    """
    try:
        client = await get_redis_client()
        cache_key = generate_cache_key(crash_data)
        
        deleted = await client.delete(cache_key)
        if deleted:
            logger.info(f"Invalidated cache for key: {cache_key}")
        return bool(deleted)
        
    except Exception as e:
        logger.warning(f"Redis cache invalidation failed: {e}")
        return False


async def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    try:
        client = await get_redis_client()
        info = await client.info("stats")
        
        return {
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": (
                info.get("keyspace_hits", 0) / 
                max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
            ) * 100,
        }
    except Exception as e:
        logger.warning(f"Failed to get cache stats: {e}")
        return {}
