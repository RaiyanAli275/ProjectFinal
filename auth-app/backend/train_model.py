#!/usr/bin/env python3
"""
ALS Recommendation Model Training Script

This script trains the ALS (Alternating Least Squares) recommendation model
using the existing user interaction data.

Usage:
    python train_model.py [--factors 64] [--iterations 50] [--regularization 0.1]
"""

import sys
import os
import argparse
from datetime import datetime

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.recommendation_engine import recommendation_engine


def train_model(factors=64, iterations=50, regularization=0.1, alpha=40):

    start_time = datetime.now()

    try:
        # Build interaction matrix
        if not recommendation_engine.build_interaction_matrix():
            return False

        # Train model
        success = recommendation_engine.train_model(
            factors=factors,
            regularization=regularization,
            iterations=iterations,
            alpha=alpha,
        )
        recommendation_engine.save_user_similarities(top_k=10)

        if success:
            end_time = datetime.now()
            training_time = (end_time - start_time).total_seconds()

            return True
        else:
            return False

    except Exception as e:
        print(f"Error during training: {e}")
        return False


def test_recommendations():
    """Test the trained model with sample recommendations"""
    try:
        # Get a sample user who has interactions
        sample_users = recommendation_engine.interactions_collection.distinct("user_id")

        if not sample_users:
            return

        # Test with first user
        test_user = sample_users[0]

        # Get recommendations
        recommendations = recommendation_engine.get_recommendations(test_user, 5)

        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                algo = rec.get("algorithm", "unknown")
                score = rec.get("recommendation_score", 0)
                confidence = rec.get("confidence", 0)
    except Exception as e:
        print(f"   Error testing recommendations: {e}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Train ALS Recommendation Model")
    parser.add_argument(
        "--factors", type=int, default=64, help="Number of latent factors (default: 64)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=50,
        help="Number of training iterations (default: 50)",
    )
    parser.add_argument(
        "--regularization",
        type=float,
        default=0.1,
        help="Regularization parameter (default: 0.1)",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=40,
        help="Confidence parameter for implicit feedback (default: 40)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check data availability, do not train",
    )

    # parser.add_argument('--factors', type=int, default=32, help='Number of latent factors (default: 64)')
    # parser.add_argument('--iterations', type=int, default=10, help='Number of training iterations (default: 50)')
    # parser.add_argument('--regularization', type=float, default=0.1, help='Regularization parameter (default: 0.1)')
    # parser.add_argument('--alpha', type=float, default=40, help='Confidence parameter for implicit feedback (default: 40)')

    args = parser.parse_args()

    if args.check_only:
        return 0

    # Train model
    success = train_model(
        factors=args.factors,
        iterations=args.iterations,
        regularization=args.regularization,
        alpha=args.alpha,
    )

    if success:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())
