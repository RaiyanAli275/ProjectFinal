from bson.objectid import ObjectId
from datetime import datetime
import re
from database.mongodb_manager import mongodb_manager
from services.cache_service import cache_service


class UserBookInteraction:
    def __init__(self):
        # Use the shared MongoDB connection pool
        self.db = mongodb_manager.get_user_auth_database()
        self.interactions_collection = self.db["user_book_interactions"]
        self.liked_genres_collection = self.db["user_liked_genres"]
        self.disliked_genres_collection = self.db["user_disliked_genres"]

        # Create indexes for better performance
        try:
            self.interactions_collection.create_index(
                [("user_id", 1), ("book_name", 1)]
            )
            self.liked_genres_collection.create_index([("user_id", 1), ("genre", 1)])
            self.disliked_genres_collection.create_index([("user_id", 1), ("genre", 1)])
        except:
            # Indexes might already exist
            pass

    def like_book(self, user_id, book_name, book_author, book_genres):
        """Like a book and update genre preferences"""
        try:
            user_object_id = ObjectId(user_id)

            # Check if user already has an interaction with this book
            existing_interaction = self.interactions_collection.find_one(
                {"user_id": user_object_id, "book_name": book_name}
            )

            # Parse genres from string to list if needed
            genres_list = self._parse_genres(book_genres)

            # Get book language and update user languages
            self._update_user_language(str(user_id), book_name)

            if existing_interaction:
                # Update existing interaction
                old_action = existing_interaction["action"]
                if old_action == "like":
                    return True
                # Update the interaction
                self.interactions_collection.update_one(
                    {"user_id": user_object_id, "book_name": book_name},
                    {
                        "$set": {
                            "action": "like",
                            "timestamp": datetime.utcnow(),
                            "book_genres": genres_list,
                        }
                    },
                )

                # If previous action was dislike, remove from disliked genres
                if old_action == "dislike":
                    self._remove_genre_preferences(
                        user_object_id, genres_list, "dislike"
                    )
                    self.remove_author_preferences(
                        user_id, book_author, "dislike", book_name
                    )

            else:
                # Create new interaction
                self.interactions_collection.insert_one(
                    {
                        "user_id": user_object_id,
                        "book_name": book_name,
                        "book_author": book_author,
                        "action": "like",
                        "timestamp": datetime.utcnow(),
                        "book_genres": genres_list,
                    }
                )

                # Add to liked genres
                self._add_genre_preferences(user_object_id, genres_list, "like")

            # Update author affinity first
            author_ranking_changed = self._update_author_affinity(
                str(user_id), book_author, "like", book_name
            )

            # Invalidate user's recommendation cache but keep author-based cache for better performance
            cache_service.invalidate_user_recommendations(str(user_id))

            # Only invalidate author-based cache if the ranking significantly changed
            if author_ranking_changed:
                cache_service.redis.delete_keys_by_pattern(
                    f"best_from_author:user:{user_id}:*"
                )
            # Increment global interaction counter
            self._increment_interaction_counter()

            return True

        except Exception as e:
            print(f"Error liking book: {e}")
            return False

    def dislike_book(self, user_id, book_name, book_author, book_genres):
        """Dislike a book and update genre preferences"""
        try:
            user_object_id = ObjectId(user_id)

            # Check if user already has an interaction with this book
            existing_interaction = self.interactions_collection.find_one(
                {"user_id": user_object_id, "book_name": book_name}
            )

            # Parse genres from string to list if needed
            genres_list = self._parse_genres(book_genres)

            # Get book language and update user languages
            self._update_user_language(str(user_id), book_name)

            if existing_interaction:
                # Update existing interaction
                old_action = existing_interaction["action"]
                if old_action == "dislike":
                    return True

                # Update the interaction
                self.interactions_collection.update_one(
                    {"user_id": user_object_id, "book_name": book_name},
                    {
                        "$set": {
                            "action": "dislike",
                            "timestamp": datetime.utcnow(),
                            "book_genres": genres_list,
                        }
                    },
                )

                # If previous action was like, remove from liked genres
                if old_action == "like":
                    self._remove_genre_preferences(user_object_id, genres_list, "like")
                    self.remove_author_preferences(
                        user_id, book_author, "like", book_name
                    )

            else:
                # Create new interaction
                self.interactions_collection.insert_one(
                    {
                        "user_id": user_object_id,
                        "book_name": book_name,
                        "book_author": book_author[0],
                        "action": "dislike",
                        "timestamp": datetime.utcnow(),
                        "book_genres": genres_list,
                    }
                )

                # Add to disliked genres
                self._add_genre_preferences(user_object_id, genres_list, "dislike")

            # Update author affinity first
            author_ranking_changed = self._update_author_affinity(
                str(user_id), book_author[0], "dislike", book_name
            )

            # Invalidate user's recommendation cache but keep author-based cache for better performance
            cache_service.invalidate_user_recommendations(str(user_id))

            # Only invalidate author-based cache if the ranking significantly changed
            if author_ranking_changed:
                cache_service.redis.delete_keys_by_pattern(
                    f"best_from_author:user:{user_id}:*"
                )

            # Increment global interaction counter
            self._increment_interaction_counter()

            return True

        except Exception as e:
            print(f"Error disliking book: {e}")
            return False

    def get_user_interaction(self, user_id, book_name):
        """Get user's interaction with a specific book"""
        try:
            user_object_id = ObjectId(user_id)
            interaction = self.interactions_collection.find_one(
                {"user_id": user_object_id, "book_name": book_name}
            )

            if interaction:
                return interaction["action"]
            return None

        except Exception as e:
            print(f"Error getting user interaction: {e}")
            return None

    def get_book_stats(self, book_name):
        """Get like/dislike counts for a book"""
        try:
            likes = self.interactions_collection.count_documents(
                {"book_name": book_name, "action": "like"}
            )

            dislikes = self.interactions_collection.count_documents(
                {"book_name": book_name, "action": "dislike"}
            )

            return {"likes": likes, "dislikes": dislikes}

        except Exception as e:
            print(f"Error getting book stats: {e}")
            return {"likes": 0, "dislikes": 0}

    def get_user_liked_genres(self, user_id, limit=10):
        """Get user's most liked genres"""
        try:
            user_object_id = ObjectId(user_id)
            genres = list(
                self.liked_genres_collection.find(
                    {"user_id": user_object_id}, {"_id": 0, "genre": 1, "count": 1}
                )
                .sort("count", -1)
                .limit(limit)
            )

            return genres

        except Exception as e:
            print(f"Error getting liked genres: {e}")
            return []

    def get_user_disliked_genres(self, user_id, limit=10):
        """Get user's most disliked genres"""
        try:
            user_object_id = ObjectId(user_id)
            genres = list(
                self.disliked_genres_collection.find(
                    {"user_id": user_object_id}, {"_id": 0, "genre": 1, "count": 1}
                )
                .sort("count", -1)
                .limit(limit)
            )

            return genres

        except Exception as e:
            print(f"Error getting disliked genres: {e}")
            return []

    def get_user_interactions(self, user_id, action=None, limit=50):
        """Get user's book interactions"""
        try:
            user_object_id = ObjectId(user_id)
            query = {"user_id": user_object_id}

            if action:
                query["action"] = action

            interactions = list(
                self.interactions_collection.find(
                    query,
                    {
                        "_id": 0,
                        "book_name": 1,
                        "book_author": 1,
                        "action": 1,
                        "timestamp": 1,
                        "book_genres": 1,
                    },
                )
                .sort("timestamp", -1)
                .limit(limit)
            )

            return interactions

        except Exception as e:
            print(f"Error getting user interactions: {e}")
            return []

    def _parse_genres(self, genres):
        """Parse genres from string to list"""
        if isinstance(genres, list):
            return [genre.strip() for genre in genres if genre.strip()]
        elif isinstance(genres, str):
            # Split by comma and clean up
            return [genre.strip() for genre in genres.split(",") if genre.strip()]
        else:
            return []

    def _add_genre_preferences(self, user_id, genres, action):
        """Add or increment genre preferences"""
        collection = (
            self.liked_genres_collection
            if action == "like"
            else self.disliked_genres_collection
        )

        for genre in genres:
            if not genre:
                continue

            # Check if genre preference exists
            existing = collection.find_one({"user_id": user_id, "genre": genre})

            if existing:
                # Increment count
                collection.update_one(
                    {"user_id": user_id, "genre": genre},
                    {"$inc": {"count": 1}, "$set": {"last_updated": datetime.utcnow()}},
                )
            else:
                # Create new preference
                collection.insert_one(
                    {
                        "user_id": user_id,
                        "genre": genre,
                        "count": 1,
                        "last_updated": datetime.utcnow(),
                    }
                )

    def _remove_genre_preferences(self, user_id, genres, action):
        """Remove or decrement genre preferences"""
        collection = (
            self.liked_genres_collection
            if action == "like"
            else self.disliked_genres_collection
        )

        for genre in genres:
            if not genre:
                continue

            # Check if genre preference exists
            existing = collection.find_one({"user_id": user_id, "genre": genre})

            if existing:
                if existing["count"] <= 1:
                    # Remove the preference if count would be 0
                    collection.delete_one({"user_id": user_id, "genre": genre})
                else:
                    # Decrement count
                    collection.update_one(
                        {"user_id": user_id, "genre": genre},
                        {
                            "$inc": {"count": -1},
                            "$set": {"last_updated": datetime.utcnow()},
                        },
                    )

    # Rating functionality removed - only like/dislike supported

    def _update_user_language(self, user_id, book_name):
        """Update user's language list based on book interaction"""
        try:
            # Import here to avoid circular imports
            from models.book import Book
            from models.user import User

            # Get book language
            book_model = Book()
            book_language = book_model.get_book_language(book_name)

            if book_language:
                # Update user's languages
                user_model = User()
                user_model.add_user_language(user_id, book_language)

        except Exception as e:
            print(f"Error updating user language: {e}")

    def remove_author_preferences(self, user_id, book_author, action, book_name):
        """Remove all preferences for a specific author"""
        try:
            # Import here to avoid circular imports
            from models.user_sorted_author_preferences import (
                user_sorted_author_preferences,
            )

            # Remove from sorted author preferences
            user_sorted_author_preferences.remove_author_preference(
                user_id, book_author, action, book_name
            )

            return True

        except Exception as e:
            print(f"Error removing author preferences: {e}")
            return False

    def get_user_interaction_count(self, user_id):
        """Get total number of interactions for a user"""
        try:
            user_object_id = ObjectId(user_id)

            return self.interactions_collection.count_documents(
                {"user_id": user_object_id}
            )

        except Exception as e:
            print(f"Error getting user interaction count: {e}")
            return 0

    def get_user_interaction_count_by_action(self, user_id, action):
        """Get count of interactions for a user by specific action"""
        try:
            user_object_id = ObjectId(user_id)

            return self.interactions_collection.count_documents(
                {"user_id": user_object_id, "action": action}
            )

        except Exception as e:
            print(f"Error getting user interaction count by action: {e}")
            return 0

    def get_user_interactions_batch(self, user_id, book_names):
        """Get user interactions for multiple books in a single query"""
        try:
            user_object_id = ObjectId(user_id)

            interactions = list(
                self.interactions_collection.find(
                    {"user_id": user_object_id, "book_name": {"$in": book_names}},
                    {"book_name": 1, "action": 1, "_id": 0},
                )
            )

            # Convert to dictionary for O(1) lookup
            return {item["book_name"]: item["action"] for item in interactions}

        except Exception as e:
            print(f"Error getting user interactions batch: {e}")
            return {}

    def get_book_stats_batch(self, book_names):
        """Get like/dislike stats for multiple books in a single query"""
        try:
            # Use aggregation to get counts for all books at once
            pipeline = [
                {
                    "$match": {
                        "book_name": {"$in": book_names},
                        "action": {"$in": ["like", "dislike"]},
                    }
                },
                {
                    "$group": {
                        "_id": {"book_name": "$book_name", "action": "$action"},
                        "count": {"$sum": 1},
                    }
                },
            ]

            results = list(self.interactions_collection.aggregate(pipeline))

            # Initialize stats for all books
            stats = {book_name: {"likes": 0, "dislikes": 0} for book_name in book_names}

            # Fill in actual counts
            for result in results:
                book_name = result["_id"]["book_name"]
                action = result["_id"]["action"]
                count = result["count"]

                if book_name in stats:
                    stats[book_name][f"{action}s"] = count

            return stats

        except Exception as e:
            print(f"Error getting book stats batch: {e}")
            return {book_name: {"likes": 0, "dislikes": 0} for book_name in book_names}

    def get_user_interacted_book_names(self, user_id):
        """Get list of all book names the user has interacted with (for filtering out from popular books)"""
        try:
            user_object_id = ObjectId(user_id)

            # Use projection to only get book names for optimal performance
            interactions = list(
                self.interactions_collection.find(
                    {"user_id": user_object_id}, {"book_name": 1, "_id": 0}
                )
            )

            # Extract just the book names as a list
            book_names = [interaction["book_name"] for interaction in interactions]

            return book_names

        except Exception as e:
            print(f"Error getting user interacted book names: {e}")
            return []

    def _update_author_affinity(self, user_id, book_author, action, book_name):
        """Update user's author preferences using the new optimized sorted system"""
        try:
            # Import here to avoid circular imports
            from models.user_sorted_author_preferences import (
                user_sorted_author_preferences,
            )

            # Get current top author before update
            current_top_author = (
                user_sorted_author_preferences.get_most_preferred_author(user_id)
            )
            current_top_author_name = (
                current_top_author["author_name"] if current_top_author else None
            )

            # Update the preference
            user_sorted_author_preferences.update_author_preference(
                user_id, book_author, action, book_name
            )

            # Get new top author after update
            new_top_author = user_sorted_author_preferences.get_most_preferred_author(
                user_id
            )
            new_top_author_name = (
                new_top_author["author_name"] if new_top_author else None
            )

            # Return True if the top author changed
            return current_top_author_name != new_top_author_name

        except Exception as e:
            print(f"Warning: Could not update author preferences: {e}")
            return False  # Conservative: assume ranking changed to invalidate cache if there's an error

    def _increment_interaction_counter(self):
        """Increment the global interaction counter and trigger training if needed"""
        try:
            from models.interaction_counter import interaction_counter

            training_triggered = interaction_counter.increment_counter()
        except Exception as e:
            print(f"Warning: Could not increment interaction counter: {e}")

    def remove_interaction(self, user_id, book_name, book_author, book_genres, action):
        """Remove a user's interaction with a book"""
        try:
            user_object_id = ObjectId(user_id)

            # Remove the interaction
            result = self.interactions_collection.delete_one(
                {"user_id": user_object_id, "book_name": book_name}
            )

            self.remove_author_preferences(user_id, book_author, action, book_name)

            self._remove_genre_preferences(user_object_id, book_genres, action)

            if result.deleted_count > 0:
                # Successfully removed interaction
                return True
            else:
                return False

        except Exception as e:
            print(f"Error removing interaction: {e}")
            return False
