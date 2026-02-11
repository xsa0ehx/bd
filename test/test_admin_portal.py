from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_admin_dashboard_requires_authentication():
    response = client.get("/admin/dashboard", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_admin_login_rejects_invalid_password():
    response = client.post("/admin/login", data={"password": "invalid"})

    assert response.status_code == 401
    assert "رمز عبور مدیر نادرست است" in response.text


def test_admin_login_accepts_default_password_and_sets_cookie():
    response = client.post(
        "/admin/login",
        data={"password": '{aZ9$kL2#mN8&qR5*vX1@pY4%wB".}'},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/dashboard"
    assert "admin_access_token" in response.cookies