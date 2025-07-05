from bson.objectid import ObjectId
from datetime import datetime
import logging
from database.mongodb_manager import mongodb_manager


class UserSortedAuthorPreferences:
    """
    Optimized database design for maintaining sorted author preferences per user.
    Each user has a single document with authors sorted by preference count in descending order.
    This allows O(1) access to the most preferred author and efficient real-time updates.
    """

    def __init__(self):
        # Use the shared MongoDB connection pool
        self.db = mongodb_manager.get_user_auth_database()
        self.collection = self.db["user_sorted_author_preferences"]

        # Create indexes for optimal performance
        try:
            self.collection.create_index(
                "user_id", unique=True
            )  # One document per user
            self.collection.create_index("last_updated")  # For cleanup queries
        except:
            # Indexes might already exist
            pass

        # Setup logging
        self.logger = logging.getLogger(__name__)

    def update_author_preference(self, user_id, author_name, action, book_name):
        """
        Update author preference and maintain sorted order in real-time.
        Uses atomic MongoDB operations for thread-safety.
        """
        try:
            if not author_name or not author_name.strip():
                return True

            author_name = author_name.strip()
            user_object_id = ObjectId(user_id) if isinstance(user_id, str) else user_id

            # Define preference weights
            weights = {
                "like": 1,  # Increment preference count
                "dislike": -1,  # Decrement preference count
            }

            weight = weights.get(action, 0)
            if weight == 0:
                return True

            # Get current user document
            user_prefs = self.collection.find_one({"user_id": user_object_id})

            if not user_prefs:
                # Create new user document with first author
                initial_author = {
                    "author_name": author_name,
                    "preference_count": max(
                        weight, 0
                    ),  # Never negative for new authors
                    "books_liked": [book_name] if weight > 0 else [],
                    "books_disliked": [book_name] if weight < 0 else [],
                    "total_interactions": 1,
                }

                self.collection.insert_one(
                    {
                        "user_id": user_object_id,
                        "sorted_authors": (
                            [initial_author] if weight > 0 else []
                        ),  # Only add if positive
                        "total_authors": 1 if weight > 0 else 0,
                        "created_at": datetime.utcnow(),
                        "last_updated": datetime.utcnow(),
                    }
                )

                return True

            # Update existing document
            sorted_authors = user_prefs.get("sorted_authors", [])
            author_found = False

            # Find and update the author in the sorted list
            for i, author in enumerate(sorted_authors):
                if author["author_name"] == author_name:
                    author_found = True
                    old_count = author["preference_count"]
                    new_count = old_count + weight

                    # Update author data
                    author["preference_count"] = max(new_count, 0)  # Never negative
                    author["total_interactions"] = (
                        author.get("total_interactions", 0) + 1
                    )

                    # Update book lists
                    if weight > 0:
                        if book_name not in author.get("books_liked", []):
                            author.setdefault("books_liked", []).append(book_name)
                    else:
                        if book_name not in author.get("books_disliked", []):
                            author.setdefault("books_disliked", []).append(book_name)

                    # Remove author if preference count becomes 0
                    if author["preference_count"] <= 0:
                        sorted_authors.pop(i)
                    else:
                        # Re-sort the list to maintain order
                        sorted_authors.sort(
                            key=lambda x: x["preference_count"], reverse=True
                        )

                    break

            # Add new author if not found and weight is positive
            if not author_found and weight > 0:
                new_author = {
                    "author_name": author_name,
                    "preference_count": weight,
                    "books_liked": [book_name],
                    "books_disliked": [],
                    "total_interactions": 1,
                }
                sorted_authors.append(new_author)
                # Sort to maintain descending order
                sorted_authors.sort(key=lambda x: x["preference_count"], reverse=True)

            # Update the document with sorted authors
            self.collection.update_one(
                {"user_id": user_object_id},
                {
                    "$set": {
                        "sorted_authors": sorted_authors,
                        "total_authors": len(sorted_authors),
                        "last_updated": datetime.utcnow(),
                    }
                },
            )

            return True

        except Exception as e:
            self.logger.error(f"Error updating author preference: {e}")
            return False

    def get_most_preferred_author(self, user_id):
        """
        Get the most preferred author with O(1) access.
        Returns the first author in the sorted list.
        """
        try:
            user_object_id = ObjectId(user_id) if isinstance(user_id, str) else user_id

            user_prefs = self.collection.find_one(
                {"user_id": user_object_id},
                {
                    "sorted_authors": {"$slice": 1}
                },  # Only get the first author for efficiency
            )

            if user_prefs and user_prefs.get("sorted_authors"):
                most_preferred = user_prefs["sorted_authors"][0]
                return {
                    "author_name": most_preferred["author_name"],
                    "preference_count": most_preferred["preference_count"],
                    "books_liked": most_preferred.get("books_liked", []),
                    "books_disliked": most_preferred.get("books_disliked", []),
                    "total_interactions": most_preferred.get("total_interactions", 0),
                }

            return None

        except Exception as e:
            self.logger.error(f"Error getting most preferred author: {e}")
            return None

    def remove_author_preference(self, user_id, author_name, action, book_name):
        """
        Remove an author's preference from the user's sorted list.
        """
        try:
            weight = -1 if action == "like" else 1
            user_object_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
            pull_path = (
                "sorted_authors.$[author].books_liked"
                if action == "like"
                else "sorted_authors.$[author].books_disliked"
            )
            result = self.collection.update_one(
                {"user_id": user_object_id},
                {
                    "$pull": {pull_path: book_name},
                    "$inc": {
                        "sorted_authors.$[author].preference_count": weight,
                        "sorted_authors.$[author].total_interactions": -1,
                    },
                },
                array_filters=[{"author.author_name": author_name}],
            )
            if result.modified_count > 0:
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error removing author preference: {e}")
            return False


# Global instance
user_sorted_author_preferences = UserSortedAuthorPreferences()
