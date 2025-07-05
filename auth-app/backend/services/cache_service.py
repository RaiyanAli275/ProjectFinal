import hashlib
import json
from typing import Optional, List, Dict, Any
import logging
from database.redis_manager import redis_manager
from database.config import DatabaseConfig

logger = logging.getLogger(__name__)


class CacheService:
    """Service for managing application caching"""

    def __init__(self):
        self.redis = redis_manager
        self.ttl = DatabaseConfig.CACHE_TTL

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters"""
        key_data = json.dumps(kwargs, sort_keys=True)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    # Recommendation Caching
    def cache_user_recommendations(
        self, user_id: str, recommendations: List[Dict], algorithm: str = "als"
    ) -> bool:
        """Cache user recommendations"""
        key = f"recommendations:user:{user_id}:{algorithm}"
        return self.redis.set_cache(key, recommendations, self.ttl["recommendations"])

    def get_cached_recommendations(
        self, user_id: str, algorithm: str = "als"
    ) -> Optional[List[Dict]]:
        """Get cached user recommendations"""
        key = f"recommendations:user:{user_id}:{algorithm}"
        return self.redis.get_cache(key)

    def invalidate_user_recommendations(self, user_id: str) -> bool:
        """Invalidate all recommendation caches for a user"""
        if not self.redis.is_available():
            return False

        pattern = f"recommendations:user:{user_id}:*"
        try:
            keys = self.redis.get_client().keys(pattern)
            if keys:
                self.redis.get_client().delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Error invalidating recommendations for user {user_id}: {e}")
            return False

    # Popular Books Caching
    def cache_popular_books(self, books: List[Dict], limit: int = 10) -> bool:
        """Cache popular books"""
        key = f"popular_books:limit:{limit}"
        return self.redis.set_cache(key, books, self.ttl["popular_books"])

    def get_cached_popular_books(self, limit: int = 10) -> Optional[List[Dict]]:
        """Get cached popular books"""
        key = f"popular_books:limit:{limit}"
        return self.redis.get_cache(key)

    # Language-Filtered Popular Books Caching
    def cache_language_filtered_books(
        self, user_id: str, books: List[Dict], limit: int = 50
    ) -> bool:
        """Cache language-filtered popular books for specific user"""
        key = f"popular_lang:{user_id}:{limit}"
        return self.redis.set_cache(key, books, 1800)  # 30 minutes TTL

    def get_cached_language_filtered_books(
        self, user_id: str, limit: int = 50
    ) -> Optional[List[Dict]]:
        """Get cached language-filtered popular books for specific user"""
        key = f"popular_lang:{user_id}:{limit}"
        return self.redis.get_cache(key)

    def invalidate_language_filtered_cache(self, user_id: str) -> bool:
        """Invalidate all language-filtered caches for a user"""
        if not self.redis.is_available():
            return False
        pattern = f"popular_lang:{user_id}:*"
        return self.redis.delete_keys_by_pattern(pattern) > 0

    # Search Results Caching
    def cache_search_results(
        self, query: str, results: List[Dict], limit: int = 20
    ) -> bool:
        """Cache search results"""
        key = self._generate_cache_key("search", query=query.lower(), limit=limit)
        return self.redis.set_cache(key, results, self.ttl["search_results"])

    def get_cached_search_results(
        self, query: str, limit: int = 20
    ) -> Optional[List[Dict]]:
        """Get cached search results"""
        key = self._generate_cache_key("search", query=query.lower(), limit=limit)
        return self.redis.get_cache(key)

    # Book Details Caching
    def cache_book_details(self, book_name: str, book_data: Dict) -> bool:
        """Cache individual book details"""
        key = f"book:details:{hashlib.md5(book_name.encode()).hexdigest()}"
        return self.redis.set_cache(key, book_data, self.ttl["book_details"])

    def get_cached_book_details(self, book_name: str) -> Optional[Dict]:
        """Get cached book details"""
        key = f"book:details:{hashlib.md5(book_name.encode()).hexdigest()}"
        return self.redis.get_cache(key)

    # User Preferences Caching
    def cache_user_preferences(self, user_id: str, preferences: Dict) -> bool:
        """Cache user preferences"""
        key = f"user:preferences:{user_id}"
        return self.redis.set_cache(key, preferences, self.ttl["user_preferences"])

    def get_cached_user_preferences(self, user_id: str) -> Optional[Dict]:
        """Get cached user preferences"""
        key = f"user:preferences:{user_id}"
        return self.redis.get_cache(key)

    def invalidate_user_preferences(self, user_id: str) -> bool:
        """Invalidate user preferences cache"""
        key = f"user:preferences:{user_id}"
        return self.redis.delete_cache(key)

    # Continue Reading Caching
    def cache_series_info(
        self, book_name: str, series_data: Dict, ttl: int = 604800
    ) -> bool:
        """Cache series info for 1 week by default"""
        key = f"series:{hashlib.md5(book_name.encode()).hexdigest()}"
        return self.redis.set_cache(key, series_data, ttl)

    def get_cached_series_info(self, book_name: str) -> Optional[Dict]:
        """Get cached series info"""
        key = f"series:{hashlib.md5(book_name.encode()).hexdigest()}"
        return self.redis.get_cache(key)

    def invalidate_series_cache(self, book_name: str) -> bool:
        """Invalidate series cache for a specific book"""
        key = f"series:{hashlib.md5(book_name.encode()).hexdigest()}"
        return self.redis.delete_cache(key)

    def cache_user_continue_reading(
        self, user_id: str, recommendations: List[Dict], ttl: int = 1800
    ) -> bool:
        """Cache user's continue reading recommendations for 30 minutes by default"""
        key = f"continue_reading:user:{user_id}"
        return self.redis.set_cache(key, recommendations, ttl)

    def get_cached_user_continue_reading(self, user_id: str) -> Optional[List[Dict]]:
        """Get cached user's continue reading recommendations"""
        key = f"continue_reading:user:{user_id}"
        return self.redis.get_cache(key)

    def invalidate_user_continue_reading_cache(self, user_id: str) -> bool:
        """Invalidate user's continue reading cache"""
        pattern = f"continue_reading:user:{user_id}*"
        return self.redis.delete_keys_by_pattern(pattern) > 0

    # Cache Statistics
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "redis_available": self.redis.is_available(),
            "connection_stats": self.redis.get_connection_stats(),
            "ttl_settings": self.ttl,
        }


# Global instance
cache_service = CacheService()
