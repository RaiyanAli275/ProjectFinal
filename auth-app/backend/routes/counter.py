from flask import Blueprint, request, jsonify
from utils.jwt_helper import token_required
from models.interaction_counter import interaction_counter

counter_bp = Blueprint("counter", __name__)


@counter_bp.route("/status", methods=["GET"])
@token_required
def get_counter_status(current_user_id):
    """Get current counter status and statistics"""
    try:
        return (
            jsonify(
                {
                    "message": "Counter status retrieved successfully",
                    "counter": {
                        "current_count": stats["current_count"],
                        "threshold": stats["threshold"],
                        "progress_percentage": round(
                            (stats["current_count"] / stats["threshold"]) * 100, 1
                        ),
                        "interactions_until_training": max(
                            0, stats["threshold"] - stats["current_count"]
                        ),
                    },
                    "statistics": {
                        "total_retrainings": stats["total_retrainings"],
                        "last_updated": (
                            stats["last_updated"].isoformat()
                            if stats["last_updated"]
                            else None
                        ),
                        "last_reset": (
                            stats["last_reset"].isoformat()
                            if stats["last_reset"]
                            else None
                        ),
                        "created_at": (
                            stats["created_at"].isoformat()
                            if stats["created_at"]
                            else None
                        ),
                        "training_in_progress": stats["training_in_progress"],
                    },
                    "recent_trainings": [
                        {
                            **training,
                            "training_started": (
                                training["training_started"].isoformat()
                                if training.get("training_started")
                                else None
                            ),
                            "training_completed": (
                                training["training_completed"].isoformat()
                                if training.get("training_completed")
                                else None
                            ),
                        }
                        for training in stats["recent_trainings"]
                    ],
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@counter_bp.route("/reset", methods=["POST"])
@token_required
def reset_counter(current_user_id):
    """Reset the counter to 0 (for testing/admin purposes)"""
    try:
        # Get current count before reset
        current_count = interaction_counter.get_current_count()

        # Reset counter
        success = interaction_counter.reset_counter()

        if success:
            return (
                jsonify(
                    {
                        "message": "Counter reset successfully",
                        "previous_count": current_count,
                        "new_count": 0,
                        "reset_success": True,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "message": "Failed to reset counter",
                        "current_count": current_count,
                        "reset_success": False,
                    }
                ),
                500,
            )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@counter_bp.route("/history", methods=["GET"])
@token_required
def get_training_history(current_user_id):
    """Get detailed training history"""
    try:
        limit = request.args.get("limit", 10, type=int)
        limit = min(limit, 50)  # Cap at 50 records

        # Get training history from the database
        history = list(
            interaction_counter.training_history_collection.find({}, {"_id": 0})
            .sort("training_started", -1)
            .limit(limit)
        )

        # Convert datetime objects to ISO strings
        for record in history:
            if record.get("training_started"):
                record["training_started"] = record["training_started"].isoformat()
            if record.get("training_completed"):
                record["training_completed"] = record["training_completed"].isoformat()

        return (
            jsonify(
                {
                    "message": f"Retrieved {len(history)} training records",
                    "training_history": history,
                    "count": len(history),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@counter_bp.route("/test-increment", methods=["POST"])
@token_required
def test_increment(current_user_id):
    """Test endpoint to increment counter (for testing purposes)"""
    try:
        # Get current count before increment
        current_count = interaction_counter.get_current_count()

        # Increment counter
        training_triggered = interaction_counter.increment_counter()

        # Get new count
        new_count = interaction_counter.get_current_count()

        return (
            jsonify(
                {
                    "message": "Counter incremented successfully",
                    "previous_count": current_count,
                    "new_count": new_count,
                    "training_triggered": training_triggered,
                    "threshold": interaction_counter.INTERACTION_THRESHOLD,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500
