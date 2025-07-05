from flask import Blueprint, request, jsonify
from utils.jwt_helper import token_required
from models.user_sorted_author_preferences import user_sorted_author_preferences
from models.user_book_interaction import UserBookInteraction
from models.ContentBasedRecommender import content_based_recommender
from database.mongodb_manager import mongodb_manager
from services.cache_service import cache_service
import time
import logging
from bson import ObjectId

best_from_author_bp = Blueprint("best_from_author", __name__)
interaction_model = UserBookInteraction()
logger = logging.getLogger(__name__)


@best_from_author_bp.route("/best-from-author", methods=["GET"])
@token_required
def get_best_from_author_recommendations(current_user_id):
    """
    Get recommendations from the user's most liked author
    Shows unread books by the author the user likes most
    """
    try:
        start_time = time.time()

        try:
            # Convert user_id to ObjectId once at the start
            user_id_obj = ObjectId(current_user_id)

            # Get parameters
            limit = request.args.get("limit", 10, type=int)
            limit = min(limit, 20)  # Max 20 recommendations

            # AGGRESSIVE CACHING: Check Redis cache first (6 hour TTL for better performance)
            cache_key = f"best_from_author:user_obj:{str(user_id_obj)}:limit:{limit}"
            cached_result = cache_service.redis.get_cache(cache_key)
            if cached_result:
                cached_result["from_cache"] = True
                cached_result["processing_time"] = time.time() - start_time
                return jsonify(cached_result), 200

            # Get most preferred author directly from MongoDB collection
            user_auth_db = mongodb_manager.get_user_auth_database()
            author_preferences = user_auth_db["user_sorted_author_preferences"]
            query = {
                "user_id": user_id_obj,
                "sorted_authors": {"$exists": True, "$ne": []}  # Ensure sorted_authors exists and is not empty
            }
        except Exception as e:
            logger.error(f"Failed to convert user_id to ObjectId: {e}")
            return jsonify({
                "message": "Invalid user ID format",
                "error": str(e),
                "recommendations": [],
                "count": 0,
                "from_cache": False,
                "processing_time": time.time() - start_time,
            }), 400
        author_doc = author_preferences.find_one(query)
        
        if author_doc:
            # Get the first author directly from the sorted array
            best_author = author_doc["sorted_authors"][0]
            author_name = best_author["author_name"]
        else:
            return (
                jsonify(
                    {
                        "message": "Like some books to discover your favorite authors!",
                        "recommendations": [],
                        "count": 0,
                        "from_cache": False,
                        "processing_time": time.time() - start_time,
                        "algorithm": "author_based_recommendations",
                    }
                ),
                200,
            )

        # Get books user has already interacted with
        user_interacted_books = set(
            interaction_model.get_user_interacted_book_names(current_user_id)
        )

        # Find unread books by this author using MongoDB with optimized query
        books_collection = mongodb_manager.get_collection("book", "booksdata")

        # Use exact match with case-insensitive collation for better performance
        author_books_cursor = books_collection.find(
            {
                "author": author_name,  # Exact match
                "name": {
                    "$nin": list(user_interacted_books)
                }  # Exclude already interacted books
            },
            projection={
                "_id": 1,
                "name": 1,
                "author": 1,
                "genres": 1,
                "summary": 1,
                "star_rating": 1,
                "num_ratings": 1,
                "language_of_book": 1,
                "year": 1,
            },
            collation={"locale": "en", "strength": 2}  # Case-insensitive match
        ).limit(limit * 2)

        author_books = list(author_books_cursor)

        # If no exact matches, try more flexible patterns (simplified for performance)
        if not author_books:

            # Single pattern with case-insensitive collation for better performance
            author_books_cursor = books_collection.find(
                {
                    "author": {"$regex": f"{author_name}"},  # Simple pattern match
                    "name": {"$nin": list(user_interacted_books)},
                },
                projection={
                    "_id": 1,
                    "name": 1,
                    "author": 1,
                    "genres": 1,
                    "summary": 1,
                    "star_rating": 1,
                    "num_ratings": 1,
                    "language_of_book": 1,
                    "year": 1,
                },
                collation={"locale": "en", "strength": 2}  # Case-insensitive match
            ).limit(limit * 2)

            author_books = list(author_books_cursor)

        # Skip complex fallback searches for better performance
        # If no books found with flexible pattern, accept empty result

        if not author_books:
            return (
                jsonify(
                    {
                        "message": f"No unread books found by {author_name}. Try exploring more books!",
                        "recommendations": [],
                        "count": 0,
                        "best_author": author_name,
                        "author_preference_count": best_author.get(
                            "preference_count", 0
                        ),
                        "books_liked_by_author": len(
                            best_author.get("books_liked", [])
                        ),
                        "from_cache": False,
                        "processing_time": time.time() - start_time,
                        "algorithm": "author_based_recommendations",
                    }
                ),
                200,
            )

        # Use fast scoring without loading heavy content model
        recommendations = []

        # Process books and create recommendations (optimized)
        for book in author_books[:limit]:
            try:
                # Fast scoring based on author preference and book metadata
                preference_count = best_author.get("preference_count", 0)
                base_score = min(preference_count / 10.0, 1.0)  # Normalize to 0-1

                # Quick metadata-based scoring
                metadata_boost = 0
                if book.get("star_rating", 0) > 4.0:
                    metadata_boost += 0.1
                if book.get("num_ratings", 0) > 1000:
                    metadata_boost += 0.05

                # Calculate final recommendation score (fast)
                recommendation_score = (base_score + metadata_boost) * 100

                recommendation = {
                    "_id": str(book["_id"]),
                    "name": book.get("name"),
                    "author": book.get("author"),
                    "genres": book.get("genres", []),
                    "summary": book.get("summary", ""),
                    "star_rating": book.get("star_rating"),
                    "num_ratings": book.get("num_ratings", 0),
                    "language": book.get("language_of_book"),
                    "year": book.get("year"),
                    "recommendation_score": recommendation_score,
                    "author_preference_count": best_author.get("preference_count", 0),
                    "algorithm": "author_based_recommendations",
                    "confidence": min(
                        base_score + 0.2, 1.0
                    ),  # Higher confidence for author-based
                    "reason": f"Because you loved other books by {author_name}",
                }

                recommendations.append(recommendation)

            except Exception as e:
                logger.warning(
                    f"Error processing book {book.get('name', 'Unknown')}: {e}"
                )
                continue

        # Sort by recommendation score
        recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)

        # Batch fetch user interaction data (optimized)
        response_data = {
            "message": f"Found {len(recommendations)} unread books by your favorite author: {author_name}",
            "recommendations": recommendations,
            "count": len(recommendations),
            "best_author": author_name,
            "author_preference_count": best_author.get("preference_count", 0),
            "books_liked_by_author": len(best_author.get("books_liked", [])),
            "total_interactions_with_author": best_author.get("total_interactions", 0),
            "from_cache": False,
            "processing_time": time.time() - start_time,
            "algorithm": "author_based_recommendations",
            "explanation": f'Based on your love for {author_name} - you\'ve enjoyed {len(best_author.get("books_liked", []))} of their books!',
        }

        # CACHE RESULT for 6 hours if successful (better performance)
        if len(recommendations) > 0:
            cache_service.redis.set_cache(cache_key, response_data, 21600)  # 6 hours

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error getting best-from-author recommendations: {e}")
        return (
            jsonify(
                {
                    "message": "Internal server error",
                    "error": str(e),
                    "recommendations": [],
                    "count": 0,
                    "from_cache": False,
                    "processing_time": (
                        time.time() - start_time if "start_time" in locals() else 0
                    ),
                }
            ),
            500,
        )


@best_from_author_bp.route("/best-from-author/refresh", methods=["POST"])
@token_required
def refresh_best_from_author_recommendations(current_user_id):
    """Force refresh best-from-author recommendations by clearing cache"""
    try:

        # Convert user_id to ObjectId for consistent cache key format
        try:
            user_id_obj = ObjectId(current_user_id)
            # Clear cache with consistent key format
            pattern = f"best_from_author:user_obj:{str(user_id_obj)}:*"
            cache_service.redis.delete_keys_by_pattern(pattern)
        except Exception as e:
            logger.error(f"Failed to convert user_id to ObjectId: {e}")
            return jsonify({
                "message": "Invalid user ID format",
                "error": str(e),
                "refreshed": False,
            }), 400

        return (
            jsonify(
                {
                    "message": "Best-from-author recommendations refreshed successfully",
                    "refreshed": True,
                    "cache_cleared": True,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error refreshing best-from-author recommendations: {e}")
        return (
            jsonify(
                {
                    "message": "Internal server error",
                    "error": str(e),
                    "refreshed": False,
                }
            ),
            500,
        )
