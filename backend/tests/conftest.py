import os
import tempfile

# Point the app at a throwaway database before anything imports app.database,
# so the suite never drops or reseeds the developer's local ecosg.db.
os.environ["ECOSG_DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="ecosg-test-"), "test.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as c:  # entering runs startup, which seeds the empty DB
        yield c
