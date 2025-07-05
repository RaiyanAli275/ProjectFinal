from flask import Blueprint, request, jsonify
import re
from models.user import User
from utils.jwt_helper import generate_token, token_required

auth_bp = Blueprint("auth", __name__)
user_model = User()


def validate_email(email):
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"


@auth_bp.route("/register", methods=["POST"])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data or not all(k in data for k in ("username", "email", "password")):
            return jsonify({"message": "Missing required fields"}), 400

        username = data["username"].strip()
        email = data["email"].strip().lower()
        password = data["password"]

        # Validate input
        if len(username) < 3:
            return (
                jsonify({"message": "Username must be at least 3 characters long"}),
                400,
            )

        if not validate_email(email):
            return jsonify({"message": "Invalid email format"}), 400

        is_valid, password_message = validate_password(password)
        if not is_valid:
            return jsonify({"message": password_message}), 400

        # Check if user already exists
        if user_model.user_exists(email=email):
            return jsonify({"message": "Email already registered"}), 409

        if user_model.user_exists(username=username):
            return jsonify({"message": "Username already taken"}), 409

        # Create user
        user_id = user_model.create_user(username, email, password)
        if user_id:
            token = generate_token(user_id)
            return (
                jsonify(
                    {
                        "message": "User registered successfully",
                        "token": token,
                        "user": {"id": user_id, "username": username, "email": email},
                    }
                ),
                201,
            )
        else:
            return jsonify({"message": "Failed to create user"}), 500

    except Exception as e:
        return jsonify({"message": "Internal server error"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()

        if not data or not all(k in data for k in ("email", "password")):
            return jsonify({"message": "Email and password are required"}), 400

        email = data["email"].strip().lower()
        password = data["password"]

        # Find user
        user = user_model.find_user_by_email(email)
        if not user:
            return jsonify({"message": "Invalid credentials"}), 401

        # Verify password
        if not user_model.verify_password(password, user["password"]):
            return jsonify({"message": "Invalid credentials"}), 401

        # Update last login
        user_model.update_last_login(str(user["_id"]))

        # Generate token
        token = generate_token(str(user["_id"]))

        return (
            jsonify(
                {
                    "message": "Login successful",
                    "token": token,
                    "user": {
                        "id": str(user["_id"]),
                        "username": user["username"],
                        "email": user["email"],
                    },
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Internal server error"}), 500


@auth_bp.route("/verify", methods=["GET"])
@token_required
def verify_token(current_user_id):
    """Verify JWT token endpoint"""
    try:
        user = user_model.find_user_by_id(current_user_id)
        if user:
            return (
                jsonify(
                    {
                        "valid": True,
                        "user": {
                            "id": str(user["_id"]),
                            "username": user["username"],
                            "email": user["email"],
                        },
                    }
                ),
                200,
            )
        else:
            return jsonify({"valid": False, "message": "User not found"}), 404
    except Exception as e:
        return jsonify({"valid": False, "message": "Internal server error"}), 500


@auth_bp.route("/user", methods=["GET"])
@token_required
def get_user(current_user_id):
    """Get user profile endpoint"""
    try:
        user = user_model.find_user_by_id(current_user_id)
        if user:
            return (
                jsonify(
                    {
                        "user": {
                            "id": str(user["_id"]),
                            "username": user["username"],
                            "email": user["email"],
                            "created_at": user["created_at"].isoformat(),
                            "last_login": (
                                user["last_login"].isoformat()
                                if user["last_login"]
                                else None
                            ),
                        }
                    }
                ),
                200,
            )
        else:
            return jsonify({"message": "User not found"}), 404
    except Exception as e:
        return jsonify({"message": "Internal server error"}), 500


@auth_bp.route("/logout", methods=["POST"])
@token_required
def logout(current_user_id):
    """User logout endpoint"""
    # In JWT, logout is typically handled client-side by removing the token
    # Server-side logout would require token blacklisting
    return jsonify({"message": "Logout successful"}), 200
