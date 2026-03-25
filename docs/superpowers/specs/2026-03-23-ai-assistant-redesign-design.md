# AI Assistant Redesign — Design Spec
**Date:** 2026-03-23
**Project:** NephroAI
**Approach:** Variant B — Async memory via Celery

---

## Problem Statement

The current AI assistant (`POST /api/advice`) has three main issues:

1. **No memory** — every request is stateless; the assistant has no knowledge of previous conversations.
2. **Overly rigid prompt** — a fixed 3-part structure produces repetitive, formulaic answers regardless of the type of question.
3. **Cost inefficiency** — a full patient snapshot (up to 40 analytes with reference ranges) is rebuilt and sent with every single request.

---

## Goals

- Persistent, multi-session chat history (like ChatGPT conversations)
- AI memory layer: auto-extracted patient facts that persist across conversations
- Patient can view and delete individual memory facts
- Adaptive prompt: conversational, structured, or personalized depending on context
- Optimized cost: Redis-cached analyte snapshot + smart per-question metric filtering

---

## Data Model

Three new tables added via `ensure_*_columns()` pattern (no Alembic).

### `ChatSession` (SQLAlchemy model)
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| user_id | int FK | references User |
| title | str(200) | auto-set from first ~60 chars of first question |
| created_at | datetime | |
| updated_at | datetime | updated on each new message |
| is_archived | bool | default false |

### `ChatMessageRecord` (SQLAlchemy model)
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| session_id | int FK | references ChatSession |
| role | str | enum: "user" / "assistant" |
| content | text | |
| created_at | datetime | |

> **Naming note:** The SQLAlchemy model is named `ChatMessageRecord` (not `ChatMessage`) to avoid collision with the existing Angular frontend interface `ChatMessage` in `frontend/src/app/core/models/chat.model.ts`. The API response DTO uses the field name `messages` with items typed as `{role, content, created_at}`.

### `PatientMemory` (SQLAlchemy model)
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| user_id | int FK | references User |
| fact | text | a single extracted fact |
| category | str | enum: "medical" / "preference" / "recommendation" |
| source_session_id | int FK nullable | which session produced this fact |
| created_at | datetime | |
| updated_at | datetime | |

Each fact is a separate row (not a JSON blob) so patients can delete individual facts.

**Examples:**
- `"Paciente toma metformina 500mg"` — medical
- `"El consejo de beber más agua no le ayudó"` — preference
- `"Se recomendó reducir consumo de fósforo"` — recommendation

---

## Backend Changes

### New endpoints

```
GET    /api/chat/sessions                   list sessions (id, title, updated_at, last message preview)
POST   /api/chat/sessions                   create new session → returns session_id
GET    /api/chat/sessions/{id}/messages     all messages for a session
DELETE /api/chat/sessions/{id}              delete session + its messages (cascade)

GET    /api/chat/memory                     list all patient memory facts
DELETE /api/chat/memory/{id}               delete a specific fact
```

All endpoints protected via `get_current_user_id`.

### Modified: `POST /api/advice`

**Request model** — add `session_id: Optional[int] = None` to `AdviceRequest`.

**Response model** — add `session_id: int` to `AdviceResponse`.

**Frontend** — update `AdviceResponseModel` in `frontend/src/app/core/models/advice.model.ts` to include `session_id: number`.

**Request flow:**
1. If no `session_id` provided, create a new `ChatSession` automatically.
2. Save user question as `ChatMessageRecord(role="user")`.
3. Load last 10 `ChatMessageRecord` rows for this session ordered by `created_at` → build OpenAI `messages[]` array with `{role, content}` pairs.
4. Load `PatientMemory` facts for the user → inject into system prompt.
5. Analyte snapshot: check Redis cache key `analyte_snapshot:{user_id}` (TTL 3h). On miss: call `_summarize_metrics_v2()`, serialize to JSON, store in Redis. From cache, select **top-5 most relevant metrics** to the question (case-insensitive keyword match against `analyte_key` and display name). Always include full list of analyte names (without values) so the AI knows what data exists.
6. Call **new helper** `_openai_chat_completion_with_history(system_prompt, messages)` — takes a pre-built `messages[]` list and appends the user prompt as the last `{role: "user"}` entry. The existing `_openai_chat_completion(system, user)` remains unchanged for other callers.
7. Save answer as `ChatMessageRecord(role="assistant")`.
8. If session title is empty, set it from the first ~60 chars of the question.
9. Fire-and-forget: enqueue Celery task `extract_patient_memory.delay(session_id, user_id)`. If `CELERY_ENABLED=False` (dev/test), call the task function synchronously and swallow exceptions — never fail the advice response due to memory extraction.
10. Return `AdviceResponse` with `answer`, `usedMetrics`, `disclaimer`, and `session_id`.

### Redis setup in `main.py`

Check if a Redis client is already initialized in `main.py`. If not, add:
```python
import redis as redis_lib
_redis_client = redis_lib.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
```
Use `_redis_client` for analyte snapshot caching. Add a `_redis_client.delete(f"analyte_snapshot:{user_id}")` call inside the `POST /api/v2/documents` route handler, after a successful document upload.

### New helper: `_openai_chat_completion_with_history(system_prompt, messages)`

```python
# messages: list of {role: str, content: str} dicts, already in order.
# Appends a final "user" entry containing the composed user_prompt.
# Uses same retry logic as _openai_chat_completion.
# max_tokens=800, temperature=0.4.
```

The existing `_openai_chat_completion(system_prompt, user_prompt)` is **not changed**.

### New Celery task: `extract_patient_memory(session_id, user_id)`

Runs asynchronously after each answer. Does not block the user response.

