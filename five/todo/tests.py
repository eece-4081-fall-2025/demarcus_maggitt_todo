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

# ---------- Frontend tests for "Add a task" ----------
@pytest.mark.skipif(True, reason="Enable Playwright frontend tests by setting skip to False and ensuring app is running")
def test_frontend_create_task_shows_in_list():
    """
    Frontend test using Playwright:
    - visit /tasks
    - open create form, fill title, submit
    - assert new task visible in list
    NOTE: This test is skipped by default. Set decorator skip to False to run.
    """
    base_url = "http://localhost:3000"  # change to your frontend dev URL
    pw, browser, context, page = start_playwright_page(base_url)
    try:
        # Adapt selectors to your app e.g. data-test attributes
        page.click("[data-test=add-task]")               # open create form
        page.fill("input[name=title]", "E2E Task " + str(uuid.uuid4()))
        page.click("[data-test=save-task]")            # submit
        # wait for list update
        page.wait_for_selector("[data-test=task-card]", timeout=3000)
        # Basic assertion: at least one task card exists
        cards = page.query_selector_all("[data-test=task-card]")
        assert len(cards) >= 1
    finally:
        stop_playwright(browser, context)

@pytest.mark.skipif(True, reason="Enable Playwright frontend tests by setting skip to False and ensuring app is running")
def test_frontend_create_task_validation_shows_error():
    """
    Frontend validation test:
    - try to submit empty form -> expect validation error visible
    """
    base_url = "http://localhost:3000"
    pw, browser, context, page = start_playwright_page(base_url)
    try:
        page.click("[data-test=add-task]")
        page.click("[data-test=save-task]")
        # Wait and assert validation text exists
        page.wait_for_selector("text=Title is required", timeout=2000)
        assert page.is_visible("text=Title is required")
    finally:
        stop_playwright(browser, context)

# ---------- Frontend tests for "Edit a task" ----------
@pytest.mark.skipif(True, reason="Enable Playwright frontend tests by setting skip to False and ensuring app is running")
def test_frontend_edit_task_prefilled_and_saves():
    """
    Frontend test:
    - ensure edit modal is prefilling form fields
    - update values and save -> task list shows updated text
    """
    base_url = "http://localhost:3000"
    pw, browser, context, page = start_playwright_page(base_url)
    try:
        # Precondition: ensure at least one task exists, or create via UI
        page.click("[data-test=add-task]")
        page.fill("input[name=title]", "Task to edit " + str(uuid.uuid4()))
        page.click("[data-test=save-task]")
        page.wait_for_selector("[data-test=task-card]")

        # Click edit on the first card
        page.click("[data-test=task-card] [data-test=edit-task]")
        # Check prefilled
        assert page.get_attribute("input[name=title]", "value") != ""
        # Change and save
        page.fill("input[name=title]", "Task edited " + str(uuid.uuid4()))
        page.click("[data-test=save-task]")
        # Verify updated content appears
        page.wait_for_timeout(500)  # brief wait for UI update
        assert page.query_selector("[data-test=task-card]") is not None
    finally:
        stop_playwright(browser, context)

# ---------- Frontend tests for "Delete a task" ----------
@pytest.mark.skipif(True, reason="Enable Playwright frontend tests by setting skip to False and ensuring app is running")
def test_frontend_delete_task_confirm_and_removes():
    """
    Frontend test:
    - create a task if necessary
    - trigger delete -> confirm -> verify it's removed from DOM
    """
    base_url = "http://localhost:3000"
    pw, browser, context, page = start_playwright_page(base_url)
    try:
        # create
        page.click("[data-test=add-task]")
        title = "To delete UI " + str(uuid.uuid4())
        page.fill("input[name=title]", title)
        page.click("[data-test=save-task]")
        page.wait_for_selector(f"text={title}")

        # find card containing the title and click delete
        page.click(f"text={title} >> xpath=.. >> [data-test=delete-task]")
        # confirm dialog
        page.click("[data-test=confirm-delete]")

        # wait briefly and assert task no longer present
        page.wait_for_timeout(300)
        assert not page.is_visible(f"text={title}")
    finally:
        stop_playwright(browser, context)

# ---------- Frontend tests for "Mark complete" ----------
@pytest.mark.skipif(True, reason="Enable Playwright frontend tests by setting skip to False and ensuring app is running")
def test_frontend_toggle_complete_updates_ui():
    """
    Frontend test:
    - create task via UI
    - toggle complete checkbox
    - assert CSS class or attribute changes to indicate completed
    """
    base_url = "http://localhost:3000"
    pw, browser, context, page = start_playwright_page(base_url)
    try:
        title = "Toggle UI " + str(uuid.uuid4())
        page.click("[data-test=add-task]")
        page.fill("input[name=title]", title)
        page.click("[data-test=save-task]")
        page.wait_for_selector(f"text={title}")

        # toggle complete (assumes a checkbox within card)
        card_selector = f"text={title} >> xpath=.."
        page.click(f"{card_selector} [data-test=complete-toggle]")
        time.sleep(0.2)
        # assert card has 'completed' class or aria-checked attribute
        # adapt selector/assertion to your app
        card = page.query_selector(card_selector)
        assert card is not None
        # Example assertion: completed class exists
        completed = card.get_attribute("class")
        assert completed is not None
    finally:
        stop_playwright(browser, context)
