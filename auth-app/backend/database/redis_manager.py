import redis
from redis.connection import ConnectionPool
from typing import Optional, Any, Union
import json
import logging
from .config import DatabaseConfig

logger = logging.getLogger(__name__)

class RedisManager:
    """Singleton Redis connection manager with connection pooling"""
    
    _instance: Optional['RedisManager'] = None
    _pool: Optional[ConnectionPool] = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls) -> 'RedisManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._pool is None:
            self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize Redis connection pool"""
        try:
            self._pool = ConnectionPool(
                host=DatabaseConfig.REDIS_HOST,
                port=DatabaseConfig.REDIS_PORT,
                password=DatabaseConfig.REDIS_PASSWORD,
                db=DatabaseConfig.REDIS_DB,
                **DatabaseConfig.REDIS_POOL_CONFIG
            )
            
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            self._client.ping()
            logger.info("Redis connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            # For development, continue without Redis if it's not available
            logger.warning("Continuing without Redis - caching will be disabled")
            self._client = None
    
    def get_client(self) -> Optional[redis.Redis]:
        """Get Redis client with connection pooling"""
        return self._client
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        return self._client is not None
    
    def set_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cache value with optional TTL"""
        if not self.is_available():
            return False
            
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            result = self._client.set(key, value, ex=ttl)
            return result
        except Exception as e:
            logger.error(f"Error setting cache for key {key}: {e}")
            return False
    
    def get_cache(self, key: str) -> Optional[Any]:
        """Get cache value"""
        if not self.is_available():
            return None
            
        try:
            value = self._client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value.decode('utf-8') if isinstance(value, bytes) else value
            return None
        except Exception as e:
            logger.error(f"Error getting cache for key {key}: {e}")
            return None
    
    def delete_cache(self, key: str) -> bool:
        """Delete cache value"""
        if not self.is_available():
            return False
            
        try:
            result = self._client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Error deleting cache for key {key}: {e}")
            return False
    
    def delete_keys_by_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern"""
        if not self.is_available():
            return 0
            
        try:
            keys = self._client.keys(pattern)
            if keys:
                deleted_count = self._client.delete(*keys)
                logger.info(f"Deleted {deleted_count} keys matching pattern: {pattern}")
                return deleted_count
            return 0
        except Exception as e:
            logger.error(f"Error deleting keys by pattern {pattern}: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.is_available():
            return False
            
        try:
            return bool(self._client.exists(key))
        except Exception as e:
            logger.error(f"Error checking existence for key {key}: {e}")
            return False
    
    def close_connection(self):
        """Close Redis connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._pool = None
            logger.info("Redis connection closed")
    
    def get_connection_stats(self) -> dict:
        """Get connection pool statistics - compatible with different Redis versions"""
        if not self._pool:
            return {'error': 'No connection pool available'}
            
        try:
            stats = {
                'max_connections': self._pool.max_connections,
                'pool_available': self.is_available()
            }
            
            # Try to get additional stats if available
            try:
                if hasattr(self._pool, 'created_connections'):
                    stats['created_connections'] = self._pool.created_connections
                if hasattr(self._pool, '_available_connections'):
                    stats['available_connections'] = len(self._pool._available_connections)
                if hasattr(self._pool, '_in_use_connections'):
                    stats['in_use_connections'] = len(self._pool._in_use_connections)
                    
                # Alternative way to get connection info
                if hasattr(self._pool, 'connection_kwargs'):
                    stats['connection_config'] = {
                        'host': self._pool.connection_kwargs.get('host', 'unknown'),
                        'port': self._pool.connection_kwargs.get('port', 'unknown'),
                        'db': self._pool.connection_kwargs.get('db', 'unknown')
                    }
            except Exception as e:
                stats['stats_error'] = f"Could not retrieve detailed stats: {e}"
                
            return stats
            
        except Exception as e:
            return {'error': f'Error retrieving connection stats: {e}'}

# Global instance
redis_manager = RedisManager()