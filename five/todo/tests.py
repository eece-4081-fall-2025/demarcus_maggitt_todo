from django.test import TestCase
import pytest
import uuid
import time

# ---------------------------
# Backend setup & fixtures
# ---------------------------
try:
    # Adjust this import to your project's FastAPI app location:
    from app.main import app  # <-- change to your "app" module if needed
    from fastapi.testclient import TestClient
    client = TestClient(app)
except Exception as e:
    # If app import fails, create a small helper to skip backend tests gracefully.
    client = None

@pytest.fixture(scope="session")
def auth_header():
    """
    Returns an Authorization header for tests.
    Adjust to your auth mechanism (JWT, session cookie, etc).
    For simple test setups you can return {} and disable auth validation server-side.
    """
    # Example: a bearer token string; adapt or return {} if no auth required.
    token = "test-token"
    return {"Authorization": f"Bearer {token}"}

def create_task_api(title="task-"+str(uuid.uuid4()), description=""):
    """
    Helper to create a task via API. Returns the created task dict.
    Assumes POST /api/tasks is available and authentication is not strictly enforced
    or auth is stubbed for tests.
    """
    assert client is not None, "Backend client not available; check app import."
    payload = {"title": title, "description": description}
    r = client.post("/api/tasks", json=payload)
    assert r.status_code in (200, 201)
    return r.json()

# ---------------------------
# Frontend (Playwright) helper
# ---------------------------
def start_playwright_page(base_url="http://localhost:3000"):
    """
    Lightweight helper that returns a Playwright page object (sync).
    The test will call playwright_context.__enter__() and return (playwright, browser, page).
    """
    playwright = pytest.importorskip("playwright.sync_api")
    pw = playwright.sync_api
    browser = pw.sync_playwright().start().webkit.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto(base_url)
    return pw, browser, context, page

def stop_playwright(browser, context):
    try:
        context.close()
    except Exception:
        pass
    try:
        browser.close()
    except Exception:
        pass

# ---------- Backend tests for "Add a task" ----------
@pytest.mark.skipif(client is None, reason="Backend app not available")
def test_backend_create_task_success(auth_header):
    """
    Red/Green/Refactor cycle targeted test: happy path to create a task.
    Expectation: POST /api/tasks returns 201 and persisted task appears in GET /api/tasks.
    """
    title = f"Buy milk {uuid.uuid4()}"
    r = client.post("/api/tasks", json={"title": title}, headers=auth_header)
    assert r.status_code in (200, 201)
    body = r.json()
    assert body["title"] == title
    assert "id" in body
    # verify via GET
    list_r = client.get("/api/tasks", headers=auth_header)
    assert list_r.status_code == 200
    assert any(t["id"] == body["id"] for t in list_r.json())

@pytest.mark.skipif(client is None, reason="Backend app not available")
def test_backend_create_task_requires_title(auth_header):
    """
    Second cycle: validation test (title required).
    Expectation: POST /api/tasks without title returns 400 (or 422 depending on server).
    """
    r = client.post("/api/tasks", json={"description": "no title"}, headers=auth_header)
    assert r.status_code in (400, 422)

# ---------- Backend tests for "Edit a task" ----------
@pytest.mark.skipif(client is None, reason="Backend app not available")
def test_backend_update_task_success(auth_header):
    """
    Happy path: create a task then update its title and description with PUT /api/tasks/:id
    """
    t = create_task_api(title="Old Title")
    r = client.put(f"/api/tasks/{t['id']}", json={"title": "New Title", "description": "Updated"}, headers=auth_header)
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "New Title"
    assert body.get("description", "") == "Updated"

@pytest.mark.skipif(client is None, reason="Backend app not available")
def test_backend_update_task_not_found(auth_header):
    """
    Edge: updating a non-existent task should return 404
    """
    r = client.put("/api/tasks/non-existent-id", json={"title": "x"}, headers=auth_header)
    assert r.status_code == 404

# ---------- Backend tests for "Delete a task" ----------
@pytest.mark.skipif(client is None, reason="Backend app not available")
def test_backend_delete_task_success(auth_header):
    """
    Happy path: create a task then delete it; verify it's removed from GET /api/tasks.
    """
    t = create_task_api(title="ToBeDeleted-"+str(uuid.uuid4()))
    r = client.delete(f"/api/tasks/{t['id']}", headers=auth_header)
    assert r.status_code in (200, 204)
    # confirm removal
    list_r = client.get("/api/tasks", headers=auth_header)
    assert not any(x["id"] == t["id"] for x in list_r.json())

@pytest.mark.skipif(client is None, reason="Backend app not available")
def test_backend_delete_task_not_found(auth_header):
    r = client.delete("/api/tasks/does-not-exist", headers=auth_header)
    assert r.status_code == 404

# ---------- Backend tests for "Mark complete" ----------
@pytest.mark.skipif(client is None, reason="Backend app not available")
def test_backend_mark_complete_and_uncomplete(auth_header):
    """
    Toggle completed state via PATCH /api/tasks/:id/complete or PUT with completed field.
    """
    t = create_task_api(title="ToggleComplete-" + str(uuid.uuid4()))
    # set completed true
    r = client.patch(f"/api/tasks/{t['id']}/complete", json={"completed": True}, headers=auth_header)
    assert r.status_code == 200
    assert r.json().get("completed", False) is True
    # toggle back to false
    r2 = client.patch(f"/api/tasks/{t['id']}/complete", json={"completed": False}, headers=auth_header)
    assert r2.status_code == 200
    assert r2.json().get("completed", True) is False

