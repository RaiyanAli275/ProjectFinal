from flask import Blueprint, request, jsonify
from utils.jwt_helper import token_required
from services.continue_reading_service import continue_reading_service
from models.user_book_interaction import UserBookInteraction
from models.book_series import BookSeries
from datetime import datetime
import logging

continue_reading_bp = Blueprint("continue_reading", __name__)
interaction_model = UserBookInteraction()
book_series_model = BookSeries()
logger = logging.getLogger(__name__)


@continue_reading_bp.route("/", methods=["GET"])
@token_required
def get_continue_reading_recommendations(current_user_id):
    """Get continue reading recommendations for user"""
    try:
        limit = request.args.get("limit", 3, type=int)
        limit = min(limit, 5)  # Max 5 recommendations

        result = continue_reading_service.get_user_recommendations(
            current_user_id, limit
        )

        response_data = {
            "message": f'Retrieved {result["count"]} continue reading recommendations',
            "recommendations": result["recommendations"],
            "count": result["count"],
            "from_cache": result.get("from_cache", False),
            "processing_time": result.get("processing_time", 0),
            "section": "continue_reading",
            "algorithm": "llm_series_detection",
        }

        # Add optional fields if they exist
        if "message" in result:
            response_data["user_message"] = result["message"]
        if "suggestion" in result:
            response_data["suggestion"] = result["suggestion"]
        if "processed_books" in result:
            response_data["processed_books"] = result["processed_books"]
        if "liked_books_count" in result:
            response_data["liked_books_count"] = result["liked_books_count"]
        if "error" in result:
            response_data["error"] = result["error"]

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error getting continue reading recommendations: {e}")
        return (
            jsonify(
                {
                    "message": "Internal server error",
                    "error": str(e),
                    "recommendations": [],
                    "count": 0,
                    "section": "continue_reading",
                }
            ),
            500,
        )


@continue_reading_bp.route("/refresh", methods=["POST"])
@token_required
def refresh_recommendations(current_user_id):
    """Force refresh continue reading recommendations"""
    try:

        # Get fresh recommendations
        result = continue_reading_service.refresh_user_recommendations(current_user_id)

        # Add user interaction data for each recommendation
        for rec in result.get("recommendations", []):
            next_book_name = rec["next_book"]["title"]

            try:
                user_interaction = interaction_model.get_user_interaction(
                    current_user_id, next_book_name
                )
                rec["user_interaction"] = user_interaction

                # Get book stats
                book_stats = interaction_model.get_book_stats(next_book_name)
                rec["likes"] = book_stats["likes"]
                rec["dislikes"] = book_stats["dislikes"]

            except Exception as e:
                logger.warning(
                    f"Error adding interaction data for {next_book_name}: {e}"
                )
                # Set default values
                rec["user_interaction"] = None
                rec["user_rating"] = None
                rec["likes"] = 0
                rec["dislikes"] = 0
                rec["average_rating"] = None
                rec["total_ratings"] = 0

        return (
            jsonify(
                {
                    "message": "Recommendations refreshed successfully",
                    "recommendations": result["recommendations"],
                    "count": result["count"],
                    "refreshed": result.get("refreshed", True),
                    "cache_cleared": result.get("cache_cleared", False),
                    "processing_time": result.get("processing_time", 0),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error refreshing recommendations: {e}")
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
