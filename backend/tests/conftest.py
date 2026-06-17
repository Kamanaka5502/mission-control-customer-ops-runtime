import pytest
from app.database import init_db


@pytest.fixture(autouse=True, scope="session")
def initialize_test_database():
    init_db()
