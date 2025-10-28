# Epic 1: Task Management 
**Goal**: deliver create/read/update/delete + complete toggle for tasks with auth-protected persistence.

## Backend
1. DB: Add tasks table + migration.
2. Model: Task ORM model (fields: id, user_id, title, description, due_date, priority, completed, created_at, updated_at).
3. API: POST /api/tasks (create).
4. API: GET /api/tasks (list for current user).
5. API: GET /api/tasks/:id (read).
6. API: PUT /api/tasks/:id (edit).
7. API: DELETE /api/tasks/:id (delete).
8. API: PATCH /api/tasks/:id/complete (toggle complete).
9. Auth middleware tests to ensure tasks are user-scoped.

## Frontend
10. Task List page (fetch & render tasks).
11. Create Task form + client validation.
12. Edit Task modal/form (prefilled).
13. Task card component (title, due, priority, assignee placeholder, complete toggle, menu).
14. Delete confirmation & undo toast (optional).
15. Filter by status (All / Active / Completed) and simple sorting.

## DevOps / CI
16. Add test runner to CI (run unit & integration tests).
17. Add migration & seed scripts for dev.

## QA
18. Write end-to-end test for create→edit→complete→delete flow.