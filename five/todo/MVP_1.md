## MVP selection
- **Epic delivered:** Epic 1 — Task Management (stories 1–4)
- **Why:** core user value — users can actually create and manage tasks. Other epics are incremental.

## MVP Scope
- Auth-protected task CRUD for a single user.
- UI: simple list, create form, edit modal, complete toggle, delete with confirmation.
- Backend: persistent storage (DB), REST API endpoints, basic validation.
- Tests: unit tests for API; one E2E test for the create→edit→complete→delete flow.

## Definition of Done
- All stories 1–4 have passing tests covering basic success & fail paths.
- Code is in main branch via PR that documents TDD cycles

## Acceptance tests
- User can create a task with a title; it appears in the list and persists after reload.
- User can edit a task and see updated fields.
- User can delete a task and it is removed.
- User can toggle complete; completed state shown visually and persisted.