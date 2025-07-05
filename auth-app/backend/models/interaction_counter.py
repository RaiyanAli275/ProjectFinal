import os
import sys
import subprocess
import threading
import logging
from datetime import datetime
from database.mongodb_manager import mongodb_manager


class InteractionCounter:
    """
    MongoDB counter system that tracks like/dislike interactions across all users
    and automatically triggers model retraining when the counter reaches the threshold.
    """

    def __init__(self):
        # Use the counter database
        self.db = mongodb_manager.get_database("counter")
        self.counters_collection = self.db["interaction_counters"]
        self.training_history_collection = self.db["training_history"]

        # Configuration
        self.INTERACTION_THRESHOLD = 10
        self.TRAINING_TIMEOUT = 600  # 10 minutes
        self.MAX_CONCURRENT_TRAININGS = 1
        self.RETRY_ATTEMPTS = 3

        # Create indexes for better performance
        try:
            self.counters_collection.create_index("counter_type", unique=True)
            self.training_history_collection.create_index("training_started")
        except:
            # Indexes might already exist
            pass

        # Setup logging
        self.logger = logging.getLogger(__name__)

        # Initialize counter if it doesn't exist
        self._initialize_counter()

        # Track concurrent trainings
        self._training_lock = threading.Lock()
        self._training_in_progress = False

    def _initialize_counter(self):
        """Initialize the counter document if it doesn't exist"""
        try:
            existing_counter = self.counters_collection.find_one(
                {"counter_type": "like_dislike_interactions"}
            )

            if not existing_counter:
                self.counters_collection.insert_one(
                    {
                        "counter_type": "like_dislike_interactions",
                        "current_count": 0,
                        "threshold": self.INTERACTION_THRESHOLD,
                        "last_updated": datetime.utcnow(),
                        "last_reset": datetime.utcnow(),
                        "total_retrainings": 0,
                        "created_at": datetime.utcnow(),
                    }
                )

        except Exception as e:
            self.logger.error(f"Error initializing counter: {e}")

    def increment_counter(self):
        """
        Atomically increment the counter and trigger training if threshold is reached.
        Returns True if training was triggered, False otherwise.
        """
        try:
            # Atomic increment operation
            result = self.counters_collection.find_one_and_update(
                {"counter_type": "like_dislike_interactions"},
                {
                    "$inc": {"current_count": 1},
                    "$set": {"last_updated": datetime.utcnow()},
                },
                return_document=True,  # Return updated document
            )

            if not result:
                return False

            current_count = result["current_count"]
            threshold = result["threshold"]

            # Check if threshold reached
            if current_count >= threshold:
                return self._trigger_model_training(current_count)

            return False

        except Exception as e:
            self.logger.error(f"Error incrementing counter: {e}")
            return False

    def _trigger_model_training(self, trigger_count):
        """Trigger model training in background and reset counter"""
        try:
            # Check if training is already in progress
            with self._training_lock:
                if self._training_in_progress:
                    return False

                self._training_in_progress = True

            # Reset counter immediately to prevent multiple triggers
            self.reset_counter()

            # Start training in background thread
            training_thread = threading.Thread(
                target=self._execute_training,
                args=(trigger_count,),
                daemon=True,  # Don't block app shutdown
            )
            training_thread.start()
            return True

        except Exception as e:
            self.logger.error(f"Error triggering model training: {e}")
            # Release lock if error occurred
            with self._training_lock:
                self._training_in_progress = False
            return False

    def _execute_training(self, trigger_count):
        """Execute the training script in background"""
        training_start = datetime.utcnow()
        training_id = None

        try:
            # Log training start
            training_record = {
                "trigger_count": trigger_count,
                "training_started": training_start,
                "training_completed": None,
                "training_duration_seconds": None,
                "training_status": "in_progress",
                "error_message": None,
                "model_metrics": {},
            }

            result = self.training_history_collection.insert_one(training_record)
            training_id = result.inserted_id

            # Get the path to train_model.py
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            train_script_path = os.path.join(backend_dir, "train_model.py")

            if not os.path.exists(train_script_path):
                raise FileNotFoundError(
                    f"Training script not found at {train_script_path}"
                )

            process = subprocess.Popen(
                [sys.executable, train_script_path],
                cwd=backend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(timeout=self.TRAINING_TIMEOUT)
                training_end = datetime.utcnow()
                duration = (training_end - training_start).total_seconds()

                if process.returncode == 0:
                    # Training successful
                    # Parse training metrics from stdout if available
                    model_metrics = self._parse_training_metrics(stdout)

                    # Update training record
                    self.training_history_collection.update_one(
                        {"_id": training_id},
                        {
                            "$set": {
                                "training_completed": training_end,
                                "training_duration_seconds": duration,
                                "training_status": "success",
                                "model_metrics": model_metrics,
                            }
                        },
                    )

                    # Increment total retrainings count
                    self.counters_collection.update_one(
                        {"counter_type": "like_dislike_interactions"},
                        {"$inc": {"total_retrainings": 1}},
                    )

                    # Force reload the newly trained model and clear caches
                    self._reload_model_and_clear_caches()

                else:
                    # Training failed
                    error_msg = f"Training failed with return code {process.returncode}. STDERR: {stderr}"
                    self.logger.error(error_msg)

                    self.training_history_collection.update_one(
                        {"_id": training_id},
                        {
                            "$set": {
                                "training_completed": training_end,
                                "training_duration_seconds": duration,
                                "training_status": "failed",
                                "error_message": error_msg,
                            }
                        },
                    )

            except subprocess.TimeoutExpired:
                # Training timed out
                process.kill()
                training_end = datetime.utcnow()
                duration = (training_end - training_start).total_seconds()

                error_msg = f"Training timed out after {duration:.1f}s"
                self.logger.error(error_msg)

                self.training_history_collection.update_one(
                    {"_id": training_id},
                    {
                        "$set": {
                            "training_completed": training_end,
                            "training_duration_seconds": duration,
                            "training_status": "timeout",
                            "error_message": error_msg,
                        }
                    },
                )

        except Exception as e:
            # Unexpected error during training
            training_end = datetime.utcnow()
            duration = (training_end - training_start).total_seconds()

            error_msg = f"Unexpected error during training: {str(e)}"
            self.logger.error(error_msg)

            if training_id:
                self.training_history_collection.update_one(
                    {"_id": training_id},
                    {
                        "$set": {
                            "training_completed": training_end,
                            "training_duration_seconds": duration,
                            "training_status": "error",
                            "error_message": error_msg,
                        }
                    },
                )

        finally:
            # Release training lock
            with self._training_lock:
                self._training_in_progress = False

    def _parse_training_metrics(self, stdout):
        """Parse training metrics from stdout"""
        metrics = {}
        try:
            lines = stdout.split("\n")
            for line in lines:
                if "Total interactions:" in line:
                    metrics["total_interactions"] = int(
                        line.split(":")[1].strip().replace(",", "")
                    )
                elif "Total users:" in line:
                    metrics["total_users"] = int(
                        line.split(":")[1].strip().replace(",", "")
                    )
                elif "Total books:" in line:
                    metrics["total_books"] = int(
                        line.split(":")[1].strip().replace(",", "")
                    )
                elif "Training time:" in line:
                    metrics["training_time_seconds"] = float(
                        line.split(":")[1].strip().split()[0]
                    )
        except Exception as e:
            self.logger.warning(f"Could not parse training metrics: {e}")

        return metrics

    def reset_counter(self):
        """Reset the counter to 0"""
        try:
            self.counters_collection.update_one(
                {"counter_type": "like_dislike_interactions"},
                {"$set": {"current_count": 0, "last_reset": datetime.utcnow()}},
            )
            return True

        except Exception as e:
            self.logger.error(f"Error resetting counter: {e}")
            return False

    def get_current_count(self):
        """Get the current counter value"""
        try:
            counter_doc = self.counters_collection.find_one(
                {"counter_type": "like_dislike_interactions"}
            )

            if counter_doc:
                return counter_doc["current_count"]
            return 0

        except Exception as e:
            self.logger.error(f"Error getting current count: {e}")
            return 0

    def _reload_model_and_clear_caches(self):
        """Reload the trained model and clear all recommendation caches"""
        try:

            # Import recommendation engine (avoid circular imports)
            from models.recommendation_engine import recommendation_engine

            # Force reload the newly trained model
            model_reloaded = recommendation_engine.force_reload_model()

            # Clear all recommendation caches
            caches_cleared = recommendation_engine.clear_all_recommendation_caches()

            if model_reloaded and caches_cleared:
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"❌ Error reloading model and clearing caches: {e}")
            return False


# Global instance
interaction_counter = InteractionCounter()
