from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from typing import Optional
import logging
from .config import DatabaseConfig

logger = logging.getLogger(__name__)

class MongoDBManager:
    """Singleton MongoDB connection manager with connection pooling"""
    
    _instance: Optional['MongoDBManager'] = None
    _client: Optional[MongoClient] = None
    _databases: dict = {}
    
    def __new__(cls) -> 'MongoDBManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize MongoDB connection with pooling"""
        try:
            self._client = MongoClient(
                DatabaseConfig.MONGODB_URI,
                **DatabaseConfig.MONGODB_POOL_CONFIG
            )
            
            # Test connection
            self._client.admin.command('ping')
            logger.info("MongoDB connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB connection: {e}")
            raise
    
    def get_database(self, db_name: str = 'booksdata') -> Database:
        """Get database instance with connection pooling"""
        if db_name not in self._databases:
            self._databases[db_name] = self._client[db_name]
        return self._databases[db_name]
    
    def get_collection(self, collection_name: str, db_name: str = 'booksdata') -> Collection:
        """Get collection instance with connection pooling"""
        db = self.get_database(db_name)
        return db[collection_name]
    
    def get_user_auth_database(self) -> Database:
        """Get user authentication database"""
        return self.get_database('user_auth_db')
    
    def get_counter_database(self) -> Database:
        """Get counter database for interaction tracking"""
        return self.get_database('counter')
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._databases.clear()
            logger.info("MongoDB connection closed")
    
    def get_connection_stats(self) -> dict:
        """Get connection pool statistics"""
        if self._client:
            return {
                'pool_size': self._client.options.pool_options.max_pool_size,
                'min_pool_size': self._client.options.pool_options.min_pool_size,
                'max_idle_time': self._client.options.pool_options.max_idle_time_seconds
            }
        return {}

# Global instance
mongodb_manager = MongoDBManager()