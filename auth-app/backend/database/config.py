import os
from typing import Dict, Any

class DatabaseConfig:
    """Database configuration management"""
    
    # MongoDB Configuration
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://alirayan:Ali212153266@cluster0.ksubn7k.mongodb.net/booksdata?retryWrites=true&w=majority')
    
    # MongoDB Connection Pool Settings (optimized for 50 concurrent users, NO TIMEOUTS)
    MONGODB_POOL_CONFIG = {
        'maxPoolSize': 20,        # Maximum connections in pool
        'minPoolSize': 5,         # Minimum connections in pool
        'maxIdleTimeMS': 30000,   # 30 seconds
        # Removed timeout settings to search until results found:
        # 'serverSelectionTimeoutMS': 5000,  # REMOVED
        # 'connectTimeoutMS': 10000,  # REMOVED
        # 'socketTimeoutMS': 20000,   # REMOVED
        'retryWrites': True,
        'w': 'majority'
    }
    
    # Redis Configuration
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    
    # Redis Connection Pool Settings
    REDIS_POOL_CONFIG = {
        'max_connections': 15,    # Maximum connections for 50 users
        'retry_on_timeout': True,
        'decode_responses': True,
        'socket_connect_timeout': 5,
        'socket_timeout': 10,
        'health_check_interval': 30
    }
    
    # Cache TTL Settings (REMOVED TIMEOUTS FOR SEARCH AND POPULAR BOOKS)
    CACHE_TTL = {
        'recommendations': 1800,    # 30 minutes
        'popular_books': None,      # NO EXPIRATION - Cache forever
        'search_results': None,     # NO EXPIRATION - Cache forever  
        'book_details': 1800,       # 30 minutes
        'user_preferences': 600     # 10 minutes
    }