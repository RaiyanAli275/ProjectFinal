from flask import Flask, jsonify
from flask_cors import CORS
from routes.auth import auth_bp
from routes.books import books_bp
from routes.continue_reading import continue_reading_bp
from routes.best_from_author import best_from_author_bp
from routes.wishlist import wishlist_bp
from routes.counter import counter_bp
from routes.recommendations import recommendations_bp
import sys
import os
import atexit
import logging

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Initialize database managers and cache service
from database.mongodb_manager import mongodb_manager
from database.redis_manager import redis_manager
from services.cache_service import cache_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)

    # Enable CORS for all routes
    CORS(app, origins=["http://localhost:3000", "http://localhost:3001"])

    # Initialize connection pools on app startup
    initialize_connections()

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(books_bp, url_prefix="/api/books")
    app.register_blueprint(continue_reading_bp, url_prefix="/api/continue-reading")
    app.register_blueprint(best_from_author_bp, url_prefix="/api/recommendations")
    app.register_blueprint(wishlist_bp, url_prefix="/api/wishlist")
    app.register_blueprint(counter_bp, url_prefix="/api/counter")
    app.register_blueprint(recommendations_bp, url_prefix="/api/recommendations")

    # Health check endpoint with connection pool status
    @app.route("/health")
    def health_check():
        from models.recommendation_engine import recommendation_engine
        from models.ContentBasedRecommender import content_based_recommender

        mongodb_stats = mongodb_manager.get_connection_stats()
        redis_stats = redis_manager.get_connection_stats()
        cache_stats = cache_service.get_cache_stats()

        return (
            jsonify(
                {
                    "status": "healthy",
                    "message": "Auth API is running with connection pooling",
                    "connections": {
                        "mongodb": {"status": "connected", "pool_stats": mongodb_stats},
                        "redis": {
                            "status": (
                                "connected"
                                if redis_manager.is_available()
                                else "disconnected"
                            ),
                            "pool_stats": redis_stats,
                        },
                        "cache": cache_stats,
                    },
                    "models": {
                        "als": {
                            "loaded": recommendation_engine.model is not None,
                            "status": (
                                "loaded"
                                if recommendation_engine.model is not None
                                else "not_loaded"
                            ),
                        },
                        "content_based": {
                            "loaded": content_based_recommender.model_loaded,
                            "status": (
                                "loaded"
                                if content_based_recommender.model_loaded
                                else "not_loaded"
                            ),
                        },
                    },
                }
            ),
            200,
        )

    # Root endpoint
    @app.route("/")
    def root():
        return (
            jsonify(
                {
                    "message": "Holmes API with AI-Powered Discovery & Connection Pooling",
                    "version": "2.1.0",
                    "features": [
                        "JWT Authentication",
                        "Book Search",
                        "ALS Matrix Factorization",
                        "Collaborative Filtering",
                        "MongoDB Connection Pooling",
                        "Redis Caching",
                        "Background Cache Refresh",
                    ],
                    "performance": {
                        "mongodb_pool": "Optimized for 50 concurrent users",
                        "redis_cache": "TTL-based caching for recommendations and popular books",
                        "cache_invalidation": "Smart invalidation on user interactions",
                    },
                    "endpoints": {
                        "auth": {
                            "register": "/api/register",
                            "login": "/api/login",
                            "verify": "/api/verify",
                            "user": "/api/user",
                            "logout": "/api/logout",
                        },
                        "books": {
                            "search": "/api/books/search",
                            "recommendations": "/api/books/recommendations",
                            "interact": "/api/books/interact",
                            "preferences": "/api/books/user-interactions",
                            "popular": "/api/books/popular",
                        },
                        "wishlist": {
                            "get_wishlist": "/api/wishlist/",
                            "add_book": "/api/wishlist/add",
                            "remove_book": "/api/wishlist/remove",
                            "toggle_book": "/api/wishlist/toggle",
                            "check_status": "/api/wishlist/check",
                            "check_batch": "/api/wishlist/check-batch",
                            "clear_all": "/api/wishlist/clear",
                            "get_count": "/api/wishlist/count",
                            "get_statistics": "/api/wishlist/statistics",
                        },
                        "counter": {
                            "status": "/api/counter/status",
                            "manual_trigger": "/api/counter/manual-trigger",
                            "reset": "/api/counter/reset",
                            "history": "/api/counter/history",
                            "test_increment": "/api/counter/test-increment",
                        },
                        "monitoring": {
                            "health": "/health",
                            "connection_stats": "Included in /health endpoint",
                        },
                    },
                }
            ),
            200,
        )

    # Connection status endpoint for monitoring
    @app.route("/api/connections/status")
    def connection_status():
        mongodb_stats = mongodb_manager.get_connection_stats()
        redis_stats = redis_manager.get_connection_stats()

        return (
            jsonify(
                {
                    "mongodb": {"connected": True, "pool_stats": mongodb_stats},
                    "redis": {
                        "connected": redis_manager.is_available(),
                        "pool_stats": redis_stats,
                    },
                    "cache_service": {
                        "available": cache_service.redis.is_available(),
                        "stats": cache_service.get_cache_stats(),
                    },
                }
            ),
            200,
        )

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"message": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"message": "Internal server error"}), 500

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"message": "Method not allowed"}), 405

    return app


def initialize_connections():
    """Initialize all connection pools and recommendation models"""
    try:
        # MongoDB connection pool is initialized automatically via singleton
        logger.info("✅ MongoDB connection pool initialized")

        # Redis connection pool is initialized automatically via singleton
        if redis_manager.is_available():
            logger.info("✅ Redis connection pool initialized")
        else:
            logger.warning("⚠️ Redis connection failed - continuing without caching")

        # Load ALS Collaborative Filtering model
        from models.recommendation_engine import recommendation_engine

        recommendation_engine._load_model()
        # Load Content-based model core components
        from models.ContentBasedRecommender import content_based_recommender

        content_based_recommender.load_core_components()

        # Register cleanup function
        atexit.register(cleanup_connections)

    except Exception as e:
        logger.error(f"❌ Error initializing connections: {e}")
        raise


def cleanup_connections():
    """Clean up connections on app shutdown"""
    try:
        mongodb_manager.close_connection()
        redis_manager.close_connection()
    except Exception as e:
        logger.error(f"Error closing connections: {e}")


if __name__ == "__main__":
    app = create_app()
    print("🚀 Starting Holmes API with Connection Pooling...")
    print("📍 Server running on: http://localhost:5000")
    print("🔗 Frontend should connect to: http://localhost:5000/api")
    app.run(debug=False, host="0.0.0.0", port=5000)
