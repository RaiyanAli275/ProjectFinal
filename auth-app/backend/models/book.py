from bson.objectid import ObjectId
import re
from database.mongodb_manager import mongodb_manager
from services.cache_service import cache_service


class Book:
    def __init__(self):
        # Use the shared MongoDB connection pool
        self.db = mongodb_manager.get_database("booksdata")
        self.collection = self.db["book"]

    def search_books_by_name(self, search_term, page_size=5, page=1):
        """Search books by name (case-insensitive, partial matching) with pagination"""
        try:
            if not search_term or len(search_term.strip()) == 0:
                return [], 0

            # Create case-insensitive regex pattern for matching start of book name
            pattern = re.compile(f"^{re.escape(search_term.strip())}", re.IGNORECASE)

            # Search query to match books that start with the search term
            query = {"name": {"$regex": pattern}}

            # Project only the fields we need
            projection = {
                "name": 1,
                "author": 1,
                "genres": 1,
                "_id": 0,  # Exclude _id for cleaner response
            }

            # Get total count for pagination
            total_count = self.collection.count_documents(query)

            # Calculate skip value for pagination
            skip = (page - 1) * page_size

            # Execute search with pagination, sorted by num_ratings (most rated first)
            results = list(
                self.collection.find(query, projection)
                .sort("num_ratings", -1)
                .skip(skip)
                .limit(page_size)
            )

            # Format authors as string if it's a list
            for book in results:
                if isinstance(book.get("author"), list):
                    book["author"] = ", ".join(book["author"])

                # Format genres as string if it's a list
                if isinstance(book.get("genres"), list):
                    book["genres"] = ", ".join(book["genres"])

                # Handle missing rating data
                if "star_rating" not in book or book["star_rating"] is None:
                    book["star_rating"] = None
                if "num_ratings" not in book or book["num_ratings"] is None:
                    book["num_ratings"] = 0

            return results, total_count

        except Exception as e:
            print(f"Error searching books: {e}")
            return []

    def get_book_language(self, book_name):
        """Get the language of a book by its name"""
        try:
            # Find the book by name (case-insensitive)
            pattern = re.compile(f"^{re.escape(book_name)}$", re.IGNORECASE)
            book = self.collection.find_one(
                {"name": {"$regex": pattern}}, {"language_of_book": 1, "_id": 0}
            )

            if book:
                # Return the language or None if not found
                return book.get("language_of_book")
            return None

        except Exception as e:
            print(f"Error getting book language: {e}")
            return None

    def _get_popular_books(self, limit=10):
        """Get popular books as fallback when no user preferences exist"""
        try:
            projection = {
                "name": 1,
                "author": 1,
                "genres": 1,
                "star_rating": 1,
                "num_ratings": 1,
                "_id": 0,
            }

            books = list(
                self.collection.find(
                    {"num_ratings": {"$exists": True, "$ne": None, "$gt": 100}},
                    projection,
                )
                .sort("num_ratings", -1)
                .limit(limit)
            )

            # Format for consistency
            for book in books:
                if isinstance(book.get("author"), list):
                    book["author"] = ", ".join(book["author"])
                if isinstance(book.get("genres"), list):
                    book["genres"] = ", ".join(book["genres"])
                book["recommendation_score"] = 50  # Default score for popular books
                book["algorithm"] = "popular"
                book["confidence"] = 0.5

            return books

        except Exception as e:
            print(f"Error getting popular books: {e}")
            return []

    def get_popular_books_by_score(self, limit=50):  # INCREASED DEFAULT LIMIT
        """Get popular books ranked by num_ratings * star_rating with permanent caching"""
        try:
            # Check cache first
            cached_books = cache_service.get_cached_popular_books(limit)
            if cached_books is not None:
                return cached_books

            # Use MongoDB aggregation to calculate popularity score
            # NO TIMEOUT - Will search until results found
            pipeline = [
                {
                    "$match": {
                        "num_ratings": {"$exists": True, "$ne": None, "$gt": 0},
                        "star_rating": {"$exists": True, "$ne": None, "$gt": 0},
                    }
                },
                {
                    "$addFields": {
                        "popularity_score": {
                            "$multiply": ["$num_ratings", "$star_rating"]
                        }
                    }
                },
                {"$sort": {"popularity_score": -1}},
                {"$limit": limit},
                {
                    "$project": {
                        "name": 1,
                        "author": 1,
                        "genres": 1,
                        "star_rating": 1,
                        "num_ratings": 1,
                        "popularity_score": 1,
                        "_id": 0,
                    }
                },
            ]

            books = list(self.collection.aggregate(pipeline))

            # Format for consistency
            for book in books:
                if isinstance(book.get("author"), list):
                    book["author"] = ", ".join(book["author"])
                if isinstance(book.get("genres"), list):
                    book["genres"] = ", ".join(book["genres"])

                # Round popularity score for cleaner display
                book["popularity_score"] = round(book.get("popularity_score", 0), 2)

            # Cache the results FOREVER (no TTL)
            cache_service.cache_popular_books(books, limit)

            return books

        except Exception as e:
            print(f"Error getting popular books by score: {e}")
            return []

    def get_popular_books_by_score_with_language_filter(
        self, user_id, limit=50, force_refresh=False
    ):
        """
        HYBRID OPTIMIZED: Get popular books with both pre-computed and runtime calculation fallback
        """
        try:
            # Step 1: Check cache first (unless force_refresh is True)
            cache_key = f"popular_lang:{user_id}:{limit}"
            if not force_refresh:
                cached_books = cache_service.redis.get_cache(cache_key)
                if cached_books is not None:
                    return cached_books

            # Step 2: Get user's preferred languages
            from models.user import User

            user_model = User()
            user_languages = user_model.get_user_languages(user_id)

            # Step 3: Try optimized query first (with pre-computed scores)
            books = self._get_popular_books_optimized(user_languages, limit)

            # Step 4: Fallback to runtime calculation if no pre-computed scores
            if not books:
                books = self._get_popular_books_runtime(user_languages, limit)

            # Step 5: Format results for consistency
            for book in books:
                if isinstance(book.get("author"), list):
                    book["author"] = ", ".join(book["author"])
                if isinstance(book.get("genres"), list):
                    book["genres"] = ", ".join(book["genres"])

                # Round popularity score for cleaner display
                book["popularity_score"] = round(book.get("popularity_score", 0), 2)

            # Step 6: Cache results for 30 minutes
            if books:
                cache_service.redis.set_cache(cache_key, books, 1800)

            return books

        except Exception as e:
            print(f"Error getting language-filtered popular books: {e}")
            # Final fallback to regular popular books
            return self.get_popular_books_by_score(limit)

    def _get_popular_books_optimized(self, user_languages, limit):
        """Get popular books using pre-computed popularity scores (FAST)"""
        try:
            # Build optimized query criteria
            match_criteria = {"popularity_score": {"$exists": True, "$gt": 0}}

            # Use $in instead of $regex for language filtering
            if user_languages:
                normalized_languages = [lang.lower() for lang in user_languages]
                match_criteria["language_of_book"] = {"$in": normalized_languages}

            # Optimized aggregation pipeline
            pipeline = [
                {"$match": match_criteria},
                {
                    # Direct sort on pre-computed indexed field
                    "$sort": {"popularity_score": -1}
                },
                {"$limit": limit},
                {
                    "$project": {
                        "name": 1,
                        "author": 1,
                        "genres": 1,
                        "star_rating": 1,
                        "num_ratings": 1,
                        "popularity_score": 1,
                        "language_of_book": 1,
                        "_id": 0,
                    }
                },
            ]

            return list(self.collection.aggregate(pipeline))

        except Exception as e:
            print(f"Error in optimized query: {e}")
            return []

    def _get_popular_books_runtime(self, user_languages, limit):
        """Get popular books using runtime calculation (SLOWER but works without pre-computed scores)"""
        try:
            # Base match criteria for books with ratings
            match_criteria = {
                "num_ratings": {"$exists": True, "$ne": None, "$gt": 0},
                "star_rating": {"$exists": True, "$ne": None, "$gt": 0},
            }

            # Use $in instead of $regex for language filtering
            if user_languages:
                normalized_languages = [lang.lower() for lang in user_languages]
                match_criteria["language_of_book"] = {"$in": normalized_languages}

            # Runtime calculation pipeline
            pipeline = [
                {"$match": match_criteria},
                {
                    "$addFields": {
                        "popularity_score": {
                            "$multiply": ["$num_ratings", "$star_rating"]
                        }
                    }
                },
                {"$sort": {"popularity_score": -1}},
                {"$limit": limit},
                {
                    "$project": {
                        "name": 1,
                        "author": 1,
                        "genres": 1,
                        "star_rating": 1,
                        "num_ratings": 1,
                        "popularity_score": 1,
                        "language_of_book": 1,
                        "_id": 0,
                    }
                },
            ]

            return list(self.collection.aggregate(pipeline))

        except Exception as e:
            print(f"Error in runtime calculation: {e}")
            return []

    def get_popular_books_by_user_top_genres(self, user_id, limit=5):
        """
        Get popular books in user's top 2 most liked genres - OPTIMIZED with aggressive caching
        Returns two separate lists for the two dashboards
        """
        try:
            # CACHE CHECK: Check if we have cached results for this user
            cache_key = f"user_genre_dashboard:{user_id}:{limit}"
            cached_result = cache_service.redis.get_cache(cache_key)
            if cached_result is not None:
                return cached_result

            # Import here to avoid circular imports
            from models.user_book_interaction import UserBookInteraction

            interaction_model = UserBookInteraction()

            # Get user's top 2 most liked genres
            top_genres = interaction_model.get_user_liked_genres(user_id, limit=2)

            if len(top_genres) < 2:
                result = {
                    "genre1": {"genre": None, "books": [], "like_count": 0},
                    "genre2": {"genre": None, "books": [], "like_count": 0},
                    "message": "Need to like books from at least 2 different genres",
                    "has_enough_data": False,
                }
                # Cache negative result for shorter time to allow quick retry
                cache_service.redis.set_cache(cache_key, result, 300)  # 5 minutes
                return result

            # Get list of books user has already interacted with to exclude them
            user_interacted_books = set(
                interaction_model.get_user_interacted_book_names(user_id)
            )

            genre1 = top_genres[0]["genre"]
            genre2 = top_genres[1]["genre"]

            # PARALLEL PROCESSING: Get popular books for both genres (excluding user interactions)
            # This is still sequential but optimized with caching
            try:
                genre1_books = self._get_popular_books_by_genre(
                    genre1, limit, exclude_books=user_interacted_books
                )
            except Exception as e:
                print(f"Error getting books for genre1 '{genre1}': {e}")
                genre1_books = []

            try:
                genre2_books = self._get_popular_books_by_genre(
                    genre2, limit, exclude_books=user_interacted_books
                )
            except Exception as e:
                print(f"Error getting books for genre2 '{genre2}': {e}")
                genre2_books = []

            result = {
                "genre1": {
                    "genre": genre1,
                    "books": genre1_books,
                    "like_count": top_genres[0]["count"],
                },
                "genre2": {
                    "genre": genre2,
                    "books": genre2_books,
                    "like_count": top_genres[1]["count"],
                },
                "has_enough_data": True,
            }

            # CACHE SUCCESS: Cache successful results for 15 minutes
            cache_service.redis.set_cache(cache_key, result, 900)  # 15 minutes

            return result

        except Exception as e:
            print(f"Error getting popular books by user top genres: {e}")
            # FALLBACK: Return structured error response
            fallback_result = {
                "genre1": {"genre": None, "books": [], "like_count": 0},
                "genre2": {"genre": None, "books": [], "like_count": 0},
                "error": str(e),
                "has_enough_data": False,
            }
            return fallback_result

    def _get_popular_books_by_genre(self, genre, limit=20, exclude_books=None):
        """
        Get popular books for a specific genre - OPTIMIZED with caching
        Now excludes books that users have already interacted with
        """
        try:
            # If we have books to exclude, we can't use the general cache
            # Create a unique cache key that includes user interactions
            if exclude_books:
                # Create a hash of excluded books for cache key uniqueness
                import hashlib

                exclude_hash = hashlib.md5(
                    ",".join(sorted(exclude_books)).encode()
                ).hexdigest()[:8]
                cache_key = f"genre_popular:{genre}:{limit}:exclude_{exclude_hash}"
            else:
                cache_key = f"genre_popular:{genre}:{limit}"

            # CACHE CHECK: Check if we have cached results for this genre
            cached_result = cache_service.redis.get_cache(cache_key)
            if cached_result is not None:
                return cached_result

            # Use case-insensitive regex for genre matching
            genre_pattern = re.compile(genre, re.IGNORECASE)

            # Build optimized query with pre-computed popularity scores
            match_criteria = {
                "genres": {"$regex": genre_pattern},
                "popularity_score": {"$exists": True, "$gt": 0},
            }

            # Add exclusion criteria if provided
            if exclude_books:
                match_criteria["name"] = {"$nin": list(exclude_books)}

            # Optimized aggregation pipeline
            pipeline = [
                {"$match": match_criteria},
                {"$sort": {"popularity_score": -1}},
                {"$limit": limit},
                {
                    "$project": {
                        "name": 1,
                        "author": 1,
                        "genres": 1,
                        "star_rating": 1,
                        "num_ratings": 1,
                        "popularity_score": 1,
                        "_id": 0,
                    }
                },
            ]

            books = list(self.collection.aggregate(pipeline))

            # Format for consistency
            for book in books:
                if isinstance(book.get("author"), list):
                    book["author"] = ", ".join(book["author"])
                if isinstance(book.get("genres"), list):
                    book["genres"] = ", ".join(book["genres"])

                # Round popularity score for cleaner display
                book["popularity_score"] = round(book.get("popularity_score", 0), 2)

            # CACHE SUCCESS: Cache results for 30 minutes (shorter cache for user-specific results)
            cache_time = 900 if exclude_books else 1800  # 15 min vs 30 min
            cache_service.redis.set_cache(cache_key, books, cache_time)

            return books

        except Exception as e:
            print(f"Error getting popular books for genre '{genre}': {e}")
            return []

    def get_book_url(self, book_name):
        """Get the URL of a book by its name from the database"""
        try:
            # Find the book by name (case-insensitive)
            pattern = re.compile(f"^{re.escape(book_name)}$", re.IGNORECASE)
            book = self.collection.find_one(
                {"name": {"$regex": pattern}},
                {
                    "url": 1,
                    "URL": 1,
                    "link": 1,
                    "Link": 1,
                    "_id": 0,
                },  # Check multiple possible field names
            )

            if book:
                # Try different possible field names for the URL
                url_fields = ["url", "URL", "link", "Link"]
                for field in url_fields:
                    if field in book and book[field]:
                        return book[field]

            return None

        except Exception as e:
            print(f"Error getting book URL: {e}")
            return None
