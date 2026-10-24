import pytest
from werkzeug.security import generate_password_hash

from app.config import TestConfig
from app import create_app
from app.models import Users
from app.views.auth import _safe_next


@pytest.fixture
def fake_auth(monkeypatch):
    monkeypatch.setattr(Users, 'authenticate', lambda self, u, p: (u, p) == ('admin', 'rahasia'))


def test_protected_page_redirects_to_login(client):
    response = client.get('/customer/?q=budi')
    assert response.status_code == 302
    assert '/login?next=/customer/?q%3Dbudi' in response.headers['Location']


def test_health_is_public(client):
    assert client.get('/health').get_json() == {'status': 'ok'}


def test_login_success_redirects_to_next(client, fake_auth):
    response = client.post('/login?next=/karyawan/', data={'username': 'admin', 'password': 'rahasia'})
    assert response.status_code == 302
    assert response.headers['Location'] == '/karyawan/'


def test_login_rejects_external_next(client, fake_auth):
    response = client.post('/login?next=//evil.com', data={'username': 'admin', 'password': 'rahasia'})
    assert response.headers['Location'] == '/'


def test_login_failure(client, fake_auth):
    response = client.post('/login', data={'username': 'admin', 'password': 'salah'})
    assert response.status_code == 401
    assert 'salah' in response.get_data(as_text=True)


def test_login_rate_limited(client, fake_auth):
    for _ in range(5):
        client.post('/login', data={'username': 'admin', 'password': 'salah'})
    response = client.post('/login', data={'username': 'admin', 'password': 'rahasia'})
    assert response.status_code == 429


def test_logout_requires_post(auth_client):
    assert auth_client.get('/logout').status_code == 405
    assert auth_client.post('/logout').status_code == 302
    assert auth_client.get('/').status_code == 302


def test_csrf_enforced():
    class CsrfConfig(TestConfig):
        WTF_CSRF_ENABLED = True

    client = create_app(CsrfConfig).test_client()
    assert client.post('/login', data={'username': 'a', 'password': 'b'}).status_code == 400


@pytest.mark.parametrize('target, expected', [
    ('/customer/', '/customer/'),
    ('//evil.com', None),
    ('https://evil.com/', None),
    ('customer', None),
    ('', None),
])
def test_safe_next(target, expected):
    assert _safe_next(target) == expected


def test_password_verify_supports_hash_and_legacy_plaintext():
    assert Users._verify(generate_password_hash('abc12345', method='pbkdf2:sha256'), 'abc12345')
    assert Users._verify('plain', 'plain')
    assert not Users._verify('plain', 'other')
    assert not Users._verify(None, 'x')
