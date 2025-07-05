#!/usr/bin/env python3

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from models.ContentBasedRecommender import content_based_recommender


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("content_model_training.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def train_content_based_model():
    """Train the content-based recommendation model"""

    print("🧠 Training Content-Based Recommendation Model")
    print("=" * 60)

    try:
        # Train the model
        print("\n📚 Starting model training...")
        success = content_based_recommender.train_model()

        if success:
            print("✅ Content-based model training completed successfully!")

            # Get some stats about the trained model
            if (
                hasattr(content_based_recommender, "book_vectors")
                and content_based_recommender.book_vectors is not None
            ):
                print(f"\n📊 Model Statistics:")
                print(f"   📖 Total books: {len(content_based_recommender.book_ids)}")
                print(
                    f"   🔢 Feature dimensions: {content_based_recommender.book_vectors.shape[1]}"
                )
                print(
                    f"   🌐 Languages supported: {len(content_based_recommender.faiss_indices)}"
                )

                for lang, data in content_based_recommender.faiss_indices.items():
                    print(f"      - {lang}: {len(data['ids'])} books")

            print(
                "\n🎯 The model is now ready to generate content-based recommendations!"
            )
            print("   Users who like books will get similar recommendations based on:")
            print("   - Book summaries (TF-IDF)")
            print("   - Genres (weighted 2x)")
            print("   - Authors (weighted 2x)")
            print("   - Publication years")

        else:
            print("❌ Model training failed!")
            print("   Check the logs for more details.")

    except Exception as e:
        print(f"❌ Error during training: {e}")
        logging.error(f"Content model training error: {e}")


def check_prerequisites():
    """Check if prerequisites are met"""
    print("🔍 Checking prerequisites...")

    try:
        # Check database connection
        db, users_db = (
            content_based_recommender.books_collection.database,
            content_based_recommender.users_collection.database,
        )
        print("✅ Database connection: OK")

        # Check if books have summaries
        books_with_summaries = (
            content_based_recommender.books_collection.count_documents(
                {
                    "summary": {"$exists": True, "$ne": None, "$ne": ""},
                    "language_of_book": {"$exists": True, "$ne": None, "$ne": ""},
                }
            )
        )

        print(f"✅ Books with summaries and language: {books_with_summaries}")

        if books_with_summaries == 0:
            print("⚠️  No books found with summaries and language information!")
            print("   The content-based model requires books to have:")
            print("   - summary field (not empty)")
            print("   - language_of_book field (not empty)")
            return False

        # Check if users have interactions
        user_interactions = (
            content_based_recommender.interactions_collection.count_documents(
                {"action": "like"}
            )
        )

        print(f"✅ User like interactions: {user_interactions}")

        if user_interactions == 0:
            print("⚠️  No user like interactions found!")
            print("   Users need to like books to get content-based recommendations.")

        return True

    except Exception as e:
        print(f"❌ Prerequisites check failed: {e}")
        return False


def main():
    """Main function"""
    setup_logging()

    print("🚀 Content-Based Recommendation Model Training")
    print("=" * 60)

    # Check prerequisites
    if not check_prerequisites():
        print(
            "\n❌ Prerequisites not met. Please fix the issues above before training."
        )
        return

    print("\n" + "=" * 60)

    # Train the model
    train_content_based_model()

    print("\n" + "=" * 60)
    print("🎉 Training process complete!")
    print("\n📝 Next steps:")
    print(
        "   1. Test the content-based endpoint: /api/books/recommendations/content-based"
    )
    print("   2. Check that users with liked books get recommendations")
    print("   3. Verify recommendations are based on similar content")


if __name__ == "__main__":
    main()
