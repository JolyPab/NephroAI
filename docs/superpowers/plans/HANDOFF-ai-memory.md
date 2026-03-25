# Handoff: AI Assistant Memory Feature

## Context
Feature branch: `feature/ai-assistant-memory`
Worktree: `c:\Users\jolypab\Documents\CODE\medic\.worktrees\feature-ai-memory`
Python binary: `/c/Users/jolypab/AppData/Local/Microsoft/WindowsApps/python3.11.exe`
Run tests from repo root: `python3.11 -m pytest backend/tests/ -v`

## Completed Tasks
- Task 1: DB models (ChatSession, ChatMessageRecord, PatientMemory) — commit `4067919`
- Task 2: Redis lazy-init client + cache invalidation on POST /api/v2/documents — commit `a1db094`
- Task 3: `_openai_chat_completion_with_history()` helper + AdviceRequest/AdviceResponse updated (`session_id: Optional[int] = None`) + test file `backend/tests/test_advice_with_history.py` (2 tests, currently FAILING intentionally — will pass after Task 6) — commits `e5a18db`, `6b5b16c`

## Pending Tasks (4–14)
All tasks are in the plan file: `docs/superpowers/plans/2026-03-23-ai-assistant-memory.md`

**Task 4** (next): Chat Session CRUD Endpoints
- Create `backend/tests/test_chat_sessions.py` (4 tests)
- Add Pydantic models: `ChatSessionCreate`, `ChatSessionItem`, `ChatSessionMessageItem`
- Add 4 endpoints to `main.py` before `@app.post("/api/advice")`:
  - `GET /api/chat/sessions`
  - `POST /api/chat/sessions`
  - `GET /api/chat/sessions/{session_id}/messages`
  - `DELETE /api/chat/sessions/{session_id}`
- Commit: `feat: add chat session CRUD endpoints`

**Task 5**: Patient Memory Endpoints (`GET /api/chat/memory`, `DELETE /api/chat/memory/{id}`)
**Task 6**: Updated `get_advice` — session management, history, Redis cache, new prompt (big task)
**Task 7**: Celery task `extract_patient_memory`
**Task 8**: Frontend models (`chat-session.model.ts`, update `advice.model.ts`)
**Task 9**: Update `advice.service.ts`
**Task 10**: i18n keys (es/en/ru)
**Task 11**: `chat-sidebar` component
**Task 12**: `chat-memory-panel` component
**Task 13**: Update `chat-page.component`
**Task 14**: Final integration check

## Key Implementation Notes
- Tests run from repo root (not `cd backend`)
- `ChatMessageRecord` (not `ChatMessage`) to avoid Angular collision
- `AdviceResponse.session_id` is `Optional[int] = None`
- Redis client is lazy-init via `_get_redis()` — returns None gracefully if Redis unavailable
- `CELERY_ENABLED` env var: if False, call task body directly wrapped in try/except
- Do NOT use subagent-driven-development skill — just implement directly to save context