1. Load last 2 `ChatMessageRecord` rows for the session (question + answer).
2. Load existing `PatientMemory` facts for the user (to avoid duplicates).
3. Call `_openai_chat_completion` with prompt:
   > System: "Eres un extractor de hechos médicos. Responde solo con JSON."
   > User: "Analiza este intercambio y extrae hechos nuevos que valga la pena recordar sobre el paciente: datos médicos, preferencias, o recomendaciones dadas. No dupliques hechos ya existentes. Devuelve un JSON array con objetos {fact, category} donde category es 'medical', 'preference', o 'recommendation'. Si no hay nada nuevo, devuelve []."
4. Parse JSON response. Ignore malformed output (silent no-op).
5. Save valid new facts to `PatientMemory`.

**Fallback when `CELERY_ENABLED=False`:** call the task body function directly (synchronously) wrapped in `try/except`, so dev environments work without Redis/Celery.

### Redis cache keys

- `analyte_snapshot:{user_id}` — full analyte snapshot JSON, TTL 3h
- Invalidated (deleted) on successful `POST /api/v2/documents`

---

## Prompt Redesign

### System prompt (new)

```
Eres NephroAI, un asistente personal de salud especializado en nefrología y
nutrición renal. Acompañas al paciente {nombre} en el seguimiento de sus
análisis de laboratorio.

No eres médico, no diagnosticas ni prescribes medicamentos. Pero sí puedes:
- Explicar qué significan sus valores de laboratorio en lenguaje sencillo
- Dar consejos prácticos de alimentación y estilo de vida
- Recordar lo que el paciente ha compartido contigo antes
- Notar mejoras o cambios en sus tendencias

Adapta tu tono y formato según el tipo de pregunta:
- Pregunta simple o conversacional → respuesta corta y directa, sin estructura rígida
- Pregunta de revisión general → usa estructura clara con puntos clave
- Conversación continua → tono cercano, usa el nombre del paciente cuando sea natural

Lo que recuerdas del paciente:
{memoria_del_paciente}

Siempre responde en español.
```

If `PatientMemory` is empty, `{memoria_del_paciente}` is replaced with: `"Aún no tienes información guardada sobre este paciente."`

### User prompt (simplified)

```
Pregunta: {question}

Período considerado: últimos {days} días.

Métricas relevantes (hasta 5):
{relevant_metrics_json}

Todos los análisis disponibles del paciente: {analyte_names_list}

{doctor_notes_if_any}
```

No more rigid structure instructions in every user prompt — the system prompt handles tone adaptation.

---

## Frontend Changes

### New layout: Chat page

```
┌─────────────────────────────────────────────┐
│  Sidebar (260px)      │  Chat area           │
│  ─────────────────    │  ─────────────────   │
│  [+ Nuevo chat]       │  [mensajes]          │
│                       │                      │
│  Hoy                  │                      │
│  > Mis análisis...    │                      │
│  > Qué significa...   │                      │
│                       │                      │
│  Esta semana          │                      │
│  > Creatinina alta    │  [formulario]        │
└─────────────────────────────────────────────┘
```

Sidebar groups sessions by date: Hoy / Esta semana / Este mes / Anterior.
On mobile: sidebar hidden by default, toggled via hamburger button in chat header.

### New components

- **`chat-sidebar.component`** — session list, "Nuevo chat" button, date grouping, delete session
- **`chat-memory-panel.component`** — list of memory facts grouped by category, delete button per fact, accessible from a settings/memory icon in the chat header

### Modified components

- **`chat-page.component`** — manages active `session_id`, loads `ChatMessageRecord[]` from API and maps to existing `ChatMessage[]` UI model when selecting a session, passes `session_id` to `adviceService.ask()`; on "Nuevo chat" creates a new session via `createSession()`
- **`advice.service.ts`** — adds `getSessions()`, `createSession()`, `getMessages(id)`, `deleteSession(id)`, `getMemory()`, `deleteMemory(id)`; updates `ask()` to accept and return `session_id`
- **`advice.model.ts`** — add `session_id: number` to `AdviceResponseModel`
- **`chat-shell.component`** — no changes (reused as-is)

> **Frontend naming note:** The existing `ChatMessage` interface (`{question, answer, metrics, disclaimer, timestamp}`) in `chat.model.ts` is the UI display model and is **not renamed**. The new API response type for session messages uses `ChatSessionMessage` (`{role, content, created_at}`) defined in a new `chat-session.model.ts`.

### i18n keys to add (es/en/ru)

```
chat.newChat, chat.today, chat.thisWeek, chat.thisMonth, chat.earlier,
chat.deleteSession, chat.memory, chat.memoryTitle, chat.memoryEmpty,
chat.memoryDeleteFact, chat.memoryCategories.medical,
chat.memoryCategories.preference, chat.memoryCategories.recommendation
```

---

## What Does NOT Change

- `chat-shell.component` — reused unchanged
- `ChatMessage` UI model in `chat.model.ts` — not renamed
- `_openai_chat_completion(system, user)` — not modified, kept for other callers
- Auth, JWT, V2 pipeline — untouched
- Doctor panel — untouched
- Mobile app — can be updated separately in a future session

---

## Success Criteria

1. User can create multiple chat sessions and switch between them via sidebar.
2. AI uses full conversation history (last 10 messages) in each response.
3. AI uses patient memory facts in system prompt from the second conversation onward.
4. After each response, new facts are extracted asynchronously (no latency added to response).
5. Patient can view and delete individual memory facts.
6. Analyte snapshot is cached in Redis; only top-5 relevant metrics sent per request.
7. AI responses vary in tone/structure based on the type of question asked.
8. Sidebar collapses on mobile.
9. Works in dev environment with `CELERY_ENABLED=False` without errors.
