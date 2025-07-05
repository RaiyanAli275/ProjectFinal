from bson.objectid import ObjectId
import bcrypt
from datetime import datetime
from database.mongodb_manager import mongodb_manager


class User:
    def __init__(self):
        # Use the shared MongoDB connection pool
        self.db = mongodb_manager.get_user_auth_database()
        self.collection = self.db["users"]

        # Create unique indexes
        try:
            self.collection.create_index("email", unique=True)
            self.collection.create_index("username", unique=True)
        except Exception:
            # Indexes might already exist
            pass

    def create_user(self, username, email, password):
        """Create a new user with hashed password"""
        try:
            # Hash password
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)

            user_data = {
                "username": username,
                "email": email,
                "password": hashed_password,
                "created_at": datetime.utcnow(),
                "last_login": None,
                "user_languages": [],  # Initialize empty languages list
            }

            result = self.collection.insert_one(user_data)
            return str(result.inserted_id)
        except Exception as e:
            return None

    def find_user_by_email(self, email):
        """Find user by email"""
        return self.collection.find_one({"email": email})

    def find_user_by_username(self, username):
        """Find user by username"""
        return self.collection.find_one({"username": username})

    def find_user_by_id(self, user_id):
        """Find user by ID"""
        try:
            return self.collection.find_one({"_id": ObjectId(user_id)})
        except:
            return None

    def verify_password(self, password, hashed_password):
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password)

    def update_last_login(self, user_id):
        """Update user's last login time"""
        try:
            self.collection.update_one(
                {"_id": ObjectId(user_id)}, {"$set": {"last_login": datetime.utcnow()}}
            )
            return True
        except:
            return False

    def user_exists(self, email=None, username=None):
        """Check if user exists by email or username"""
        query = {}
        if email:
            query["email"] = email
        if username:
            query["username"] = username

        return self.collection.find_one(query) is not None

    def add_user_language(self, user_id, language):
        """Add a language to user's languages list if not already present"""
        try:
            if not language:
                return True

            # Use $addToSet to add language only if it doesn't exist
            self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$addToSet": {"user_languages": language.lower()}},
            )
            return True
        except Exception as e:
            print(f"Error adding user language: {e}")
            return False

    def get_user_languages(self, user_id):
        """Get user's language preferences"""
        try:
            user = self.find_user_by_id(user_id)
            if user:
                return user.get("user_languages", [])
            return []
        except Exception as e:
            print(f"Error getting user languages: {e}")
            return []
