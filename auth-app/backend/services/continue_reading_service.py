from models.book_series import BookSeries
from models.user_book_interaction import UserBookInteraction
from services.llm_service import get_llm_service
from services.cache_service import cache_service
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ContinueReadingService:
    def __init__(self):
        self.book_series = BookSeries()
        self.user_interactions = UserBookInteraction()
        self.llm_service = None  # Initialize lazily

    def _get_llm_service(self):
        """Get LLM service instance (lazy loading)"""
        if self.llm_service is None:
            self.llm_service = get_llm_service()
        return self.llm_service

    def get_user_recommendations(self, user_id, limit=3):
        """
        Get continue reading recommendations for user

        Returns:
            {
                'recommendations': [...],
                'count': int,
                'from_cache': bool,
                'processing_time': float,
                'message': str (optional)
            }
        """
        import time

        start_time = time.time()

        try:

            # AGGRESSIVE CACHING: Check Redis cache first (2 hour TTL)
            cache_key = f"continue_reading:user:{user_id}"
            step_start = time.time()
            cached_result = cache_service.redis.get_cache(cache_key)

            if cached_result:
                cached_result["from_cache"] = True
                cached_result["processing_time"] = time.time() - start_time
                return cached_result

            # TIMING: Get user's liked books
            step_start = time.time()
            liked_books = self.user_interactions.get_user_interactions(
                user_id,
                action="like",
                limit=1000,  # Get up to 1000 liked books (effectively all)
            )

            if not liked_books:
                return {
                    "recommendations": [],
                    "count": 0,
                    "message": "Like some books to see continue reading recommendations!",
                    "suggestion": "Start by liking books that interest you to discover series recommendations.",
                    "from_cache": False,
                    "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                }

            # Sort books by popularity (prioritize well-known series first)
            def get_popularity_score(book):
                book_name = book.get("book_name", "").lower()

                # High priority for popular series
                high_priority_keywords = [
                    "harry potter",
                    "hunger games",
                    "maze runner",
                    "twilight",
                    "percy jackson",
                    "divergent",
                    "lord of the rings",
                    "game of thrones",
                ]

                for keyword in high_priority_keywords:
                    if keyword in book_name:
                        return 10.0  # High priority

                # Medium priority for other known series
                medium_priority_keywords = [
                    "chronicles of narnia",
                    "fifty shades",
                    "outlander",
                    "vampire diaries",
                    "mortal instruments",
                    "throne of glass",
                    "shadowhunters",
                ]

                for keyword in medium_priority_keywords:
                    if keyword in book_name:
                        return 5.0  # Medium priority

                # Try numeric popularity scores
                popularity = book.get("popularity_score", 0)
                if popularity > 0:
                    return popularity

                # Fallback: use rating indicators
                rating_avg = book.get("rating_avg", 0)
                rating_count = book.get("rating_count", 0)
                if rating_avg > 0 and rating_count > 0:
                    return rating_avg * (rating_count / 100)

                return 0.0

            liked_books_sorted = sorted(
                liked_books, key=get_popularity_score, reverse=True
            )

            # Log top 5 most popular books being processed first
            top_books = liked_books_sorted[:5]
            for i, book in enumerate(top_books, 1):
                popularity = get_popularity_score(book)
                book_name = book["book_name"]

            all_recommendations = []
            processed_books = []

            # OPTIMIZATION: Only process top 20 most popular books for speed
            # (instead of ALL books which could be hundreds)
            top_books_to_process = liked_books_sorted[:20]

            step_start = time.time()
            llm_calls_made = 0
            cache_hits = 0

            # Process top liked books to find series (starting with most popular)
            for i, book in enumerate(top_books_to_process):
                book_name = book["book_name"]
                book_author = book.get("book_author", "")

                # EARLY EXIT: Stop if we already have enough recommendations
                if len(all_recommendations) >= limit:
                    break

                try:
                    book_start = time.time()
                    series_rec = self._get_series_recommendation(book_name, book_author)
                    book_time = time.time() - book_start

                    if book_time > 1.0:  # Track slow LLM calls
                        llm_calls_made += 1
                    else:
                        cache_hits += 1
                    if series_rec:
                        # Check if user already liked the recommended book
                        next_book_title = series_rec["next_book"]["title"]
                        if not self._user_already_liked_book(user_id, next_book_title):
                            # Enhanced duplicate detection - check both title and normalized title
                            is_duplicate = False
                            normalized_title = next_book_title.lower().strip()

                            for existing_rec in all_recommendations:
                                existing_title = (
                                    existing_rec["next_book"]["title"].lower().strip()
                                )
                                # Check exact match and normalized match
                                if (
                                    existing_title == normalized_title
                                    or self._are_similar_titles(
                                        existing_title, normalized_title
                                    )
                                ):
                                    is_duplicate = True
                                    break

                            if not is_duplicate:
                                all_recommendations.append(series_rec)

                    processed_books.append(
                        {
                            "book_name": book_name,
                            "book_author": book_author,
                            "has_series": series_rec is not None,
                        }
                    )

                except Exception as e:
                    logger.error(f"Error processing book {book_name}: {e}")
                    continue

            # Select the best 3 recommendations based on confidence score and recency
            recommendations = self._select_best_recommendations(
                all_recommendations, limit
            )

            result = {
                "recommendations": recommendations,
                "count": len(recommendations),
                "from_cache": False,
                "processing_time": time.time() - start_time,
                "books_processed": len(top_books_to_process),
                "llm_calls_made": llm_calls_made,
                "cache_hits": cache_hits,
                "total_candidates_found": len(all_recommendations),
                "algorithm": "llm_series_detection_v3_optimized",
                "generated_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            }

            # CACHE FINAL RESULT in Redis for 2 hours
            if recommendations:
                cache_service.redis.set_cache(cache_key, result, 7200)  # 2 hours

            if len(recommendations) == 0:
                result["message"] = "No series found for your liked books."
                result["suggestion"] = (
                    "Try liking books that are part of popular series!"
                )
            elif len(all_recommendations) > limit:
                result["message"] = (
                    f"Found {len(all_recommendations)} series recommendations, showing best {len(recommendations)}"
                )

            return result

        except Exception as e:
            logger.error(f"Error getting user recommendations: {e}")
            return {
                "recommendations": [],
                "count": 0,
                "error": str(e),
                "from_cache": False,
                "processing_time": time.time() - start_time,
            }

    def _get_series_recommendation(self, book_name, book_author):
        """Get series recommendation for a specific book"""
        try:
            # Check cache/database first
            series_info = self.book_series.get_series_info(book_name, book_author)

            if series_info and series_info.get("is_series", False):
                return self._format_recommendation(book_name, book_author, series_info)

            # Check Redis cache for LLM response first
            llm_cache_key = f"llm_series:{book_name}:{book_author}".lower().replace(
                " ", "_"
            )
            cached_llm_response = cache_service.redis.get_cache(llm_cache_key)

            if cached_llm_response:
                llm_response = cached_llm_response
                success = True
                metadata = {"cached": True}
            else:
                # Query LLM if not cached
                llm_service = self._get_llm_service()
                success, llm_response, metadata = llm_service.detect_book_series(
                    book_name, book_author
                )

                # Cache LLM response for 24 hours
                if success and llm_response:
                    cache_service.redis.set_cache(
                        llm_cache_key, llm_response, 86400
                    )  # 24 hours

            if success and llm_response and llm_response.get("is_series", False):


                return self._format_recommendation(book_name, book_author, llm_response)
            else:
                return None

        except Exception as e:
            logger.error(f"Error getting series recommendation for {book_name}: {e}")
            return None

    def _format_recommendation(self, original_book, original_author, series_data):
        """Format recommendation for frontend display"""
        try:
            next_book = series_data.get("next_book", {})

            # Ensure we have required fields
            if not next_book.get("title") or not next_book.get("author"):
                return None

            recommendation = {
                "original_book": {
                    "name": original_book,
                    "author": original_author or "Unknown Author",
                },
                "next_book": {
                    "title": next_book["title"],
                    "author": next_book["author"],
                    "description": next_book.get(
                        "description", "No description available."
                    ),
                    "order_in_series": next_book.get("order_in_series", 1),
                },
                "series_name": series_data.get("series_name", "Unknown Series"),
                "attribution": f"Next book for: {original_book}",
                "confidence_score": series_data.get("confidence", 0.8),
                "verification_status": series_data.get(
                    "verification_status", "pending"
                ),
            }

            return recommendation

        except Exception as e:
            logger.error(f"Error formatting recommendation: {e}")
            return None

    def _user_already_liked_book(self, user_id, book_title):
        """Check if user already liked the recommended book"""
        try:
            user_interaction = self.user_interactions.get_user_interaction(
                user_id, book_title
            )
            return user_interaction == "like"
        except Exception as e:
            logger.error(f"Error checking user interaction for {book_title}: {e}")
            return False

    def _are_similar_titles(self, title1, title2):
        """Check if two titles are similar (handles variations like 'Catching Fire' vs 'The Hunger Games: Catching Fire')"""
        try:
            # Remove common prefixes and normalize
            def normalize_title(title):
                title = title.lower().strip()
                # Remove series prefixes
                prefixes_to_remove = [
                    "the hunger games:",
                    "harry potter and the",
                    "the maze runner:",
                    "twilight:",
                    "percy jackson:",
                    "the lord of the rings:",
                ]
                for prefix in prefixes_to_remove:
                    if title.startswith(prefix):
                        title = title[len(prefix) :].strip()
                return title

            norm1 = normalize_title(title1)
            norm2 = normalize_title(title2)

            # Check if one contains the other (handles partial matches)
            return norm1 == norm2 or norm1 in norm2 or norm2 in norm1

        except Exception as e:
            logger.error(f"Error comparing titles {title1} and {title2}: {e}")
            return False

    def _select_best_recommendations(self, all_recommendations, limit=3):
        """
        Select the best recommendations from all candidates
        Prioritizes by:
        1. Confidence score (higher is better)
        2. Verification status (verified > pending)
        3. Series popularity (if available)
        4. Original book popularity (from popular books get priority)
        """
        if not all_recommendations:
            return []

        if len(all_recommendations) <= limit:
            return all_recommendations

        # Sort recommendations by quality score
        def calculate_quality_score(rec):
            score = 0

            # Confidence score (0-1) * 100 for base score
            confidence = rec.get("confidence_score", 0.8)
            score += confidence * 100

            # Verification status bonus
            verification = rec.get("verification_status", "pending")
            if verification == "verified":
                score += 20
            elif verification == "pending":
                score += 10

            # Series name length bonus (more specific names often indicate real series)
            series_name = rec.get("series_name", "")
            if len(series_name) > 10:  # Detailed series names
                score += 5

            # Popularity bonus - recommendations from popular books get priority
            original_book = rec.get("original_book", {})
            book_name = original_book.get("name", "")

            # Bonus for well-known popular series
            popular_series_keywords = [
                "harry potter",
                "hunger games",
                "maze runner",
                "twilight",
                "percy jackson",
                "divergent",
                "lord of the rings",
                "game of thrones",
                "chronicles of narnia",
                "fifty shades",
                "outlander",
                "vampire diaries",
            ]

            for keyword in popular_series_keywords:
                if keyword in book_name.lower() or keyword in series_name.lower():
                    score += 15  # Significant bonus for popular series
                    break

            return score

        # Sort by quality score descending
        sorted_recommendations = sorted(
            all_recommendations, key=calculate_quality_score, reverse=True
        )

        # Take top 'limit' recommendations
        selected = sorted_recommendations[:limit]

        return selected

    def refresh_user_recommendations(self, user_id):
        """Force refresh recommendations for a user by clearing ONLY continue reading cache"""
        try:
            # Clear user cache from book series model
            cleared = self.book_series.invalidate_user_cache(user_id)

            # ONLY clear the exact continue reading cache key - don't touch other caches
            cache_key = f"continue_reading:user:{user_id}"
            cache_service.redis.delete_cache(cache_key)

            # DO NOT clear pattern-based cache as it affects other recommendation systems
            # cache_service.redis.delete_keys_by_pattern(f"continue_reading:user:{user_id}*")  # REMOVED

            # Get fresh recommendations
            result = self.get_user_recommendations(user_id)
            result["refreshed"] = True
            result["cache_cleared"] = True

            return result

        except Exception as e:
            logger.error(f"Error refreshing recommendations for user {user_id}: {e}")
            return {
                "recommendations": [],
                "count": 0,
                "error": str(e),
                "refreshed": False,
            }


# Global instance
continue_reading_service = ContinueReadingService()
