from fastapi.testclient import TestClient

from app.main import app

DEFAULT_ADMIN_PASSWORD = '{aZ9$kL2#mN8&qR5*vX1@pY4%wB".}'


def _extract_csrf_token(html: str) -> str:
    marker = 'name="csrf_token" value="'
    start = html.find(marker)
    assert start != -1
    start += len(marker)
    end = html.find('"', start)
    return html[start:end]


def test_admin_login_success_redirects_to_dashboard():
    with TestClient(app) as client:
        login_page = client.get('/admin/login')
        assert login_page.status_code == 200

        csrf_token = _extract_csrf_token(login_page.text)

        response = client.post(
            '/admin/login',
            data={
                'password': DEFAULT_ADMIN_PASSWORD,
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers['location'] == '/admin/dashboard'


def test_admin_login_wrong_password_enforces_lockout():
    with TestClient(app) as client:
        login_page = client.get('/admin/login')
        csrf_token = _extract_csrf_token(login_page.text)

        wrong_attempt = client.post(
            '/admin/login',
            data={'password': 'wrong-pass', 'csrf_token': csrf_token},
        )
        assert wrong_attempt.status_code == 401
        assert 'Incorrect password. Please wait for 15 minutes before trying again.' in wrong_attempt.text

        second_attempt = client.post(
            '/admin/login',
            data={'password': DEFAULT_ADMIN_PASSWORD, 'csrf_token': csrf_token},
        )
        assert second_attempt.status_code == 429
        assert 'Incorrect password. Please wait for 15 minutes before trying again.' in second_attempt.text


def test_admin_dashboard_requires_authentication():
    with TestClient(app) as client:
        response = client.get('/admin/dashboard', follow_redirects=False)
        assert response.status_code == 303
        assert response.headers['location'] == '/admin/login'