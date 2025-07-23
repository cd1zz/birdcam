import shutil
import sys
from pathlib import Path

import types

import pytest
from dotenv import load_dotenv

sys.modules.setdefault("cv2", types.ModuleType("cv2"))

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Get the project root directory (parent of tests directory)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

ORIGINAL_ENV_PATH = PROJECT_ROOT / ".env.processor"
if not ORIGINAL_ENV_PATH.exists():
    ORIGINAL_ENV_PATH = PROJECT_ROOT / "config/examples/.env.processor.example"

TEST_ENV_PATH = Path(".env.test")
TMP_STORAGE = Path("tests/tmp/storage")


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    shutil.copyfile(ORIGINAL_ENV_PATH, TEST_ENV_PATH)

    # Override storage path so database is created in tests/tmp
    lines = TEST_ENV_PATH.read_text().splitlines()
    with TEST_ENV_PATH.open("w") as f:
        for line in lines:
            if line.startswith("STORAGE_PATH="):
                f.write(f"STORAGE_PATH={TMP_STORAGE}\n")
            else:
                f.write(line + "\n")

    # Ensure storage directory exists
    TMP_STORAGE.mkdir(parents=True, exist_ok=True)

    load_dotenv(TEST_ENV_PATH, override=True)

    yield

    if TEST_ENV_PATH.exists():
        TEST_ENV_PATH.unlink()
    if TMP_STORAGE.exists():
        shutil.rmtree(TMP_STORAGE)


class DummyModelManager:
    def __init__(self):
        self.is_loaded = False


class DummyProcessingService:
    def __init__(self):
        self.model_manager = DummyModelManager()

    def get_queue_metrics(self):
        return {
            "queue_length": 0,
            "currently_processing": 0,
            "failed_videos": 0,
            "is_processing": False,
        }

    def get_processing_rate_metrics(self):
        return {
            "videos_per_hour": 0,
            "videos_per_day": 0,
            "avg_processing_time": 0,
            "session_processed": 0,
            "session_failed": 0,
        }

    def get_detailed_processing_stats(self):
        return {
            "total_processed": 0,
            "videos_with_detections": 0,
            "detection_rate": 0,
            "total_detections": 0,
        }

    def receive_video(self, *_, **__):
        return "test.mp4"

    def process_pending_videos(self):
        pass

    def cleanup_old_videos(self):
        pass

    def delete_detection(self, *_):
        return 0


class DummyRepo:
    def create_table(self):
        pass

    def get_today_detections(self):
        return 0

    def get_processed_count(self):
        return 0

    def get_recent_filtered_with_thumbnails(self, *_, **__):
        return []

    def delete_detection(self, *_):
        return 0


@pytest.fixture(scope="session")
def flask_app():
    from config.settings import load_processing_config
    from web.app import create_processing_app

    config = load_processing_config()
    app = create_processing_app(
        DummyProcessingService(),
        DummyRepo(),
        DummyRepo(),
        config,
    )
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="session")
def client(flask_app):
    return flask_app.test_client()
