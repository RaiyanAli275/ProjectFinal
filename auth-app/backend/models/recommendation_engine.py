import numpy as np
import pandas as pd
import scipy.sparse as sparse
from implicit.als import AlternatingLeastSquares
from pymongo import MongoClient
import pickle
import os
from datetime import datetime, timedelta
import logging
from bson import ObjectId
from sklearn.metrics.pairwise import cosine_similarity
from services.cache_service import cache_service


class ALSRecommendationEngine:
    def __init__(self):
        self.client = MongoClient(
            "mongodb+srv://alirayan:Ali212153266@cluster0.ksubn7k.mongodb.net/booksdata?retryWrites=true&w=majority"
        )
        self.db = self.client["booksdata"]
        self.users_db = self.client["user_auth_db"]

        # Collections
        self.books_collection = self.db["book"]
        self.interactions_collection = self.users_db["user_book_interactions"]
        self.cache_collection = self.users_db["recommendation_cache"]
        self.users = self.users_db["users"]

        # Model parameters
        self.model = None
        self.user_item_matrix = None
        self.user_mapping = {}  # user_id -> matrix_index
        self.item_mapping = {}  # book_name -> matrix_index
        self.reverse_item_mapping = {}  # matrix_index -> book_name
        self.reverse_user_mapping = {}  # matrix_index -> user_id

        # Model file path
        self.model_path = "als_model.pkl"
        self.mappings_path = "als_mappings.pkl"

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def build_interaction_matrix(self):
        """Build user-item interaction matrix from MongoDB data"""
        try:
            # Get all interactions
            interactions = list(self.interactions_collection.find({}))

            if not interactions:
                return False

            # Convert to DataFrame
            df = pd.DataFrame(interactions)

            # Ensure user_id is ObjectId
            df["user_id"] = df["user_id"].apply(
                lambda x: ObjectId(x) if isinstance(x, str) else x
            )

            # Map actions to weights
            weight_map = {
                "like": 3.0,  # Strong positive signal
                "dislike": 0.1,  # Very weak signal (don't completely exclude)
                # 'search': 1.0     # Implicit interest signal
            }

            df["weight"] = df["action"].map(weight_map).fillna(1.0)

            # Create mappings
            unique_users = df["user_id"].unique()
            unique_books = df["book_name"].unique()

            self.user_mapping = {user: idx for idx, user in enumerate(unique_users)}
            self.item_mapping = {book: idx for idx, book in enumerate(unique_books)}
            self.reverse_user_mapping = {
                idx: user for user, idx in self.user_mapping.items()
            }
            self.reverse_item_mapping = {
                idx: book for book, idx in self.item_mapping.items()
            }

            # Map to matrix indices
            df["user_idx"] = df["user_id"].map(self.user_mapping)
            df["item_idx"] = df["book_name"].map(self.item_mapping)

            # Group by user-item pairs and sum weights (handle multiple interactions)
            interaction_df = (
                df.groupby(["user_idx", "item_idx"])["weight"].sum().reset_index()
            )

            # Create sparse matrix
            self.user_item_matrix = sparse.csr_matrix(
                (
                    interaction_df["weight"],
                    (interaction_df["user_idx"], interaction_df["item_idx"]),
                ),
                shape=(len(unique_users), len(unique_books)),
            )

            return True

        except Exception as e:
            self.logger.error(f"Error building interaction matrix: {e}")
            return False

    def train_model(self, factors=64, regularization=0.1, iterations=50, alpha=40):
        """Train the ALS model"""
        try:

            # Initialize ALS model
            self.model = AlternatingLeastSquares(
                factors=factors,
                regularization=regularization,
                iterations=iterations,
                alpha=alpha,  # Confidence parameter for implicit feedback
                random_state=42,
            )

            # Train the model
            self.model.fit(self.user_item_matrix)

            # Save model and mappings
            self._save_model()

            return True

        except Exception as e:
            self.logger.error(f"Error training model: {e}")
            return False

    def _get_user_languages(self, user_id):
        """Get user's preferred languages based on their book interactions"""
        try:
            from models.user import User

            user_model = User()

            # Get user's languages from their profile
            user_languages = user_model.get_user_languages(user_id)

            # Convert to lowercase for easier matching
            user_languages_lower = [lang.lower().strip() for lang in user_languages]

            return user_languages_lower

        except Exception as e:
            self.logger.error(f"Error getting user languages for user {user_id}: {e}")
            return []

    def _meets_language_requirement(self, book_info, user_languages):
        """Check if book is in one of the user's preferred languages (optimized)"""
        if not user_languages:
            return True  # No language filter if user has no language preferences

        try:
            # Check if language is already in book_info to avoid extra DB call
            book_language = book_info.get("language_of_book")
            if not book_language:
                # If we can't determine the book's language, allow it (fallback for performance)
                return True

            book_language_lower = book_language.lower().strip()

            # Quick check - if any user language is in book language or vice versa
            for user_lang in user_languages:
                if self._languages_match(book_language_lower, user_lang):
                    return True

            return False

        except Exception as e:
            self.logger.error(
                f"Error checking language requirement for book '{book_info.get('name', '')}': {e}"
            )
            return True  # Allow book if there's an error (fallback)

    def _languages_match(self, book_language, user_language):
        """Check if book language matches user preference with smart matching"""
        book_language = book_language.lower().strip()
        user_language = user_language.lower().strip()

        # Exact match
        if book_language == user_language:
            return True

        # Handle common language variations and synonyms
        language_mappings = {
            "english": ["en", "eng", "en-us", "en-gb", "english"],
            "spanish": [
                "es",
                "esp",
                "español",
                "castellano",
                "es-es",
                "es-mx",
                "spanish",
            ],
            "french": ["fr", "français", "francais", "fr-fr", "french"],
            "german": ["de", "deutsch", "german", "de-de"],
            "italian": ["it", "italiano", "it-it", "italian"],
            "portuguese": [
                "pt",
                "português",
                "portugues",
                "pt-br",
                "pt-pt",
                "portuguese",
            ],
            "chinese": ["zh", "chinese", "mandarin", "zh-cn", "zh-tw"],
            "japanese": ["ja", "japanese", "jp", "ja-jp"],
            "korean": ["ko", "korean", "kr", "ko-kr"],
            "russian": ["ru", "russian", "русский", "ru-ru"],
            "arabic": ["ar", "arabic", "العربية", "ar-sa", "عربي", "عربية"],
            "hindi": ["hi", "hindi", "हिन्दी", "hi-in"],
        }

        # Check if either language contains the other (partial match)
        if user_language in book_language or book_language in user_language:
            return True

        # Check language mappings
        for main_lang, alternatives in language_mappings.items():
            if (
                (user_language == main_lang and book_language in alternatives)
                or (book_language == main_lang and user_language in alternatives)
                or (user_language in alternatives and book_language in alternatives)
            ):
                return True

        return False

    def _get_book_info(self, book_name):
        """Get detailed book information"""
        try:
            book = self.books_collection.find_one({"name": book_name})
            return self._format_book_info(book) if book else None
        except Exception as e:
            self.logger.error(f"Error getting book info for {book_name}: {e}")
            return None

    def _format_book_info(self, book):
        """Format book information for API response"""
        if not book:
            return None

        # Format authors and genres
        author = book.get("author", "Unknown Author")
        if isinstance(author, list):
            author = ", ".join(author)

        genres = book.get("genres", "")
        if isinstance(genres, list):
            genres = ", ".join(genres)

        return {
            "name": book.get("name", ""),
            "author": author,
            "genres": genres,
            "star_rating": book.get("star_rating"),
            "num_ratings": book.get("num_ratings", 0),
            "language_of_book": book.get("language_of_book"),
            "popularity_score": book.get("popularity_score", 0),
        }

    def _save_model(self):
        """Save trained model and mappings to disk"""
        try:
            # Save model
            with open(self.model_path, "wb") as f:
                pickle.dump(self.model, f)

            # Save mappings
            mappings = {
                "user_mapping": self.user_mapping,
                "item_mapping": self.item_mapping,
                "reverse_user_mapping": self.reverse_user_mapping,
                "reverse_item_mapping": self.reverse_item_mapping,
            }

            with open(self.mappings_path, "wb") as f:
                pickle.dump(mappings, f)

        except Exception as e:
            self.logger.error(f"Error saving model: {e}")

    def _load_model(self):
        """Load trained model and mappings from disk"""
        try:
            if not os.path.exists(self.model_path) or not os.path.exists(
                self.mappings_path
            ):
                return False

            # Load model
            with open(self.model_path, "rb") as f:
                self.model = pickle.load(f)

            # Load mappings
            with open(self.mappings_path, "rb") as f:
                mappings = pickle.load(f)
                self.user_mapping = mappings["user_mapping"]
                self.item_mapping = mappings["item_mapping"]
                self.reverse_user_mapping = mappings["reverse_user_mapping"]
                self.reverse_item_mapping = mappings["reverse_item_mapping"]

            return True

        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return False

    def force_reload_model(self):
        """Force reload the model from disk (used after training)"""
        try:

            # Clear current model state
            self.model = None
            self.user_item_matrix = None
            self.user_mapping = {}
            self.item_mapping = {}
            self.reverse_item_mapping = {}
            self.reverse_user_mapping = {}

            # Attempt to load the updated model
            if self._load_model():
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"Error force reloading model: {e}")
            return False

    def clear_all_recommendation_caches(self):
        """Clear all recommendation caches from MongoDB and Redis"""
        try:
            # Clear MongoDB recommendation cache
            mongo_deleted = self.cache_collection.delete_many({})

            # Clear Redis caches via cache service
            from services.cache_service import cache_service

            # Clear Redis recommendation caches by pattern
            if cache_service.redis.is_available():
                client = cache_service.redis.get_client()

                # Clear all recommendation patterns
                patterns = [
                    "recommendations:*",
                    "based_on_likes:*",
                    "continue_reading:*",
                    "popular_books:*",
                    "collaborative_filtering:*",
                    "content_based:*",
                ]

                total_cleared = 0
                for pattern in patterns:
                    try:
                        keys = client.keys(pattern)
                        if keys:
                            client.delete(*keys)
                            total_cleared += len(keys)
                    except Exception as e:
                        self.logger.warning(f"Error clearing pattern {pattern}: {e}")

            return True

        except Exception as e:
            self.logger.error(f"Error clearing recommendation caches: {e}")
            return False

    def get_cached_recommendations(self, user_id):
        """Get cached recommendations if still valid"""
        try:
            cache = self.cache_collection.find_one(
                {"user_id": user_id, "expires_at": {"$gt": datetime.utcnow()}}
            )

            return cache["recommendations"] if cache else None

        except Exception as e:
            self.logger.error(f"Error getting cached recommendations: {e}")
            return None

    def get_enhanced_ubcf_recommendations(self, user_id, num_recommendations=10):
        """
        Enhanced User-Based Collaborative Filtering:
        1. Get ALL books from most similar user that target user hasn't interacted with
        2. If need more, get from 2nd most similar user
        3. Continue until we have enough recommendations
        Pure collaborative filtering based on user similarity hierarchy.
        """
        try:

            # Check cache first
            cached_recommendations = cache_service.get_cached_recommendations(
                user_id, algorithm="enhanced_ubcf"
            )
            if cached_recommendations:
                return cached_recommendations[:num_recommendations]

            # Convert string ID to ObjectId if needed
            user_object_id = ObjectId(user_id) if isinstance(user_id, str) else user_id

            # check if the model is loaded in memory ///// before try anithing else
            if self.model is None:
                # Model is NOT loaded yet
                # load the model
                self._load_model()

            user_mapping = self.user_mapping.keys()

            # Check if user exists in training data
            if user_object_id not in user_mapping:
                if not self._retrain_for_new_user(user_id):
                    return []

            # Get similar users from MongoDB
            similar_users = self.users_db["user_similarities"].find_one(
                {"user_id": user_object_id}, {"similar_users": 1, "similarities": 1}
            )

            if not similar_users:
                return []

            similar_user_ids = similar_users.get("similar_users", [])
            similarity_scores = similar_users.get("similarities", [])

            sorted_user_ids = []

            for uid, score in zip(similar_user_ids, similarity_scores):
                if score < 0.5:
                    continue
                sorted_user_ids.append(uid)

            # Import interaction model to get detailed interactions
            from models.user_book_interaction import UserBookInteraction

            interaction_model = UserBookInteraction()

            # Get books user has already interacted with
            user_interacted_books = set(
                interaction_model.get_user_interacted_book_names(user_id)
            )

            # Get target user's languages
            user_languages = self._get_user_languages(user_id)

            recommendations = []

            # Process users in similarity order
            for rank, similar_user_id in enumerate(sorted_user_ids):
                if len(recommendations) >= num_recommendations:
                    break

                # Get this similar user's liked books
                similar_user_books = interaction_model.get_user_interactions(
                    similar_user_id, action="like", limit=100
                )
                liked_books = []
                book_info_map = {}
                for book in similar_user_books:
                    book_name = book["book_name"]
                    if book_name in user_interacted_books:
                        continue
                    if book_name not in book_info_map:
                        info = self._get_book_info(book_name)
                        if info:
                            book_info_map[book_name] = info
                            book["popularity_score"] = info.get("popularity_score", 0)
                            liked_books.append(book)
                liked_books.sort(
                    key=lambda x: x.get("popularity_score", 0), reverse=True
                )

                # Add books that target user hasn't interacted with
                books_added_from_this_user = 0
                for book_interaction in liked_books:
                    if len(recommendations) >= num_recommendations:
                        break

                    book_name = book_interaction["book_name"]

                    # Check if we already added this book
                    if any(rec["name"] == book_name for rec in recommendations):
                        continue

                    book_info = book_info_map[book_name]

                    # Check if the user can read the book
                    if not self._meets_language_requirement(book_info, user_languages):
                        continue  # Skip books in languages the user can't read

                    recommendations.append(book_info)
                    books_added_from_this_user += 1

                # If we have enough recommendations, stop
                if len(recommendations) >= num_recommendations:
                    break
            # Sort by recommendation score (highest similarity first)
            # Take only the requested number
            final_recommendations = recommendations[:num_recommendations]

            # Cache the results
            if final_recommendations:
                cache_service.cache_user_recommendations(
                    user_id, final_recommendations, algorithm="enhanced_ubcf"
                )

            return final_recommendations

        except Exception as e:
            self.logger.error(f"Error in enhanced UBCF for user {user_id}: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return []

    def save_user_similarities(self, top_k=10):
        if self.model is None or self.user_mapping is None:
            return False

        try:
            user_ids_cursor = self.users.find({}, {"_id": 1})
            registered_user_ids = [doc["_id"] for doc in user_ids_cursor]
            reverse_user_mapping1 = {v: k for k, v in self.user_mapping.items()}

            # Map to indices
            registered_user_indices = [
                self.user_mapping[user_id]
                for user_id in registered_user_ids
                if user_id in self.user_mapping
            ]

            user_factors = self.model.user_factors  # shape: (num_users, num_factors)
            similarity_matrix = cosine_similarity(user_factors)

            top_k_similar_users = []
            for user_idx in registered_user_indices:
                sims = similarity_matrix[user_idx]
                top_indices = np.argsort(sims)[::-1][1 : top_k + 1]  # exclude self
                top_scores = [float(sims[i]) for i in top_indices]
                top_k_similar_users.append(
                    {
                        "user_id": reverse_user_mapping1[user_idx],
                        "similar_users": [
                            reverse_user_mapping1[i] for i in top_indices
                        ],
                        "similarities": top_scores,
                    }
                )

            collection = self.users_db["user_similarities"]
            collection.delete_many({})
            collection.insert_many(top_k_similar_users)

            return True

        except Exception as e:
            self.logger.info(f"❌ Error computing/saving user similarities: {e}")
            return False

    def _retrain_for_new_user(self, user_id):
        """
        Simple retraining for new user using external train_model.py script.
        Returns True if successful, False otherwise.
        """
        try:
            from models.user_book_interaction import UserBookInteraction

            interaction_model = UserBookInteraction()
            interaction_count = interaction_model.get_user_interaction_count(user_id)
            if interaction_count == 0:
                return False
            import subprocess, sys, os

            # This works from any subdirectory in backend/
            script_dir = os.path.dirname(os.path.abspath(__file__))
            backend_dir = os.path.dirname(script_dir)  # models/ -> backend/
            train_script_path = os.path.join(backend_dir, "train_model.py")

            # Verify the file exists
            if not os.path.exists(train_script_path):
                raise FileNotFoundError(
                    f"Training script not found at {train_script_path}"
                )

            # Use in subprocess
            result = subprocess.run(
                [sys.executable, train_script_path], cwd=backend_dir
            )
            if result.returncode == 0:
                # Reload the model since train_model.py has updated it
                if not self._load_model():
                    return False
                return True
            else:
                return False
        except Exception as e:
            self.logger.error(f"Error in retraining: {e}")
            return False


# Global instance
recommendation_engine = ALSRecommendationEngine()
