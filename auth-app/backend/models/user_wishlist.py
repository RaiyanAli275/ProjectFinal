from bson.objectid import ObjectId
from datetime import datetime
from database.mongodb_manager import mongodb_manager
from services.cache_service import cache_service


class UserWishlist:
    def __init__(self):
        # Use the shared MongoDB connection pool
        self.db = mongodb_manager.get_user_auth_database()
        self.collection = self.db["user_wishlists"]

        # Create indexes for better performance
        try:
            self.collection.create_index(
                [("user_id", 1), ("book_name", 1)], unique=True
            )
            self.collection.create_index([("user_id", 1), ("added_at", -1)])
        except:
            # Indexes might already exist
            pass

    def add_to_wishlist(self, user_id, book_name, book_author, book_genres):
        """Add a book to user's wishlist"""
        try:
            user_object_id = ObjectId(user_id)

            # Check if book is already in wishlist
            existing_item = self.collection.find_one(
                {"user_id": user_object_id, "book_name": book_name}
            )

            if existing_item:
                return {"success": False, "message": "Book is already in your wishlist"}

            # Parse genres from string to list if needed
            genres_list = self._parse_genres(book_genres)

            # Add to wishlist
            wishlist_item = {
                "user_id": user_object_id,
                "book_name": book_name,
                "book_author": book_author,
                "book_genres": genres_list,
                "added_at": datetime.utcnow(),
            }

            result = self.collection.insert_one(wishlist_item)

            if result.inserted_id:
                # Invalidate user's wishlist cache
                self._invalidate_wishlist_cache(str(user_id))

                return {
                    "success": True,
                    "message": "Book added to wishlist successfully",
                    "wishlist_id": str(result.inserted_id),
                }
            else:
                return {"success": False, "message": "Failed to add book to wishlist"}

        except Exception as e:
            print(f"Error adding book to wishlist: {e}")
            return {"success": False, "message": "Internal server error"}

    def remove_from_wishlist(self, user_id, book_name):
        """Remove a book from user's wishlist"""
        try:
            user_object_id = ObjectId(user_id)

            result = self.collection.delete_one(
                {"user_id": user_object_id, "book_name": book_name}
            )

            if result.deleted_count > 0:
                # Invalidate user's wishlist cache
                self._invalidate_wishlist_cache(str(user_id))

                return {
                    "success": True,
                    "message": "Book removed from wishlist successfully",
                }
            else:
                return {"success": False, "message": "Book not found in wishlist"}

        except Exception as e:
            print(f"Error removing book from wishlist: {e}")
            return {"success": False, "message": "Internal server error"}

    def get_user_wishlist(self, user_id, limit=50, skip=0):
        """Get user's wishlist with pagination"""
        try:
            # Check cache first
            cache_key = f"wishlist:{user_id}:{limit}:{skip}"
            cached_wishlist = cache_service.redis.get_cache(cache_key)
            if cached_wishlist is not None:
                return cached_wishlist

            user_object_id = ObjectId(user_id)

            # Get wishlist items sorted by most recently added
            wishlist_items = list(
                self.collection.find(
                    {"user_id": user_object_id},
                    {
                        "_id": 0,
                        "book_name": 1,
                        "book_author": 1,
                        "book_genres": 1,
                        "added_at": 1,
                    },
                )
                .sort("added_at", -1)
                .skip(skip)
                .limit(limit)
            )

            # Format for consistency with other endpoints
            for item in wishlist_items:
                if isinstance(item.get("book_genres"), list):
                    item["book_genres"] = ", ".join(item["book_genres"])

            result = {
                "wishlist": wishlist_items,
                "count": len(wishlist_items),
                "total_count": self.get_wishlist_count(user_id),
            }

            # Cache for 10 minutes
            cache_service.redis.set_cache(cache_key, result, 600)

            return result

        except Exception as e:
            print(f"Error getting user wishlist: {e}")
            return {"wishlist": [], "count": 0, "total_count": 0}

    def get_wishlist_count(self, user_id):
        """Get total count of items in user's wishlist"""
        try:
            user_object_id = ObjectId(user_id)
            return self.collection.count_documents({"user_id": user_object_id})
        except Exception as e:
            print(f"Error getting wishlist count: {e}")
            return 0

    def is_in_wishlist(self, user_id, book_name):
        """Check if a book is in user's wishlist"""
        try:
            user_object_id = ObjectId(user_id)

            item = self.collection.find_one(
                {"user_id": user_object_id, "book_name": book_name}
            )

            return item is not None

        except Exception as e:
            print(f"Error checking if book is in wishlist: {e}")
            return False

    def get_wishlist_status_batch(self, user_id, book_names):
        """Check wishlist status for multiple books in a single query"""
        try:
            user_object_id = ObjectId(user_id)

            wishlist_items = list(
                self.collection.find(
                    {"user_id": user_object_id, "book_name": {"$in": book_names}},
                    {"book_name": 1, "_id": 0},
                )
            )

            # Convert to set for O(1) lookup
            wishlist_books = {item["book_name"] for item in wishlist_items}

            # Return dictionary with book_name -> in_wishlist mapping
            return {book_name: book_name in wishlist_books for book_name in book_names}

        except Exception as e:
            print(f"Error getting wishlist status batch: {e}")
            return {book_name: False for book_name in book_names}

    def clear_wishlist(self, user_id):
        """Clear all items from user's wishlist"""
        try:
            user_object_id = ObjectId(user_id)

            result = self.collection.delete_many({"user_id": user_object_id})

            if result.deleted_count >= 0:
                # Invalidate user's wishlist cache
                self._invalidate_wishlist_cache(str(user_id))

                return {
                    "success": True,
                    "message": f"Cleared {result.deleted_count} items from wishlist",
                    "cleared_count": result.deleted_count,
                }
            else:
                return {"success": False, "message": "Failed to clear wishlist"}

        except Exception as e:
            print(f"Error clearing wishlist: {e}")
            return {"success": False, "message": "Internal server error"}

    def get_wishlist_statistics(self, user_id):
        """Get statistics about user's wishlist"""
        try:
            user_object_id = ObjectId(user_id)

            # Use aggregation to get genre distribution
            pipeline = [
                {"$match": {"user_id": user_object_id}},
                {"$unwind": "$book_genres"},
                {"$group": {"_id": "$book_genres", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10},
            ]

            genre_stats = list(self.collection.aggregate(pipeline))

            # Get total count and recent additions
            total_count = self.get_wishlist_count(user_id)

            recent_additions = list(
                self.collection.find(
                    {"user_id": user_object_id},
                    {"book_name": 1, "added_at": 1, "_id": 0},
                )
                .sort("added_at", -1)
                .limit(5)
            )

            return {
                "total_count": total_count,
                "genre_distribution": [
                    {"genre": item["_id"], "count": item["count"]}
                    for item in genre_stats
                ],
                "recent_additions": recent_additions,
            }

        except Exception as e:
            print(f"Error getting wishlist statistics: {e}")
            return {"total_count": 0, "genre_distribution": [], "recent_additions": []}

    def _parse_genres(self, genres):
        """Parse genres from string to list"""
        if isinstance(genres, list):
            return [genre.strip() for genre in genres if genre.strip()]
        elif isinstance(genres, str):
            # Split by comma and clean up
            return [genre.strip() for genre in genres.split(",") if genre.strip()]
        else:
            return []

    def _invalidate_wishlist_cache(self, user_id):
        """Invalidate user's wishlist cache"""
        try:
            cache_service.redis.delete_keys_by_pattern(f"wishlist:{user_id}:*")
        except Exception as e:
            print(f"Error invalidating wishlist cache: {e}")
