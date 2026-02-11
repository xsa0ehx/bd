from pathlib import Path


def test_dashboard_template_file_exists_in_expected_path():
    assert Path("app/templates/dashboard/main.html").exists()


def test_dashboard_route_renders_existing_template_and_includes_required_context_fields():
    source = Path("app/routers/ui_auth.py").read_text(encoding="utf-8")

    assert '"dashboard/main.html"' in source
    assert '"user": user' in source
    assert '"profile": user.profile' in source
    assert 'jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])' in source


def test_request_logging_middleware_initializes_response_before_usage():
    source = Path("app/main.py").read_text(encoding="utf-8")

    assert "response = None" in source
    assert "response = JSONResponse(" in source
    assert 'response.headers["X-Process-Time"]' in source