from flask import Blueprint, request, jsonify
from models.user_wishlist import UserWishlist
from models.user_book_interaction import UserBookInteraction
from utils.jwt_helper import token_required

wishlist_bp = Blueprint("wishlist", __name__)
wishlist_model = UserWishlist()
interaction_model = UserBookInteraction()


@wishlist_bp.route("/", methods=["GET"])
@token_required
def get_user_wishlist(current_user_id):
    """Get user's wishlist with pagination"""
    try:
        # Get pagination parameters
        limit = request.args.get("limit", 50, type=int)
        limit = min(limit, 100)  # Cap at 100 items
        skip = request.args.get("skip", 0, type=int)

        # Get wishlist
        wishlist_data = wishlist_model.get_user_wishlist(current_user_id, limit, skip)

        return (
            jsonify(
                {
                    "message": f'Retrieved {wishlist_data["count"]} wishlist items',
                    "wishlist": wishlist_data["wishlist"],
                    "count": wishlist_data["count"],
                    "total_count": wishlist_data["total_count"],
                    "has_more": (skip + limit) < wishlist_data["total_count"],
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@wishlist_bp.route("/add", methods=["POST"])
@token_required
def add_to_wishlist(current_user_id):
    """Add a book to user's wishlist"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "No data provided"}), 400

        book_name = data.get("book_name")
        book_author = data.get("book_author", "")
        book_genres = data.get("book_genres", "")

        if not book_name:
            return jsonify({"message": "Book name is required"}), 400

        # Add to wishlist
        result = wishlist_model.add_to_wishlist(
            current_user_id, book_name, book_author, book_genres
        )

        if result["success"]:
            # Get updated wishlist count
            wishlist_count = wishlist_model.get_wishlist_count(current_user_id)

            return (
                jsonify(
                    {
                        "message": result["message"],
                        "book_name": book_name,
                        "in_wishlist": True,
                        "wishlist_count": wishlist_count,
                    }
                ),
                200,
            )
        else:
            status_code = 409 if "already in" in result["message"] else 500
            return (
                jsonify(
                    {
                        "message": result["message"],
                        "book_name": book_name,
                        "in_wishlist": status_code == 409,
                    }
                ),
                status_code,
            )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@wishlist_bp.route("/remove", methods=["POST"])
@token_required
def remove_from_wishlist(current_user_id):
    """Remove a book from user's wishlist"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "No data provided"}), 400

        book_name = data.get("book_name")

        if not book_name:
            return jsonify({"message": "Book name is required"}), 400

        # Remove from wishlist
        result = wishlist_model.remove_from_wishlist(current_user_id, book_name)

        if result["success"]:
            # Get updated wishlist count
            wishlist_count = wishlist_model.get_wishlist_count(current_user_id)

            return (
                jsonify(
                    {
                        "message": result["message"],
                        "book_name": book_name,
                        "in_wishlist": False,
                        "wishlist_count": wishlist_count,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "message": result["message"],
                        "book_name": book_name,
                        "in_wishlist": False,
                    }
                ),
                404,
            )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@wishlist_bp.route("/toggle", methods=["POST"])
@token_required
def toggle_wishlist(current_user_id):
    """Toggle a book's wishlist status (add if not in wishlist, remove if in wishlist)"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "No data provided"}), 400

        book_name = data.get("book_name")
        book_author = data.get("book_author", "")
        book_genres = data.get("book_genres", "")

        if not book_name:
            return jsonify({"message": "Book name is required"}), 400

        # Check if book is currently in wishlist
        is_in_wishlist = wishlist_model.is_in_wishlist(current_user_id, book_name)

        if is_in_wishlist:
            # Remove from wishlist
            result = wishlist_model.remove_from_wishlist(current_user_id, book_name)
            action = "removed"
            new_status = False
        else:
            # Add to wishlist
            result = wishlist_model.add_to_wishlist(
                current_user_id, book_name, book_author, book_genres
            )
            action = "added"
            new_status = True

        if result["success"]:
            # Get updated wishlist count
            wishlist_count = wishlist_model.get_wishlist_count(current_user_id)

            return (
                jsonify(
                    {
                        "message": f'Book {action} {"to" if action == "added" else "from"} wishlist successfully',
                        "book_name": book_name,
                        "action": action,
                        "in_wishlist": new_status,
                        "wishlist_count": wishlist_count,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "message": result["message"],
                        "book_name": book_name,
                        "in_wishlist": is_in_wishlist,  # Keep original status on error
                    }
                ),
                500,
            )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@wishlist_bp.route("/check", methods=["POST"])
@token_required
def check_wishlist_status(current_user_id):
    """Check if a book is in user's wishlist"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "No data provided"}), 400

        book_name = data.get("book_name")

        if not book_name:
            return jsonify({"message": "Book name is required"}), 400

        # Check wishlist status
        in_wishlist = wishlist_model.is_in_wishlist(current_user_id, book_name)

        return jsonify({"book_name": book_name, "in_wishlist": in_wishlist}), 200

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@wishlist_bp.route("/check-batch", methods=["POST"])
@token_required
def check_wishlist_status_batch(current_user_id):
    """Check wishlist status for multiple books"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "No data provided"}), 400

        book_names = data.get("book_names", [])

        if not book_names or not isinstance(book_names, list):
            return jsonify({"message": "book_names array is required"}), 400

        if len(book_names) > 100:  # Limit batch size
            return jsonify({"message": "Maximum 100 books per batch request"}), 400

        # Check wishlist status for all books
        wishlist_status = wishlist_model.get_wishlist_status_batch(
            current_user_id, book_names
        )

        return (
            jsonify(
                {
                    "message": f"Checked wishlist status for {len(book_names)} books",
                    "wishlist_status": wishlist_status,
                    "count": len(book_names),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@wishlist_bp.route("/clear", methods=["POST"])
@token_required
def clear_wishlist(current_user_id):
    """Clear all items from user's wishlist"""
    try:
        # Optional confirmation parameter
        confirm = request.args.get("confirm", "false").lower() == "true"

        if not confirm:
            return (
                jsonify(
                    {
                        "message": "Are you sure you want to clear your entire wishlist?",
                        "confirmation_required": True,
                        "instruction": "Add ?confirm=true to the URL to proceed",
                    }
                ),
                200,
            )

        # Clear wishlist
        result = wishlist_model.clear_wishlist(current_user_id)

        if result["success"]:
            return (
                jsonify(
                    {
                        "message": result["message"],
                        "cleared_count": result["cleared_count"],
                        "wishlist_count": 0,
                    }
                ),
                200,
            )
        else:
            return jsonify({"message": result["message"]}), 500

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@wishlist_bp.route("/count", methods=["GET"])
@token_required
def get_wishlist_count(current_user_id):
    """Get user's wishlist count"""
    try:
        count = wishlist_model.get_wishlist_count(current_user_id)

        return (
            jsonify(
                {
                    "wishlist_count": count,
                    "message": f"You have {count} books in your wishlist",
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@wishlist_bp.route("/statistics", methods=["GET"])
@token_required
def get_wishlist_statistics(current_user_id):
    """Get statistics about user's wishlist"""
    try:
        stats = wishlist_model.get_wishlist_statistics(current_user_id)

        return (
            jsonify(
                {
                    "message": "Wishlist statistics retrieved successfully",
                    "statistics": stats,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500
