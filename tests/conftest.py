from unittest.mock import patch
import pytest
import mongomock
from db import DB


@pytest.fixture
def mock_db():
    with patch("db.MongoClient", mongomock.MongoClient):
        yield DB()
