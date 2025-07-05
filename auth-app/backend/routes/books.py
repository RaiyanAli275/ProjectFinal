from flask import Blueprint, request, jsonify
from models.book import Book
from models.user_book_interaction import UserBookInteraction
from models.user_wishlist import UserWishlist
from utils.jwt_helper import token_required
from utils.user_language_detector import (
    user_language_detector,
)  # NEW: Language detection
from services.cache_service import cache_service

books_bp = Blueprint("books", __name__)
book_model = Book()
interaction_model = UserBookInteraction()
wishlist_model = UserWishlist()


@books_bp.route("/search", methods=["GET"])
@token_required
def search_books(current_user_id):
    """Search books by name (protected endpoint) with pagination"""
    try:
        # Get search query parameter
        search_query = request.args.get("q", "").strip()

        if not search_query:
            return (
                jsonify(
                    {
                        "message": "Search query is required",
                        "books": [],
                        "total_count": 0,
                        "has_more": False,
                        "current_page": 1,
                    }
                ),
                400,
            )

        if len(search_query) < 2:
            return (
                jsonify(
                    {
                        "message": "Search query must be at least 2 characters",
                        "books": [],
                        "total_count": 0,
                        "has_more": False,
                        "current_page": 1,
                    }
                ),
                400,
            )

        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        page_size = 5  # Fixed page size for consistent pagination

        # Search books with pagination
        books, total_count = book_model.search_books_by_name(
            search_query, page_size, page
        )

        # Get all book names for batch operations
        book_names = [book["name"] for book in books]

        # Batch queries for better performance
        user_interactions = interaction_model.get_user_interactions_batch(
            current_user_id, book_names
        )
        book_stats = interaction_model.get_book_stats_batch(book_names)
        wishlist_status = wishlist_model.get_wishlist_status_batch(
            current_user_id, book_names
        )

        return (
            jsonify(
                {
                    "message": f'Found {total_count} books matching "{search_query}"',
                    "books": books,
                    "total_count": total_count,
                    "has_more": total_count > (page * page_size),
                    "current_page": page,
                    "query": search_query,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@books_bp.route("/like", methods=["POST"])
@token_required
def like_book(current_user_id):
    """Like a book"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "No data provided"}), 400

        book_name = data.get("book_name")
        book_author = data.get("book_author", "")
        book_genres = data.get("book_genres", "")

        if not book_name:
            return jsonify({"message": "Book name is required"}), 400

        # Like the book
        success = interaction_model.like_book(
            current_user_id, book_name, book_author, book_genres
        )

        if success:
            # Invalidate relevant caches since book stats changed
            cache_service.redis.delete_keys_by_pattern("popular_books:*")
            cache_service.redis.delete_keys_by_pattern("search:*")
            cache_service.redis.delete_keys_by_pattern(
                "popular_lang:*"
            )  # Language-filtered cache

            # Get updated stats
            book_stats = interaction_model.get_book_stats(book_name)

            return (
                jsonify(
                    {
                        "message": "Book liked successfully",
                        "book_name": book_name,
                        "action": "like",
                        "likes": book_stats["likes"],
                        "dislikes": book_stats["dislikes"],
                    }
                ),
                200,
            )
        else:
            return jsonify({"message": "Failed to like book"}), 500

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@books_bp.route("/dislike", methods=["POST"])
@token_required
def dislike_book(current_user_id):
    """Dislike a book"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "No data provided"}), 400

        book_name = data.get("book_name")
        book_author = data.get("book_author", "")
        book_genres = data.get("book_genres", "")

        if not book_name:
            return jsonify({"message": "Book name is required"}), 400

        # Dislike the book
        success = interaction_model.dislike_book(
            current_user_id, book_name, book_author, book_genres
        )

        if success:
            # Invalidate relevant caches since book stats changed
            cache_service.redis.delete_keys_by_pattern("popular_books:*")
            cache_service.redis.delete_keys_by_pattern("search:*")
            cache_service.redis.delete_keys_by_pattern(
                "popular_lang:*"
            )  # Language-filtered cache

            # Get updated stats
            book_stats = interaction_model.get_book_stats(book_name)

            return (
                jsonify(
                    {
                        "message": "Book disliked successfully",
                        "book_name": book_name,
                        "action": "dislike",
                        "likes": book_stats["likes"],
                        "dislikes": book_stats["dislikes"],
                    }
                ),
                200,
            )
        else:
            return jsonify({"message": "Failed to dislike book"}), 500

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@books_bp.route("/remove-interaction", methods=["POST"])
@token_required
def remove_interaction(current_user_id):
    """Remove user's interaction with a book"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "No data provided"}), 400

        book_name = data.get("book_name")
        book_author = data.get("book_author", "")
        book_genres = data.get("book_genres", "")
        action = data.get("action")  # Get action from request

        if not book_name:
            return jsonify({"message": "Book name is required"}), 400

        if not action:
            return jsonify({"message": "Action (like/dislike) is required"}), 400

        # Remove interaction
        success = interaction_model.remove_interaction(
            current_user_id, book_name, book_author, book_genres, action
        )

        if success:
            # Invalidate relevant caches since book stats changed
            cache_service.redis.delete_keys_by_pattern("popular_books:*")
            cache_service.redis.delete_keys_by_pattern("search:*")
            cache_service.redis.delete_keys_by_pattern(
                "popular_lang:*"
            )  # Language-filtered cache

            # Get updated stats
            book_stats = interaction_model.get_book_stats(book_name)

            return (
                jsonify(
                    {
                        "message": "Interaction removed successfully",
                        "book_name": book_name,
                        "action": None,
                        "likes": book_stats["likes"],
                        "dislikes": book_stats["dislikes"],
                    }
                ),
                200,
            )
        else:
            return jsonify({"message": "No interaction found or failed to remove"}), 404

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@books_bp.route("/user-interactions", methods=["GET"])
@token_required
def get_user_interactions(current_user_id):
    """Get user's book interactions"""
    try:
        action = request.args.get("action")  # 'like', 'dislike', or None for all
        limit = request.args.get("limit", 50, type=int)
        limit = min(limit, 200)  # Increased cap to 200 results

        interactions = interaction_model.get_user_interactions(
            current_user_id, action, limit
        )

        return (
            jsonify(
                {
                    "message": f"Retrieved {len(interactions)} interactions",
                    "interactions": interactions,
                    "count": len(interactions),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@books_bp.route("/popular", methods=["GET"])
@token_required
def get_popular_books(current_user_id):
    """Get popular books ranked by num_ratings * star_rating, with language filtering"""
    try:
        # Get parameters - Optimized for performance
        limit = request.args.get(
            "limit", 50, type=int
        )  # Balanced limit for performance
        force_refresh = request.args.get("refresh", "false").lower() == "true"

        # Try to get language-filtered popular books first
        books = book_model.get_popular_books_by_score_with_language_filter(
            current_user_id, limit, force_refresh=force_refresh
        )

        # If no books found with language filter, fallback to regular popular books
        if not books:
            books = book_model.get_popular_books_by_score(limit)

        return (
            jsonify(
                {
                    "message": f"Retrieved {len(books)} popular books",
                    "books": books,
                    "count": len(books),
                    "ranking_method": "popularity_score (num_ratings * star_rating)",
                    "language_filtered": (
                        len(books) > 0 and "language_of_book" in books[0]
                        if books
                        else False
                    ),
                    "force_refresh": force_refresh,
                    "from_cache": not force_refresh,
                    "optimization_status": "hybrid (pre-computed + runtime fallback)",
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@books_bp.route("/popular/refresh", methods=["POST"])
@token_required
def refresh_popular_books(current_user_id):
    """Force refresh popular books by clearing cache and recalculating"""
    try:
        limit = request.args.get("limit", 50, type=int)

        # Clear relevant caches
        cache_service.redis.delete_keys_by_pattern("popular_books:*")
        cache_service.redis.delete_keys_by_pattern("popular_lang:*")

        # Get fresh popular books with force refresh
        books = book_model.get_popular_books_by_score_with_language_filter(
            current_user_id, limit, force_refresh=True
        )

        # If no books found with language filter, fallback to regular popular books
        if not books:
            books = book_model.get_popular_books_by_score(limit)

        return (
            jsonify(
                {
                    "message": f"Refreshed {len(books)} popular books",
                    "books": books,
                    "count": len(books),
                    "ranking_method": "popularity_score (num_ratings * star_rating)",
                    "language_filtered": (
                        len(books) > 0 and "language_of_book" in books[0]
                        if books
                        else False
                    ),
                    "refreshed": True,
                    "cache_cleared": True,
                    "optimization_status": "hybrid (pre-computed + runtime fallback)",
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@books_bp.route("/popular/by-user-genres", methods=["GET"])
@token_required
def get_popular_books_by_user_genres(current_user_id):
    """Get popular books in user's top 2 most liked genres for personalized dashboards - ULTRA OPTIMIZED"""
    import time

    start_time = time.time()

    try:
        # Get limit parameter - Optimized for performance
        limit = request.args.get(
            "limit", 20, type=int
        )  # Balanced limit for performance
        limit = min(limit, 50)  # Max 50 books per genre

        # TIMEOUT PROTECTION: Set maximum execution time
        max_execution_time = 45  # 45 seconds max

        # CIRCUIT BREAKER: Check if this endpoint has been failing
        failure_cache_key = f"dashboard_failures:{current_user_id}"
        recent_failures = cache_service.redis.get_cache(failure_cache_key) or 0

        if recent_failures >= 3:
            # If user has had 3+ recent failures, return fallback immediately
            return (
                jsonify(
                    {
                        "message": "Personalized dashboards temporarily unavailable - showing fallback content",
                        "suggestion": "Please try again in a few minutes",
                        "genre1": {"genre": "Popular", "books": [], "like_count": 0},
                        "genre2": {"genre": "Trending", "books": [], "like_count": 0},
                        "count": 0,
                        "has_enough_data": False,
                        "fallback_mode": True,
                        "circuit_breaker_active": True,
                    }
                ),
                200,
            )

        # TIMEOUT CHECK: Monitor execution time
        def check_timeout():
            if time.time() - start_time > max_execution_time:
                raise TimeoutError("Dashboard query exceeded maximum execution time")

        check_timeout()

        # Get popular books by user's top genres with timeout monitoring
        genre_books = book_model.get_popular_books_by_user_top_genres(
            current_user_id, limit
        )

        check_timeout()

        # Check if user has enough genre data
        if not genre_books.get("has_enough_data", False):
            return (
                jsonify(
                    {
                        "message": "Need to like books from at least 2 different genres to see personalized dashboards",
                        "suggestion": "Like books from different genres to get personalized popular book recommendations",
                        "genre1": {"genre": None, "books": [], "like_count": 0},
                        "genre2": {"genre": None, "books": [], "like_count": 0},
                        "count": 0,
                        "has_enough_data": False,
                    }
                ),
                200,
            )

        check_timeout()

        # OPTIMIZATION: Collect all book names from both genres for batch queries
        all_book_names = []
        all_book_names.extend([book["name"] for book in genre_books["genre1"]["books"]])
        all_book_names.extend([book["name"] for book in genre_books["genre2"]["books"]])

        # Skip batch processing if no books found (saves time)
        if not all_book_names:
            execution_time = time.time() - start_time
            return (
                jsonify(
                    {
                        "message": f"No popular books found for your top genres",
                        "genre1": {
                            "genre": genre_books["genre1"]["genre"],
                            "books": [],
                            "count": 0,
                            "like_count": genre_books["genre1"]["like_count"],
                        },
                        "genre2": {
                            "genre": genre_books["genre2"]["genre"],
                            "books": [],
                            "count": 0,
                            "like_count": genre_books["genre2"]["like_count"],
                        },
                        "total_books": 0,
                        "has_enough_data": True,
                        "execution_time": f"{execution_time:.2f}s",
                        "optimization_status": "ultra_fast_cached",
                    }
                ),
                200,
            )

        check_timeout()

        total_books = len(genre_books["genre1"]["books"]) + len(
            genre_books["genre2"]["books"]
        )
        execution_time = time.time() - start_time

        # SUCCESS: Reset failure counter on successful response
        cache_service.redis.delete_cache(failure_cache_key)

        return (
            jsonify(
                {
                    "message": f"Retrieved popular books for your top 2 genres",
                    "genre1": {
                        "genre": genre_books["genre1"]["genre"],
                        "books": genre_books["genre1"]["books"],
                        "count": len(genre_books["genre1"]["books"]),
                        "like_count": genre_books["genre1"]["like_count"],
                    },
                    "genre2": {
                        "genre": genre_books["genre2"]["genre"],
                        "books": genre_books["genre2"]["books"],
                        "count": len(genre_books["genre2"]["books"]),
                        "like_count": genre_books["genre2"]["like_count"],
                    },
                    "total_books": total_books,
                    "has_enough_data": True,
                    "execution_time": f"{execution_time:.2f}s",
                    "ranking_method": "popularity_score (num_ratings * star_rating)",
                    "personalization": "based_on_user_top_2_liked_genres",
                    "optimization_status": "ultra_optimized_with_timeout_protection",
                }
            ),
            200,
        )

    except TimeoutError as timeout_error:
        execution_time = time.time() - start_time
        # TIMEOUT HANDLING: Increment failure counter
        cache_service.redis.set_cache(
            failure_cache_key, recent_failures + 1, 300
        )  # 5 min expiry

        return (
            jsonify(
                {
                    "message": "Dashboard query timed out - please try again",
                    "error": "Request exceeded maximum execution time",
                    "execution_time": f"{execution_time:.2f}s",
                    "has_enough_data": False,
                    "timeout": True,
                    "suggestion": "The server is optimizing your dashboard. Please try again in a moment.",
                }
            ),
            408,
        )  # Request Timeout

    except Exception as e:
        execution_time = time.time() - start_time
        # ERROR HANDLING: Increment failure counter
        cache_service.redis.set_cache(
            failure_cache_key, recent_failures + 1, 300
        )  # 5 min expiry

        print(f"Dashboard error for user {current_user_id}: {e}")
        return (
            jsonify(
                {
                    "message": "Internal server error",
                    "error": str(e),
                    "execution_time": f"{execution_time:.2f}s",
                    "has_enough_data": False,
                    "suggestion": "Please try again. If the problem persists, the system is being optimized.",
                }
            ),
            500,
        )


@books_bp.route("/buy", methods=["POST"])
@token_required
def get_book_purchase_url_post(current_user_id):
    """Get book purchase URL from database via POST request"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "No data provided"}), 400

        book_name = data.get("book_name")

        if not book_name:
            return jsonify({"message": "Book name is required"}), 400

        # Get book URL from database
        book_url = book_model.get_book_url(book_name)

        if book_url:
            return (
                jsonify(
                    {
                        "message": "Book URL retrieved successfully",
                        "book_name": book_name,
                        "url": book_url,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "message": "Book URL not found",
                        "book_name": book_name,
                        "url": None,
                    }
                ),
                404,
            )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500
