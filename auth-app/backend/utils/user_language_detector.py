import logging
from collections import Counter
from typing import List, Dict, Set
from database.mongodb_manager import mongodb_manager
from bson import ObjectId

logger = logging.getLogger(__name__)


class UserLanguageDetector:
    """Detect user's preferred languages from their reading history"""

    def __init__(self):
        self.db = mongodb_manager.get_database("booksdata")
        self.users_db = mongodb_manager.get_database("user_auth_db")
        self.books_collection = self.db["book"]
        self.interactions_collection = self.users_db["user_book_interactions"]

        # Cache for user language preferences
        self._language_cache = {}

        # Default languages to always include
        self.default_languages = {"english"}

        # Minimum threshold for including a language
        self.min_language_threshold = 2  # At least 2 books in a language

    def get_user_languages(self, user_id: str, max_languages: int = 3) -> Set[str]:
        """
        Get user's preferred languages based on their profile and reading history

        Args:
            user_id: User ID
            max_languages: Maximum number of languages to return

        Returns:
            Set of language codes (e.g., {'english', 'arabic'})
        """
        try:
            # Check cache first
            cache_key = f"{user_id}_{max_languages}"
            if cache_key in self._language_cache:
                return self._language_cache[cache_key]

            # PRIORITY 1: Check user's profile language preferences
            # Try both string and ObjectId formats
            user_profile = None
            try:
                # Try as ObjectId first
                user_profile = self.users_db["users"].find_one(
                    {"_id": ObjectId(user_id)}
                )
            except:
                # If that fails, try as string
                user_profile = self.users_db["users"].find_one({"_id": user_id})

            if user_profile and "user_languages" in user_profile:
                profile_languages = user_profile["user_languages"]
                if isinstance(profile_languages, list) and profile_languages:
                    # Clean and validate languages
                    clean_languages = set()
                    for lang in profile_languages[:max_languages]:
                        if isinstance(lang, str) and lang.strip():
                            clean_languages.add(lang.lower().strip())

                    if clean_languages:
                        self._language_cache[cache_key] = clean_languages
                        return clean_languages
            # PRIORITY 2: Analyze reading history if no profile languages
            user_interactions = list(
                self.interactions_collection.find(
                    {"user_id": user_id, "action": "like"}
                )
            )

            if not user_interactions:
                # New user - return default language
                languages = self.default_languages.copy()
                self._language_cache[cache_key] = languages
                return languages

            # Get book names from interactions
            book_names = [interaction["book_name"] for interaction in user_interactions]

            # Get languages for these books
            book_languages = self._get_book_languages(book_names)

            # Count language frequency
            language_counts = Counter(book_languages)

            # Filter languages with minimum threshold
            significant_languages = {
                lang
                for lang, count in language_counts.items()
                if count >= self.min_language_threshold
            }

            # Always include English as fallback
            significant_languages.add("english")

            # Get top languages (most frequent first)
            top_languages = [
                lang
                for lang, count in language_counts.most_common(max_languages)
                if lang in significant_languages
            ]

            # Ensure we have at least English
            if not top_languages:
                top_languages = ["english"]

            # Convert to set and limit size
            languages = set(top_languages[:max_languages])

            # Cache the result
            self._language_cache[cache_key] = languages

            return languages

        except Exception as e:
            logger.error(f"Error detecting languages for user {user_id}: {e}")
            # Return default on error
            return self.default_languages.copy()

    def _get_book_languages(self, book_names: List[str]) -> List[str]:
        """Get languages for a list of book names"""
        try:
            # Query books by name and get their languages
            books = list(
                self.books_collection.find(
                    {"book_name": {"$in": book_names}}, {"book_name": 1, "book_lang": 1}
                )
            )

            # Extract languages
            languages = []
            for book in books:
                lang = book.get("book_lang", "english")
                if lang:
                    # Normalize language names
                    lang = lang.lower().strip()
                    languages.append(lang)
                else:
                    languages.append("english")  # Default fallback

            return languages

        except Exception as e:
            logger.error(f"Error getting book languages: {e}")
            return ["english"] * len(book_names)  # Fallback

    def get_language_statistics(self, user_id: str) -> Dict:
        """Get detailed language statistics for a user"""
        try:
            user_interactions = list(
                self.interactions_collection.find(
                    {"user_id": user_id, "action": "like"}
                )
            )

            if not user_interactions:
                return {
                    "languages": {},
                    "total_books": 0,
                    "message": "No reading history",
                }

            book_names = [interaction["book_name"] for interaction in user_interactions]
            book_languages = self._get_book_languages(book_names)

            language_counts = Counter(book_languages)

            return {
                "languages": dict(language_counts),
                "total_books": len(user_interactions),
                "top_language": (
                    language_counts.most_common(1)[0] if language_counts else "english"
                ),
                "language_diversity": len(language_counts),
            }

        except Exception as e:
            logger.error(f"Error getting language statistics for user {user_id}: {e}")
            return {"error": str(e)}

    def clear_cache(self, user_id: str = None):
        """Clear language cache for a user or all users"""
        if user_id:
            # Clear cache for specific user
            keys_to_remove = [
                key for key in self._language_cache.keys() if key.startswith(user_id)
            ]
            for key in keys_to_remove:
                del self._language_cache[key]
        else:
            # Clear all cache
            self._language_cache.clear()

    def debug_user_profile(self, user_id: str):
        """Debug method to check user profile data"""
        try:
            # Try both ObjectId and string formats
            user_profile_obj = None
            user_profile_str = None

            try:
                user_profile_obj = self.users_db["users"].find_one(
                    {"_id": ObjectId(user_id)}
                )
            except:
                pass

            try:
                user_profile_str = self.users_db["users"].find_one({"_id": user_id})
            except:
                pass

            return user_profile_obj or user_profile_str

        except Exception as e:
            logger.error(f"Error debugging user profile for {user_id}: {e}")
            return None

    def get_supported_languages(self) -> List[str]:
        """Get list of all supported languages in the system"""
        try:
            # Get unique languages from books collection
            languages = self.books_collection.distinct("book_lang")

            # Clean and normalize
            clean_languages = []
            for lang in languages:
                if lang and isinstance(lang, str):
                    clean_lang = lang.lower().strip()
                    if clean_lang and clean_lang != "null":
                        clean_languages.append(clean_lang)

            return sorted(list(set(clean_languages)))

        except Exception as e:
            logger.error(f"Error getting supported languages: {e}")
            return ["english"]  # Fallback


# Global instance
user_language_detector = UserLanguageDetector()
