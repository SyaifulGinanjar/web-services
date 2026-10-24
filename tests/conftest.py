import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import login_limiter


@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app
    login_limiter._hits.clear()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    with client.session_transaction() as session:
        session['username'] = 'admin'
    return client
