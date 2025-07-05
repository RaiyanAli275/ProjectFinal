from bson.objectid import ObjectId
from datetime import datetime, timedelta
import hashlib
import json
from database.mongodb_manager import mongodb_manager
from services.cache_service import cache_service


class BookSeries:
    def __init__(self):
        # Use the shared MongoDB connection pool
        self.db = mongodb_manager.get_database("booksdata")
        self.collection = self.db["book_series"]
        self.user_cache_collection = mongodb_manager.get_user_auth_database()[
            "user_continue_reading_cache"
        ]
        # Create optimized indexes for performance
        self._create_indexes()

    def _create_indexes(self):
        """Create optimized indexes for performance"""
        try:
            # Index for book lookups
            self.collection.create_index(
                [("book_name", 1), ("book_author", 1)],
                name="book_lookup_idx",
                background=True,
            )

            # Index for series lookups
            self.collection.create_index(
                [("series_name", 1)], name="series_name_idx", background=True
            )

            # Index for verification status
            self.collection.create_index(
                [("verification_status", 1)],
                name="verification_status_idx",
                background=True,
            )

            # Index for request tracking
            self.collection.create_index(
                [("last_requested", -1)], name="last_requested_idx", background=True
            )

            # User cache indexes
            self.user_cache_collection.create_index(
                [("user_id", 1)], name="user_cache_idx", background=True
            )

            # TTL index for automatic expiration (expires after expires_at time)
            self.user_cache_collection.create_index(
                [("expires_at", 1)],
                expireAfterSeconds=0,
                name="ttl_idx",
                background=True,
            )

        except Exception as e:
            # Indexes might already exist
            print(f"Index creation note: {e}")

    def get_series_info(self, book_name, book_author=None):
        """
        Get series information for a book from cache or database
        Returns series data or None if not found
        """
        try:
            # Generate cache key
            cache_key = self._generate_series_cache_key(book_name, book_author)

            # Check Redis cache first (1 week TTL)
            cached_data = cache_service.redis.get_cache(cache_key)
            if cached_data is not None:
                return cached_data

            # Fall back to MongoDB
            query = {"book_name": book_name}
            if book_author:
                query["book_author"] = book_author

            series_doc = self.collection.find_one(query)

            if series_doc:
                # Update last requested timestamp
                self.collection.update_one(
                    {"_id": series_doc["_id"]},
                    {
                        "$set": {"last_requested": datetime.utcnow()},
                        "$inc": {"request_count": 1},
                    },
                )

                # Format for response
                series_data = {
                    "is_series": True,
                    "series_name": series_doc.get("series_name"),
                    "next_book": {
                        "title": series_doc.get("next_book_title"),
                        "author": series_doc.get("next_book_author"),
                        "description": series_doc.get("next_book_description"),
                        "order_in_series": series_doc.get("series_order"),
                    },
                    "confidence": series_doc.get("confidence_score", 0.8),
                    "verification_status": series_doc.get(
                        "verification_status", "verified"
                    ),
                }

                # Cache in Redis for 1 week (604800 seconds)
                cache_service.redis.set_cache(cache_key, series_data, 604800)

                return series_data

            return None

        except Exception as e:
            print(f"Error getting series info: {e}")
            return None

    def invalidate_user_cache(self, user_id):
        """
        Invalidate cached recommendations for a user
        """
        try:
            user_object_id = ObjectId(user_id)
            result = self.user_cache_collection.delete_many({"user_id": user_object_id})
            return result.deleted_count > 0

        except Exception as e:
            print(f"Error invalidating user cache: {e}")
            return False

    def _generate_series_cache_key(self, book_name, book_author=None):
        """
        Generate Redis cache key for series data
        """
        key_data = f"{book_name}:{book_author or ''}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"series:{key_hash}"
