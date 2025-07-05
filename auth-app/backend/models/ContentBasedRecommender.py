import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import (
    MultiLabelBinarizer,
    OneHotEncoder,
    MinMaxScaler,
    normalize,
)
from sklearn.decomposition import TruncatedSVD
from pymongo.collection import Collection
from scipy.sparse import hstack, csr_matrix
import faiss
import logging
import joblib
from database.mongodb_manager import mongodb_manager
import os
import gc
from tqdm import tqdm
import shutil
import psutil
from utils.user_language_detector import user_language_detector


class ContentBasedRecommender:
    def load_core_components(self):
        """Load core model components at startup"""
        try:
            # Load basic metadata
            required_files = ["book_ids.npy", "book_names.npy", "book_langs.npy"]
            if not all(os.path.exists(f) for f in required_files):
                return False

            # Load metadata
            self.book_ids = np.load("book_ids.npy", allow_pickle=True).tolist()
            self.book_names = np.load("book_names.npy", allow_pickle=True).tolist()
            book_langs = np.load("book_langs.npy", allow_pickle=True)

            # Rebuild mappings
            self.book_index = {book_id: i for i, book_id in enumerate(self.book_ids)}
            self.book_name_to_id = {
                name: book_id for name, book_id in zip(self.book_names, self.book_ids)
            }
            self.book_language_map = {
                book_id: lang for book_id, lang in zip(self.book_ids, book_langs)
            }

            # Load all transformers
            if not self._load_fitted_transformers():
                return False

            # Load English FAISS index
            english_index_file = "FAISS/faiss_index_english.index"
            english_ids_file = "book_ids_english.npy"

            if os.path.exists(english_index_file) and os.path.exists(english_ids_file):
                self.faiss_indices["english"] = {
                    "index": faiss.read_index(english_index_file),
                    "ids": np.load(english_ids_file, allow_pickle=True).tolist(),
                }
                self.loaded_languages.add("english")
                books_count = len(self.faiss_indices["english"]["ids"])

                # Mark as loaded since core components are ready
                self.model_loaded = True
                return True

            return False
        except Exception as e:
            self.logger.error(f"Error loading core components: {e}")
            return False

    def __init__(
        self,
        books_collection: Collection = None,
        interactions_collection: Collection = None,
        users_collection: Collection = None,
    ):
        # Get database collections
        if (
            books_collection is None
            or interactions_collection is None
            or users_collection is None
        ):
            self.books_collection = mongodb_manager.get_collection("book", "booksdata")
            self.interactions_collection = mongodb_manager.get_collection(
                "user_book_interactions", "user_auth_db"
            )
            self.users_collection = mongodb_manager.get_collection(
                "users", "user_auth_db"
            )
        else:
            self.books_collection = books_collection
            self.interactions_collection = interactions_collection
            self.users_collection = users_collection

        # CHANGED: All sparse extractors + added SVD
        self.tfidf_vectorizer = TfidfVectorizer(
            stop_words="english", max_features=10000
        )
        self.genre_binarizer = MultiLabelBinarizer()
        self.author_encoder = OneHotEncoder(
            sparse_output=True, handle_unknown="ignore"
        )  # FIXED: sparse_output=True
        self.year_scaler = MinMaxScaler()
        self.svd_reducer = TruncatedSVD(
            n_components=256, random_state=42
        )  # NEW: Dimensionality reduction

        # NEW: Model file paths for persistence
        self.model_files = {
            "tfidf": "models/tfidf_vectorizer.joblib",
            "genre": "models/genre_binarizer.joblib",
            "author": "models/author_encoder.joblib",
            "year": "models/year_scaler.joblib",
            "svd": "models/svd_reducer.joblib",
        }

        self.book_index = {}
        self.book_vectors = None
        self.book_ids = []
        self.book_names = []
        self.book_name_to_id = {}
        self.book_language_map = {}
        self.faiss_indices = {}  # per-language FAISS indices

        # Setup logging
        self.logger = logging.getLogger(__name__)

        # User-specific loading tracking
        self.current_user_id = None  # Track which user the model is loaded for
        self.loaded_languages = set()  # Track which languages are currently loaded

        # Vector cache for performance
        self.vector_cache = {}  # Cache book vectors to avoid recomputation

        # Initialize as not loaded - will load on first request
        self.model_loaded = False

    def train_model(self, chunk_size=10000):  # CHANGED: Default chunk size reduced
        """Train model with memory optimization"""
        try:
            # Check if we should retrain
            if not self._should_retrain():
                return self.load_model()

            # Check disk space

            # Create models and FAISS directories
            os.makedirs("models", exist_ok=True)
            os.makedirs("FAISS", exist_ok=True)

            # Count total books for planning
            total_books = self.books_collection.count_documents(
                {
                    "summary": {"$exists": True, "$ne": None, "$ne": ""},
                    "language_of_book": {"$exists": True, "$ne": None, "$ne": ""},
                }
            )

            if total_books == 0:
                return False

            total_chunks = (total_books + chunk_size - 1) // chunk_size

            # PHASE 1: Sample books and fit transformers
            if not self._fit_transformers_on_sample():
                return False

            # PHASE 2: Stream process all books in chunks
            return self._stream_process_all_books(chunk_size, total_chunks)

        except Exception as e:
            self.logger.error(f"Training error: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return False

    def _fit_transformers_on_sample(self, sample_size=75000):
        """PHASE 1: Fit all transformers on a representative sample"""
        # NEW: Separate fitting phase for better memory control
        try:
            # Use database aggregation for efficient sampling
            pipeline = [
                {
                    "$match": {
                        "summary": {"$exists": True, "$ne": None, "$ne": ""},
                        "language_of_book": {"$exists": True, "$ne": None, "$ne": ""},
                    }
                },
                {"$sample": {"size": sample_size}},
            ]

            sample_books = list(self.books_collection.aggregate(pipeline))
            if not sample_books:
                return False

            # Extract features for fitting
            summaries = [book.get("summary", "") for book in sample_books]
            genres = [
                self._parse_genres(book.get("genres", [])) for book in sample_books
            ]
            authors = self._prepare_authors(
                [book.get("author", "") for book in sample_books]
            )
            years = np.array([[book.get("year", 0)] for book in sample_books])

            # Fit all transformers
            self.tfidf_vectorizer.fit(summaries)

            self.genre_binarizer.fit(genres)

            self.author_encoder.fit(authors)

            self.year_scaler.fit(years)

            # Create combined features for SVD fitting
            summary_vecs = self.tfidf_vectorizer.transform(summaries)
            genre_vecs = csr_matrix(self.genre_binarizer.transform(genres) * 2.0)
            author_vecs = self.author_encoder.transform(authors) * 2.0  # Already sparse
            year_scaled = csr_matrix(self.year_scaler.transform(years))

            # MEMORY CRITICAL: Keep everything sparse until SVD
            combined_sparse = hstack(
                [summary_vecs, genre_vecs, author_vecs, year_scaled]
            ).tocsr()

            # Fit SVD on sparse matrix
            self.svd_reducer.fit(combined_sparse)

            # Clean up sample data
            del sample_books, summaries, genres, authors, years
            del summary_vecs, genre_vecs, author_vecs, year_scaled, combined_sparse
            gc.collect()

            # Save fitted transformers
            self._save_fitted_transformers()

            return True

        except Exception as e:
            self.logger.error(f"Error in transformer fitting phase: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return False

    def _prepare_authors(self, authors):
        """Prepare author data for OneHotEncoder"""
        # NEW: Consistent author data preparation
        prepared = []
        for author in authors:
            if isinstance(author, list):
                author_str = ", ".join(author) if author else ""
            else:
                author_str = str(author) if author else ""
            prepared.append([author_str])  # 2D structure required
        return prepared

    def _stream_process_all_books(self, chunk_size, total_chunks):
        """PHASE 2: Stream process all books in memory-safe chunks"""
        # NEW: Streaming processing with incremental FAISS building
        try:

            # Initialize aggregation structures
            all_book_ids = []
            all_book_names = []
            all_book_languages = []
            lang_faiss_builders = {}  # Per-language FAISS index builders

            # Stream process using database cursor
            cursor = self.books_collection.find(
                {
                    "summary": {"$exists": True, "$ne": None, "$ne": ""},
                    "language_of_book": {"$exists": True, "$ne": None, "$ne": ""},
                }
            ).batch_size(chunk_size)

            chunk_num = 0
            current_chunk = []

            for book in cursor:
                current_chunk.append(book)

                if len(current_chunk) >= chunk_size:
                    chunk_num += 1

                    # Process chunk with memory safety
                    if not self._process_chunk_optimized(
                        current_chunk,
                        chunk_num,
                        all_book_ids,
                        all_book_names,
                        all_book_languages,
                        lang_faiss_builders,
                    ):
                        return False

                    # Clear chunk and cleanup memory
                    current_chunk = []
                    gc.collect()

            # Process remaining books
            if current_chunk:
                chunk_num += 1
                self._process_chunk_optimized(
                    current_chunk,
                    chunk_num,
                    all_book_ids,
                    all_book_names,
                    all_book_languages,
                    lang_faiss_builders,
                )

            # Finalize FAISS indices
            return self._finalize_faiss_indices(
                all_book_ids, all_book_names, all_book_languages, lang_faiss_builders
            )

        except Exception as e:
            self.logger.error(f"Error in streaming processing: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return False

    def _process_chunk_optimized(
        self,
        chunk,
        chunk_num,
        all_book_ids,
        all_book_names,
        all_book_languages,
        lang_faiss_builders,
    ):
        """Process a single chunk with optimal memory usage"""
        # NEW: Memory-optimized chunk processing
        try:
            # Extract features (keeping sparse)
            summaries = [book.get("summary", "") for book in chunk]
            genres = [self._parse_genres(book.get("genres", [])) for book in chunk]
            authors = self._prepare_authors([book.get("author", "") for book in chunk])
            years = np.array([[book.get("year", 0)] for book in chunk])

            # Transform with fitted transformers (all sparse)
            summary_vecs = self.tfidf_vectorizer.transform(summaries)
            genre_vecs = csr_matrix(self.genre_binarizer.transform(genres) * 2.0)
            author_vecs = self.author_encoder.transform(authors) * 2.0  # Already sparse
            year_scaled = csr_matrix(self.year_scaler.transform(years))

            # MEMORY CRITICAL: Combine sparse features
            combined_sparse = hstack(
                [summary_vecs, genre_vecs, author_vecs, year_scaled]
            ).tocsr()

            # Apply SVD transformation (sparse to dense 256D)
            dense_256d = self.svd_reducer.transform(combined_sparse).astype("float32")

            # L2 normalize
            dense_256d = normalize(dense_256d, norm="l2", axis=1)

            # Clean up intermediate sparse matrices
            del summary_vecs, genre_vecs, author_vecs, year_scaled, combined_sparse
            gc.collect()

            # Process books for FAISS
            chunk_book_ids = []
            chunk_book_names = []
            chunk_book_languages = []

            for i, book in enumerate(chunk):
                book_id = book["_id"]
                book_name = book["name"]
                book_lang = book["language_of_book"]
                vector = dense_256d[i : i + 1]  # Single row as 2D array

                # Initialize language FAISS builder if needed
                if book_lang not in lang_faiss_builders:
                    lang_faiss_builders[book_lang] = {
                        "vectors": [],
                        "ids": [],
                        "dim": 256,
                    }

                # Add to language-specific builder
                lang_faiss_builders[book_lang]["vectors"].append(vector)
                lang_faiss_builders[book_lang]["ids"].append(book_id)

                # Add to global lists
                chunk_book_ids.append(book_id)
                chunk_book_names.append(book_name)
                chunk_book_languages.append(book_lang)

            # Extend global lists
            all_book_ids.extend(chunk_book_ids)
            all_book_names.extend(chunk_book_names)
            all_book_languages.extend(chunk_book_languages)

            # Clean up
            del dense_256d, chunk
            gc.collect()

            return True

        except Exception as e:
            self.logger.error(f"Error processing chunk {chunk_num}: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return False

    def _finalize_faiss_indices(
        self, all_book_ids, all_book_names, all_book_languages, lang_faiss_builders
    ):
        """Build final FAISS indices and save everything"""
        # NEW: Finalize FAISS indices with proper configuration
        try:

            # Save global metadata
            self.book_ids = all_book_ids
            self.book_names = all_book_names
            self.book_index = {book_id: i for i, book_id in enumerate(all_book_ids)}
            self.book_name_to_id = {
                name: book_id for name, book_id in zip(all_book_names, all_book_ids)
            }
            self.book_language_map = {
                book_id: lang for book_id, lang in zip(all_book_ids, all_book_languages)
            }

            # Save metadata to disk
            np.save("book_ids.npy", np.array(all_book_ids, dtype=object))
            np.save("book_names.npy", np.array(all_book_names, dtype=object))
            np.save("book_langs.npy", np.array(all_book_languages, dtype=object))

            # Build FAISS indices per language
            self.faiss_indices = {}
            for lang, builder in lang_faiss_builders.items():
                if not builder["vectors"]:
                    continue

                # Combine all vectors for this language
                lang_vectors = np.vstack(builder["vectors"]).astype("float32")
                num_vectors = len(lang_vectors)

                # Choose appropriate FAISS index type
                if num_vectors < 1000:
                    # Small dataset: use flat index
                    index = faiss.IndexFlatIP(256)
                else:
                    # Large dataset: use IVF index
                    nlist = max(int(np.sqrt(num_vectors)), 10)
                    quantizer = faiss.IndexFlatIP(256)
                    index = faiss.IndexIVFFlat(
                        quantizer, 256, nlist, faiss.METRIC_INNER_PRODUCT
                    )

                    # Train the index
                    index.train(lang_vectors)

                # Add vectors to index
                index.add(lang_vectors)

                # Save index and metadata
                index_file = f"FAISS/faiss_index_{lang}.index"
                ids_file = f"book_ids_{lang}.npy"

                faiss.write_index(index, index_file)
                np.save(ids_file, np.array(builder["ids"], dtype=object))

                # Clean up
                del lang_vectors, index
                gc.collect()

            # Load the completed model
            self.model_loaded = self.load_model()

            if self.model_loaded:
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"Error finalizing FAISS indices: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return False

    def _save_fitted_transformers(self):
        """Save all fitted transformers with joblib"""
        # NEW: Comprehensive model persistence
        try:

            joblib.dump(self.tfidf_vectorizer, self.model_files["tfidf"])
            joblib.dump(self.genre_binarizer, self.model_files["genre"])
            joblib.dump(self.author_encoder, self.model_files["author"])
            joblib.dump(self.year_scaler, self.model_files["year"])
            joblib.dump(self.svd_reducer, self.model_files["svd"])

        except Exception as e:
            self.logger.error(f"Error saving transformers: {e}")
            raise

    def _load_fitted_transformers(self):
        """Load all fitted transformers with joblib"""
        # NEW: Load saved transformers
        try:
            if not all(os.path.exists(path) for path in self.model_files.values()):
                return False

            self.tfidf_vectorizer = joblib.load(self.model_files["tfidf"])
            self.genre_binarizer = joblib.load(self.model_files["genre"])
            self.author_encoder = joblib.load(self.model_files["author"])
            self.year_scaler = joblib.load(self.model_files["year"])
            self.svd_reducer = joblib.load(self.model_files["svd"])

            return True

        except Exception as e:
            self.logger.error(f"Error loading transformers: {e}")
            return False

    def load_model(self, user_id=None, target_languages=None):
        """Load pre-trained model from disk with selective language loading"""
        try:
            # If core components not loaded yet, load them first
            if not self.model_loaded and not self.load_core_components():
                return False

            # OPTIMIZED: Selective language loading
            if target_languages is None:
                if user_id:
                    # Detect user's preferred languages
                    target_languages = user_language_detector.get_user_languages(
                        user_id, max_languages=3
                    )
                else:
                    # Default: load only English for anonymous users
                    target_languages = {"english"}

            # Load only target language FAISS indices
            self.faiss_indices = {}
            total_books_loaded = 0

            for lang in target_languages:
                index_file = f"FAISS/faiss_index_{lang}.index"
                ids_file = f"book_ids_{lang}.npy"

                if os.path.exists(index_file) and os.path.exists(ids_file):
                    self.faiss_indices[lang] = {
                        "index": faiss.read_index(index_file),
                        "ids": np.load(ids_file, allow_pickle=True).tolist(),
                    }
                    books_count = len(self.faiss_indices[lang]["ids"])
                    total_books_loaded += books_count

            # Always ensure English is loaded as fallback
            if "english" not in self.faiss_indices:
                english_index_file = "FAISS/faiss_index_english.index"
                english_ids_file = "book_ids_english.npy"

                if os.path.exists(english_index_file) and os.path.exists(
                    english_ids_file
                ):
                    self.faiss_indices["english"] = {
                        "index": faiss.read_index(english_index_file),
                        "ids": np.load(english_ids_file, allow_pickle=True).tolist(),
                    }
                    books_count = len(self.faiss_indices["english"]["ids"])
                    total_books_loaded += books_count

            # Update tracking
            if target_languages:
                self.loaded_languages = target_languages

            return True

        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return False

    def get_similar_books_for_user(self, user_id, limit=10, alternative=False):
        """Get similar books using optimized FAISS search with selective language loading"""
        import time

        start_time = time.time()
        try:

            # TIMING: User language detection
            step_start = time.time()
            user_languages = user_language_detector.get_user_languages(
                user_id, max_languages=3
            )

            # FIXED: More intelligent reload logic to avoid unnecessary reloading
            needs_reload = False

            # Only reload if truly necessary
            if not self.model_loaded:
                needs_reload = True
            elif not self.faiss_indices:
                needs_reload = True
            elif not user_languages.issubset(self.loaded_languages):
                # Only reload if user needs languages we don't have
                missing_languages = user_languages - self.loaded_languages
                if missing_languages:
                    needs_reload = True

            # Update tracking regardless of reload
            if self.model_loaded:
                self.current_user_id = user_id
                if user_languages:
                    self.loaded_languages.update(user_languages)

            if needs_reload:
                # TIMING: Model loading (this might be the bottleneck!)
                step_start = time.time()
                if not self.load_model(user_id=user_id):
                    return []
                self.model_loaded = True
                self.current_user_id = user_id
                self.loaded_languages = user_languages
            else:
                # Still update tracking for cached model
                self.current_user_id = user_id
                if user_languages:
                    self.loaded_languages.update(user_languages)

            # TIMING: Database query for user's liked book (recent or alternative)
            step_start = time.time()
            if alternative:
                base_book_name = self._get_alternative_liked_book(user_id)
            else:
                base_book_name = self._get_most_recent_liked_book(user_id)

            if not base_book_name or base_book_name not in self.book_name_to_id:
                self.logger.warning(f"No recent liked book found for user {user_id}")
                return []

            base_book_id = self.book_name_to_id[base_book_name]
            if base_book_id not in self.book_index:
                return []

            if not user_languages:
                user_languages = {"english"}

            # Get book's language and check availability
            base_lang = self.book_language_map.get(base_book_id)
            if not base_lang or base_lang not in self.faiss_indices:
                if "english" in self.faiss_indices:
                    base_lang = "english"
                else:
                    return []

            # TIMING: Get base book info from database
            step_start = time.time()
            base_book = self._get_book_info(base_book_id)

            if not base_book:
                return []

            # TIMING: Transform book to vector (this might be slow!)
            step_start = time.time()
            base_vector = self._transform_single_book_to_vector(base_book)

            if base_vector is None:
                return []

            from models.user_book_interaction import UserBookInteraction

            interaction_model = UserBookInteraction()
            user_interacted_books = set(
                interaction_model.get_user_interacted_book_names(user_id)
            )

            # TIMING: FAISS search
            step_start = time.time()
            index = self.faiss_indices[base_lang]["index"]
            all_ids = self.faiss_indices[base_lang]["ids"]

            D, I = index.search(
                base_vector.reshape(1, -1), limit + len(user_interacted_books)
            )

            # TIMING: Gather candidate book IDs
            step_start = time.time()
            candidate_book_ids = {
                all_ids[i]
                for i in I[0]
                if i < len(all_ids) and all_ids[i] != base_book_id
            }

            # TIMING: Batch database fetch (this might be slow!)
            step_start = time.time()
            retrieved_books = self._get_books_info_by_ids(candidate_book_ids)

            # TIMING: Build recommendations response
            step_start = time.time()
            recommendations = []
            for i, similarity_score in zip(I[0], D[0]):
                if i >= len(all_ids):
                    continue

                book_id = all_ids[i]
                if book_id == base_book_id:
                    continue

                # CHANGED HERE: fetch from in-memory batch
                book = retrieved_books.get(book_id)  # CHANGED HERE
                if book["name"] in user_interacted_books:
                    continue
                if book:
                    recommendations.append(
                        {
                            "_id": str(book["_id"]),
                            "name": book.get("name"),
                            "summary": book.get("summary"),
                            "genres": book.get("genres", []),
                            "author": book.get("author"),
                            "language": book.get("language_of_book"),
                            "star_rating": book.get("star_rating"),
                            "num_ratings": book.get("num_ratings", 0),
                            "similarity_score": float(similarity_score),
                            "recommendation_score": float(similarity_score) * 100,
                            "algorithm": "content_based_faiss_optimized",
                            "based_on_book": base_book_name,
                            "confidence": min(float(similarity_score), 1.0),
                        }
                    )

                if len(recommendations) >= limit:
                    break

            return recommendations

        except Exception as e:
            self.logger.error(f"Error getting similar books for user {user_id}: {e}")
            return []

    def _transform_single_book_to_vector(self, book):
        """Transform a single book to 256D vector using fitted transformers with caching"""
        try:
            # Check cache first for performance
            book_id = book.get("_id")
            if book_id and book_id in self.vector_cache:
                return self.vector_cache[book_id]
            # Extract features
            summary = book.get("summary", "")
            genres = self._parse_genres(book.get("genres", []))
            author = self._prepare_authors([book.get("author", "")])
            year = np.array([[book.get("year", 0)]])

            # Transform with fitted transformers (keeping sparse)
            summary_vec = self.tfidf_vectorizer.transform([summary])
            genre_vec = csr_matrix(self.genre_binarizer.transform([genres]) * 2.0)
            author_vec = self.author_encoder.transform(author) * 2.0
            year_scaled = csr_matrix(self.year_scaler.transform(year))

            # Combine sparse features
            combined_sparse = hstack(
                [summary_vec, genre_vec, author_vec, year_scaled]
            ).tocsr()

            # Apply SVD to get 256D dense vector
            dense_256d = self.svd_reducer.transform(combined_sparse).astype("float32")

            # L2 normalize
            normalized_vector = normalize(dense_256d, norm="l2", axis=1)[0]

            # Cache the result for future use
            if book_id:
                self.vector_cache[book_id] = normalized_vector
                # Limit cache size to prevent memory bloat
                if len(self.vector_cache) > 1000:
                    # Remove oldest entries (simple FIFO)
                    oldest_keys = list(self.vector_cache.keys())[:100]
                    for key in oldest_keys:
                        del self.vector_cache[key]

            return normalized_vector

        except Exception as e:
            self.logger.error(f"Error transforming single book to vector: {e}")
            return None

    # Keep existing utility methods unchanged
    def _parse_genres(self, genres):
        if isinstance(genres, list):
            return genres
        elif isinstance(genres, str):
            return [g.strip() for g in genres.split(",") if g.strip()]
        return []

    def _get_book_info(self, book_id):
        try:
            return self.books_collection.find_one({"_id": book_id})
        except Exception as e:
            self.logger.error(f"Error getting book info for {book_id}: {e}")
            return None

    def _get_most_recent_liked_book(self, user_id):
        try:
            from bson import ObjectId

            user_object_id = ObjectId(user_id) if isinstance(user_id, str) else user_id

            recent = self.interactions_collection.find_one(
                {"user_id": user_object_id, "action": "like"}, sort=[("timestamp", -1)]
            )
            return recent["book_name"] if recent else None
        except Exception as e:
            self.logger.error(
                f"Error getting recent liked book for user {user_id}: {e}"
            )
            return None

    def _get_alternative_liked_book(self, user_id):
        """Get a different random liked book (not the most recent one)"""
        try:
            from bson import ObjectId
            import random

            user_object_id = ObjectId(user_id) if isinstance(user_id, str) else user_id

            # Get all liked books except the most recent one
            liked_books = list(
                self.interactions_collection.find(
                    {"user_id": user_object_id, "action": "like"},
                    sort=[("timestamp", -1)],
                ).limit(20)
            )  # Get up to 20 recent likes to choose from

            if len(liked_books) <= 1:
                # If user has only 1 or no liked books, return the most recent (or None)
                return liked_books[0]["book_name"] if liked_books else None

            # Skip the first (most recent) and randomly choose from the rest
            alternative_books = liked_books[1:]
            selected_book = random.choice(alternative_books)

            return selected_book["book_name"]

        except Exception as e:
            self.logger.error(
                f"Error getting alternative liked book for user {user_id}: {e}"
            )
            # Fallback to most recent if alternative fails
            return self._get_most_recent_liked_book(user_id)

    def _get_books_info_by_ids(self, book_ids):
        """Batch-fetch books by their IDs"""
        books_cursor = self.books_collection.find({"_id": {"$in": list(book_ids)}})
        return {book["_id"]: book for book in books_cursor}

    def _should_retrain(self):
        """Check if model files exist and are recent"""
        try:
            # Check if main files exist
            required_files = ["book_ids.npy", "book_names.npy", "book_langs.npy"]
            if not all(os.path.exists(f) for f in required_files):
                return True

            # Check transformer files
            if not all(os.path.exists(path) for path in self.model_files.values()):
                return True

            # Check if any FAISS index files exist
            faiss_dir = "FAISS"
            if os.path.exists(faiss_dir):
                faiss_files = [
                    f
                    for f in os.listdir(faiss_dir)
                    if f.startswith("faiss_index_") and f.endswith(".index")
                ]
            else:
                faiss_files = []
            if not faiss_files:
                return True

            return False

        except Exception as e:
            self.logger.warning(f"Error checking model files: {e}")
            return True

    def get_based_on_likes_recommendations(
        self, user_id, liked_books, disliked_books, limit=10
    ):
        """
        Get content-based recommendations based on average profile of all user's liked books
        vs disliked books pattern. Uses existing content-based algorithm.
        """
        import time

        start_time = time.time()
        try:

            # TIMING: User language detection and model loading
            step_start = time.time()
            user_languages = user_language_detector.get_user_languages(
                user_id, max_languages=3
            )

            # Check if model needs loading/reloading
            if not self.model_loaded or not user_languages.issubset(
                self.loaded_languages
            ):
                if not self.load_model(user_id=user_id):
                    return {
                        "recommendations": [],
                        "count": 0,
                        "explanation": "Model loading failed",
                    }
                self.model_loaded = True
                self.current_user_id = user_id
                self.loaded_languages = user_languages

            # Get book names from liked books
            liked_book_names = [book["book_name"] for book in liked_books]
            disliked_book_names = (
                [book["book_name"] for book in disliked_books] if disliked_books else []
            )

            if not liked_book_names:
                return {
                    "recommendations": [],
                    "count": 0,
                    "explanation": "No liked books found to analyze",
                }

            # TIMING: Fetch liked book details
            step_start = time.time()
            liked_book_ids = []
            for book_name in liked_book_names:
                if book_name in self.book_name_to_id:
                    book_id = self.book_name_to_id[book_name]
                    if book_id in self.book_index:
                        liked_book_ids.append(book_id)

            if not liked_book_ids:
                return {
                    "recommendations": [],
                    "count": 0,
                    "explanation": "No liked books found in content model",
                }

            # Batch fetch liked books info
            liked_books_info = self._get_books_info_by_ids(liked_book_ids)

            # TIMING: Transform liked books to vectors and create average profile
            step_start = time.time()
            liked_vectors = []
            valid_liked_books = []

            for book_id, book_info in liked_books_info.items():
                vector = self._transform_single_book_to_vector(book_info)
                if vector is not None:
                    liked_vectors.append(vector)
                    valid_liked_books.append(book_info)

            if not liked_vectors:
                return {
                    "recommendations": [],
                    "count": 0,
                    "explanation": "Could not process liked books for content analysis",
                }

            # Create average "like profile" vector
            like_profile_vector = np.mean(liked_vectors, axis=0).astype("float32")
            like_profile_vector = normalize(
                like_profile_vector.reshape(1, -1), norm="l2", axis=1
            )[0]

            # If we have disliked books, create "dislike profile" and adjust
            if disliked_book_names:
                step_start = time.time()
                disliked_book_ids = []
                for book_name in disliked_book_names:
                    if book_name in self.book_name_to_id:
                        book_id = self.book_name_to_id[book_name]
                        if book_id in self.book_index:
                            disliked_book_ids.append(book_id)

                if disliked_book_ids:
                    disliked_books_info = self._get_books_info_by_ids(disliked_book_ids)
                    disliked_vectors = []

                    for book_id, book_info in disliked_books_info.items():
                        vector = self._transform_single_book_to_vector(book_info)
                        if vector is not None:
                            disliked_vectors.append(vector)

                    if disliked_vectors:
                        # Create average "dislike profile" vector
                        dislike_profile_vector = np.mean(
                            disliked_vectors, axis=0
                        ).astype("float32")
                        dislike_profile_vector = normalize(
                            dislike_profile_vector.reshape(1, -1), norm="l2", axis=1
                        )[0]

                        # Adjust like profile to move away from dislike profile
                        # Enhanced like profile = like_profile + (like_profile - dislike_profile) * 0.3
                        difference_vector = like_profile_vector - dislike_profile_vector
                        like_profile_vector = like_profile_vector + (
                            difference_vector * 0.3
                        )
                        like_profile_vector = normalize(
                            like_profile_vector.reshape(1, -1), norm="l2", axis=1
                        )[0]

            # TIMING: Search across user's preferred languages
            step_start = time.time()
            all_candidates = []

            # Search in user's preferred languages
            search_languages = user_languages if user_languages else {"english"}
            for lang in search_languages:
                if lang in self.faiss_indices:
                    index = self.faiss_indices[lang]["index"]
                    all_ids = self.faiss_indices[lang]["ids"]

                    # Search for similar books (get more candidates to filter)
                    search_limit = min(limit * 3, len(all_ids))
                    D, I = index.search(
                        like_profile_vector.reshape(1, -1), search_limit
                    )

                    # Add candidates with language info
                    for i, similarity_score in zip(I[0], D[0]):
                        if i < len(all_ids):
                            book_id = all_ids[i]
                            # Skip if this was one of the liked books
                            if book_id not in liked_book_ids:
                                all_candidates.append(
                                    {
                                        "book_id": book_id,
                                        "similarity_score": float(similarity_score),
                                        "language": lang,
                                    }
                                )

            # Sort all candidates by similarity score
            all_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
            top_candidates = all_candidates[
                : limit * 2
            ]  # Get extra candidates for filtering

            # TIMING: Fetch candidate book details
            step_start = time.time()
            candidate_book_ids = [c["book_id"] for c in top_candidates]
            candidate_books_info = self._get_books_info_by_ids(candidate_book_ids)

            # TIMING: Build final recommendations
            step_start = time.time()
            recommendations = []
            processed_books = set()  # Avoid duplicates

            for candidate in top_candidates:
                if len(recommendations) >= limit:
                    break

                book_id = candidate["book_id"]
                book_info = candidate_books_info.get(book_id)

                if book_info and book_id not in processed_books:
                    processed_books.add(book_id)

                    similarity_score = candidate["similarity_score"]
                    recommendation_score = similarity_score * 100

                    recommendations.append(
                        {
                            "_id": str(book_info["_id"]),
                            "name": book_info.get("name"),
                            "author": book_info.get("author"),
                            "genres": book_info.get("genres", []),
                            "star_rating": book_info.get("star_rating"),
                            "num_ratings": book_info.get("num_ratings", 0),
                            "language": book_info.get("language_of_book"),
                            "similarity_score": similarity_score,
                            "recommendation_score": recommendation_score,
                            "algorithm": "content_based_likes_profile",
                            "confidence": min(similarity_score, 1.0),
                            "based_on_books_count": len(valid_liked_books),
                            "disliked_books_count": len(disliked_book_names),
                        }
                    )

            # Create explanation
            explanation = (
                f"Based on content analysis of {len(valid_liked_books)} books you liked"
            )
            if disliked_book_names:
                explanation += f" and {len(disliked_book_names)} books you disliked"

            result = {
                "recommendations": recommendations,
                "count": len(recommendations),
                "explanation": explanation,
                "processing_time": time.time() - start_time,
                "liked_books_analyzed": len(valid_liked_books),
                "search_languages": list(search_languages),
            }

            return result

        except Exception as e:
            self.logger.error(f"Error in get_based_on_likes_recommendations: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return {
                "recommendations": [],
                "count": 0,
                "explanation": f"Error: {str(e)}",
                "processing_time": (
                    time.time() - start_time if "start_time" in locals() else 0
                ),
            }


# Global instance
content_based_recommender = ContentBasedRecommender()
