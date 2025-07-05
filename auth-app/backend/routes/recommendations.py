from flask import Blueprint, request, jsonify
from models.book import Book
from models.user_book_interaction import UserBookInteraction
from models.user_wishlist import UserWishlist
from models.ContentBasedRecommender import content_based_recommender
from utils.jwt_helper import token_required
from utils.user_language_detector import (
    user_language_detector,
)  # NEW: Language detection
from services.cache_service import cache_service
import logging
import time


recommendations_bp = Blueprint("recommendations", __name__)
book_model = Book()
interaction_model = UserBookInteraction()
wishlist_model = UserWishlist()
logger = logging.getLogger(__name__)


@recommendations_bp.route("/collaborative", methods=["GET"])
@token_required
def get_collaborative_recommendations(current_user_id):
    """Get enhanced collaborative filtering recommendations - 'Recommended for You' section"""
    try:
        limit = request.args.get("limit", 10, type=int)
        limit = min(limit, 20)

        # Check if user has minimum interactions for collaborative filtering
        user_interaction_count = interaction_model.get_user_interaction_count(
            current_user_id
        )

        if user_interaction_count == 0:
            return (
                jsonify(
                    {
                        "message": "Interact with more books to see collaborative recommendations!",
                        "recommendations": [],
                        "suggestion": "Like, dislike, or rate at least 3 books to get recommendations based on similar users.",
                        "count": 0,
                        "is_new_user": True,
                        "interaction_count": user_interaction_count,
                        "section": "recommended_for_you",
                        "algorithm": "enhanced_collaborative_filtering",
                    }
                ),
                200,
            )

        # Use enhanced UBCF with multi-user fallback
        from models.recommendation_engine import recommendation_engine

        recommendations = recommendation_engine.get_enhanced_ubcf_recommendations(
            current_user_id, limit
        )

        if not recommendations:
            return (
                jsonify(
                    {
                        "message": "No collaborative recommendations available at this time",
                        "recommendations": [],
                        "suggestion": "Try interacting with more books or check back later.",
                        "count": 0,
                        "is_new_user": False,
                        "interaction_count": user_interaction_count,
                        "section": "recommended_for_you",
                        "algorithm": "enhanced_collaborative_filtering",
                    }
                ),
                200,
            )

        return (
            jsonify(
                {
                    "message": f"Generated {len(recommendations)} enhanced collaborative filtering recommendations",
                    "recommendations": recommendations,
                    "count": len(recommendations),
                    "is_new_user": False,
                    "interaction_count": user_interaction_count,
                    "section": "recommended_for_you",
                    "algorithm": "enhanced_collaborative_filtering",
                    "description": "Multi-user cascade: finds books from most similar users until 5 recommendations found",
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


def _content_based_response(user_id, limit, alternative=False):
    """
    Shared helper for both /content-based and /content-based-alt.
    If alternative=True, calls the recommender in alternative mode.
    """
    section = "because_you_liked_alt" if alternative else "because_you_liked"
    algorithm = (
        "content_based_faiss_alternative" if alternative else "content_based_faiss"
    )

    # 1) Get user like-count
    user_likes = interaction_model.get_user_interaction_count_by_action(user_id, "like")
    if user_likes == 0:
        return (
            jsonify(
                {
                    "message": "Like some books to see content-based recommendations!",
                    "recommendations": [],
                    "count": 0,
                    "is_new_user": True,
                    "interaction_count": 0,
                    "section": section,
                    "suggestion": "Start by liking books that interest you to get personalized recommendations based on similar content.",
                }
            ),
            200,
        )

    # 2) Ensure the base model exists / is loaded
    if not content_based_recommender.book_vectors:
        if content_based_recommender._should_retrain():
            if not content_based_recommender.train_model():
                return (
                    jsonify(
                        {
                            "message": "Content-based recommendations temporarily unavailable",
                            "recommendations": [],
                            "count": 0,
                            "error": "model_training_failed",
                            "section": section,
                        }
                    ),
                    500,
                )

    # 3) Fetch recommendations
    recs = content_based_recommender.get_similar_books_for_user(
        user_id, limit, alternative=alternative
    )

    # 4) Handle “no recs” case
    if not recs:
        return (
            jsonify(
                {
                    "message": f'No {"alternative " if alternative else ""}content-based recommendations available at this time',
                    "recommendations": [],
                    "count": 0,
                    "section": section,
                    "suggestion": "Try liking books from different genres or languages to expand your recommendations.",
                }
            ),
            200,
        )

    # 5) Success payload
    return (
        jsonify(
            {
                "message": f"Generated {len(recs)} content-based recommendations",
                "recommendations": recs,
                "count": len(recs),
                "is_new_user": False,
                "interaction_count": user_likes,
                "section": section,
                "algorithm": algorithm,
                "based_on_book": recs[0].get("based_on_book"),
            }
        ),
        200,
    )


@recommendations_bp.route("/content-based", methods=["GET"])
@token_required
def get_content_based_recommendations(current_user_id):
    limit = min(request.args.get("limit", 10, type=int), 20)
    return _content_based_response(current_user_id, limit, alternative=False)


@recommendations_bp.route("/content-based-alt", methods=["GET"])
@token_required
def get_content_based_recommendations_alt(current_user_id):
    limit = min(request.args.get("limit", 10, type=int), 20)
    return _content_based_response(current_user_id, limit, alternative=True)


@recommendations_bp.route("/based-on-likes", methods=["GET"])
@token_required
def get_based_on_likes_recommendations(current_user_id):
    """
    Get content-based recommendations based on user's overall like/dislike patterns
    Uses existing ContentBasedRecommender with user preference profiling
    """
    try:
        start_time = time.time()

        # Get parameters
        limit = request.args.get("limit", 10, type=int)
        limit = min(limit, 20)  # Max 20 recommendations

        # AGGRESSIVE CACHING: Check Redis cache first (2 hour TTL)
        cache_key = f"based_on_likes:user:{current_user_id}:{limit}"
        cached_result = cache_service.redis.get_cache(cache_key)

        if cached_result:
            cached_result["from_cache"] = True
            cached_result["processing_time"] = time.time() - start_time
            return jsonify(cached_result), 200

        # Get user's interaction history
        liked_books = interaction_model.get_user_interactions(
            current_user_id, action="like", limit=1000
        )
        disliked_books = interaction_model.get_user_interactions(
            current_user_id, action="dislike", limit=1000
        )

        if not liked_books:
            return (
                jsonify(
                    {
                        "message": "Like some books to see personalized recommendations!",
                        "recommendations": [],
                        "count": 0,
                        "from_cache": False,
                        "processing_time": time.time() - start_time,
                        "algorithm": "content_based_preference_profiling",
                    }
                ),
                200,
            )

        # Use content-based recommender for preference profiling
        result = content_based_recommender.get_based_on_likes_recommendations(
            user_id=current_user_id,
            liked_books=liked_books,
            disliked_books=disliked_books,
            limit=limit,
        )
        response_data = {
            "message": f'Found {result["count"]} recommendations based on your reading preferences',
            "recommendations": result["recommendations"],
            "count": result["count"],
            "liked_books_analyzed": len(liked_books),
            "disliked_books_analyzed": len(disliked_books),
            "from_cache": False,
            "processing_time": time.time() - start_time,
            "algorithm": "content_based_preference_profiling",
            "explanation": result.get(
                "explanation", "Based on your overall reading preferences"
            ),
        }

        # CACHE RESULT for 2 hours if successful
        if result["count"] > 0:
            cache_service.redis.set_cache(cache_key, response_data, 7200)  # 2 hours

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error getting based-on-likes recommendations: {e}")
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


@recommendations_bp.route("/based-on-likes/refresh", methods=["POST"])
@token_required
def refresh_based_on_likes_recommendations(current_user_id):
    """Force refresh based-on-likes recommendations by clearing cache"""
    try:

        # Clear cache for this user
        cache_service.redis.delete_keys_by_pattern(
            f"based_on_likes:user:{current_user_id}:*"
        )

        return (
            jsonify(
                {
                    "message": "Based-on-likes recommendations refreshed successfully",
                    "refreshed": True,
                    "cache_cleared": True,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error refreshing based-on-likes recommendations: {e}")
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
