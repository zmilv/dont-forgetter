import pytest


@pytest.fixture(scope="session")
def celery_config():
    return {
        "broker_url": "memory://",
        "result_backend": "redis://",
        "worker_concurrency": 1,
    }
