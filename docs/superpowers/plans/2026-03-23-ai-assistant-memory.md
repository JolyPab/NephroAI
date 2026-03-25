# AI Assistant Memory & Sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent multi-session chat history, AI-extracted patient memory, Redis-cached analyte snapshots, and an adaptive prompt to the NephroAI AI assistant.

**Architecture:** Three new DB tables (`ChatSession`, `ChatMessageRecord`, `PatientMemory`) added via `ensure_*` pattern. `/api/advice` gains session awareness and passes conversation history to OpenAI. A new Celery task extracts patient facts asynchronously. Frontend gains a sidebar with session list and a memory panel.

**Tech Stack:** Python/FastAPI, SQLAlchemy, Redis (redis-py), Celery, Angular 20 (standalone+module), `@ngx-translate/core`, Bootstrap Icons.

**Spec:** `docs/superpowers/specs/2026-03-23-ai-assistant-redesign-design.md`

---

## File Map

### Backend — new / modified
| File | Action | Responsibility |
|---|---|---|
| `backend/database.py` | Modify | Add `ChatSession`, `ChatMessageRecord`, `PatientMemory` models + `ensure_chat_tables()` called from `init_db()` |
| `backend/main.py` | Modify | Redis client init, `_openai_chat_completion_with_history()`, chat session CRUD endpoints, memory endpoints, updated `get_advice()` |
| `backend/tasks.py` | Modify | Add `extract_patient_memory` Celery task + stub |

### Backend — new tests
| File | Tests |
|---|---|
| `backend/tests/test_chat_sessions.py` | Session CRUD endpoints |
| `backend/tests/test_chat_memory.py` | PatientMemory endpoints |
| `backend/tests/test_advice_with_history.py` | Updated `get_advice` with session_id, history, caching |

### Frontend — new files
| File | Responsibility |
|---|---|
| `frontend/src/app/core/models/chat-session.model.ts` | `ChatSessionSummary`, `ChatSessionMessage` interfaces |
| `frontend/src/app/features/patient/components/chat-sidebar/chat-sidebar.component.ts` | Session list, date grouping, new chat button |
| `frontend/src/app/features/patient/components/chat-sidebar/chat-sidebar.component.html` | |
| `frontend/src/app/features/patient/components/chat-sidebar/chat-sidebar.component.scss` | |
| `frontend/src/app/features/patient/components/chat-memory-panel/chat-memory-panel.component.ts` | Memory fact list + delete |
| `frontend/src/app/features/patient/components/chat-memory-panel/chat-memory-panel.component.html` | |
| `frontend/src/app/features/patient/components/chat-memory-panel/chat-memory-panel.component.scss` | |

### Frontend — modified files
| File | Change |
|---|---|
| `frontend/src/app/core/models/advice.model.ts` | Add `session_id: number` to `AdviceResponseModel` |
| `frontend/src/app/core/services/advice.service.ts` | Add session + memory API methods; update `ask()` |
| `frontend/src/app/features/patient/pages/chat/chat-page.component.ts` | Session management, history loading, sidebar/memory toggle |
| `frontend/src/app/features/patient/pages/chat/chat-page.component.html` | Two-column layout with sidebar |
| `frontend/src/app/features/patient/pages/chat/chat-page.component.scss` | Sidebar + responsive styles |
| `frontend/src/app/features/patient/patient.module.ts` | Declare new components |
| `frontend/src/assets/i18n/es.json` | New chat.* keys |
| `frontend/src/assets/i18n/en.json` | New chat.* keys |
| `frontend/src/assets/i18n/ru.json` | New chat.* keys |

---

## Task 1: DB Models — ChatSession, ChatMessageRecord, PatientMemory

**Files:**
- Modify: `backend/database.py`

- [ ] **Step 1: Add SQLAlchemy models to `database.py`**

  After the existing `V2DoctorNote` class (search for it to find the right insertion point), add:

  ```python
  class ChatSession(Base):
      __tablename__ = "chat_sessions"
      id = Column(Integer, primary_key=True, index=True)
      user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
      title = Column(String(200), nullable=True)
      created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
      updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
      is_archived = Column(Boolean, default=False, nullable=False)
      messages = relationship("ChatMessageRecord", back_populates="session", cascade="all, delete-orphan")


  class ChatMessageRecord(Base):
      __tablename__ = "chat_message_records"
      id = Column(Integer, primary_key=True, index=True)
      session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
      role = Column(String(20), nullable=False)   # "user" or "assistant"
      content = Column(Text, nullable=False)
      created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
      session = relationship("ChatSession", back_populates="messages")


  class PatientMemory(Base):
      __tablename__ = "patient_memory"
      id = Column(Integer, primary_key=True, index=True)
      user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
      fact = Column(Text, nullable=False)
      category = Column(String(30), nullable=False)  # "medical" | "preference" | "recommendation"
      source_session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)
      created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
      updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
  ```

- [ ] **Step 2: Add `ensure_chat_tables()` and call it from `init_db()`**

  Add after `ensure_users_columns`:

  ```python
  def ensure_chat_tables(engine) -> None:
      """Create chat_sessions, chat_message_records, patient_memory if not present."""
      Base.metadata.create_all(bind=engine)
  ```

  In `init_db()`, add the call:
  ```python
  ensure_chat_tables(engine)
  ```

- [ ] **Step 3: Verify models are importable**

  ```bash
  python -c "from backend.database import ChatSession, ChatMessageRecord, PatientMemory; print('OK')"
  ```
  Expected: `OK` (run from repo root `medic/`)

- [ ] **Step 4: Commit**

  ```bash
  git add backend/database.py
  git commit -m "feat: add ChatSession, ChatMessageRecord, PatientMemory DB models"
  ```

---

## Task 2: Redis Client in `main.py`

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add Redis client initialization near the top of `main.py`**

  Find the block of `import` statements at the top of `backend/main.py`. After the existing imports, add:

  ```python
  import redis as redis_lib

  _redis_client: Optional[redis_lib.Redis] = None

  def _get_redis() -> Optional[redis_lib.Redis]:
      global _redis_client
      if _redis_client is None:
          redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
          try:
              _redis_client = redis_lib.from_url(redis_url, socket_connect_timeout=2)
              _redis_client.ping()
          except Exception:
              _redis_client = None
      return _redis_client
  ```

  `_get_redis()` returns `None` gracefully when Redis is unavailable (dev without Redis). All caching calls must check for `None`.

- [ ] **Step 2: Invalidate cache on document upload**

  In the `create_v2_document` handler (`POST /api/v2/documents`, around line 1100), just before the final `return` (after `db.commit()`), add:

  ```python
  r = _get_redis()
  if r:
      try:
          r.delete(f"analyte_snapshot:{user_id}")
      except Exception:
          pass
  ```

- [ ] **Step 3: Verify no import errors**

  ```bash
  python -c "from backend.main import app; print('OK')"
  ```
  Expected: `OK` (run from repo root `medic/`)

- [ ] **Step 4: Commit**

  ```bash
  git add backend/main.py
  git commit -m "feat: add Redis client helper and analyte cache invalidation on upload"
  ```

---

## Task 3: `_openai_chat_completion_with_history` Helper

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing test**

  Create `backend/tests/test_advice_with_history.py`:

  ```python
  import asyncio
  import datetime as dt
  from unittest.mock import patch
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from backend.database import Base, User, V2Document, V2Metric, ChatSession, ChatMessageRecord
  from backend.main import AdviceRequest, get_advice


  def _setup_db():
      engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
      Base.metadata.create_all(bind=engine)
      return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


  def _seed_user_with_metric(db):
      user = User(email="hist@test.local", hashed_password="x", full_name="Ana García", is_active=True, is_doctor=False)
      db.add(user)
      db.commit()
      db.refresh(user)
      doc = V2Document(user_id=user.id, document_hash="h1", source_filename="a.pdf",
                       analysis_date=dt.datetime(2026, 1, 1), report_date=dt.datetime(2026, 1, 1))
      db.add(doc)
      db.flush()
      db.add(V2Metric(document_id=doc.id, analyte_key="CREATININE__SERUM__NUM",
                      raw_name="Creatinina", specimen="serum", context="random",
                      value_numeric=1.2, unit="mg/dL", page=1, evidence="Creat 1.2"))
      db.commit()
      return user


  def test_advice_creates_session_when_none_provided():
      db = _setup_db()
      user = _seed_user_with_metric(db)
      with patch("backend.main._openai_chat_completion_with_history", return_value="respuesta de prueba"), \
           patch("backend.main._get_redis", return_value=None):
          response = asyncio.run(get_advice(
              req=AdviceRequest(question="Como esta mi creatinina?"),
              user_id=user.id, db=db,
          ))
      assert response.answer == "respuesta de prueba"
      assert response.session_id is not None
      session = db.query(ChatSession).filter_by(user_id=user.id).first()
      assert session is not None
      assert "creatinina" in (session.title or "").lower()
      db.close()


  def test_advice_reuses_existing_session_and_saves_messages():
      db = _setup_db()
      user = _seed_user_with_metric(db)
      session = ChatSession(user_id=user.id, title="")
      db.add(session)
      db.commit()
      db.refresh(session)
      db.add(ChatMessageRecord(session_id=session.id, role="user", content="Hola"))
      db.add(ChatMessageRecord(session_id=session.id, role="assistant", content="Hola, en que puedo ayudarte?"))
      db.commit()

      with patch("backend.main._openai_chat_completion_with_history", return_value="bien") as mock_llm, \
           patch("backend.main._get_redis", return_value=None):
          asyncio.run(get_advice(
              req=AdviceRequest(question="Que significa creatinina alta?", session_id=session.id),
              user_id=user.id, db=db,
          ))
      # History passed to LLM must include prior messages
      call_args = mock_llm.call_args
      messages_arg = call_args[0][1]  # second positional arg
      roles = [m["role"] for m in messages_arg]
      assert "user" in roles
      assert "assistant" in roles
      db.close()
  ```

- [ ] **Step 2: Run test — expect FAIL (function not defined)**

  ```bash
  cd backend && python -m pytest tests/test_advice_with_history.py -v
  ```
  Expected: `FAILED` — `ImportError` or `AttributeError` on `_openai_chat_completion_with_history` / `session_id`.

- [ ] **Step 3: Add `_openai_chat_completion_with_history` to `main.py`**

  Add immediately after `_openai_chat_completion` (around line 745):

  ```python
  def _openai_chat_completion_with_history(system_prompt: str, messages: list[dict]) -> str:
      """Call OpenAI chat completion with a full messages list.

      `messages` is a list of {role, content} dicts in chronological order.
      Uses same retry logic as _openai_chat_completion.
      """
      key = os.getenv("OPENAI_API_KEY")
      model = os.getenv("OPENAI_MODEL", "gpt-4o")
      if not key:
          raise HTTPException(status_code=500, detail="OpenAI API key is missing.")

      url = "https://api.openai.com/v1/chat/completions"
      headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
      full_messages = [{"role": "system", "content": system_prompt}] + messages
      base_payload = {"model": model, "messages": full_messages, "temperature": 0.4}

      preferred_token_param = "max_tokens"
      model_lc = model.lower()
      if model_lc.startswith(("gpt-5", "o1", "o3", "o4")):
          preferred_token_param = "max_completion_tokens"
      token_params = [preferred_token_param, "max_completion_tokens", "max_tokens"]

      resp = None
      last_error_text = ""
      for token_param in dict.fromkeys(token_params):
          payload = dict(base_payload)
          payload[token_param] = 800
          resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
          if resp.status_code < 400:
              break
          last_error_text = resp.text
          error_text_lc = last_error_text.lower()
          can_retry = (resp.status_code == 400 and
                       ("max_tokens" in error_text_lc or "max_completion_tokens" in error_text_lc))
          if not can_retry:
              raise HTTPException(status_code=502, detail=f"OpenAI error: {last_error_text}")

      if resp is None or resp.status_code >= 400:
          raise HTTPException(status_code=502, detail=f"OpenAI error: {last_error_text}")

      data = resp.json()
      try:
          content = data["choices"][0]["message"]["content"]
          if isinstance(content, str):
              return content
          if isinstance(content, list):
              chunks = [item.get("text", "") if isinstance(item, dict) else str(item) for item in content]
              return "\n".join(c for c in chunks if c).strip()
          return str(content)
      except Exception:
          raise HTTPException(status_code=502, detail="Malformed response from OpenAI.")
  ```

- [ ] **Step 4: Add `session_id` to `AdviceRequest` and `AdviceResponse`**

  In `AdviceRequest` (around line 748):
  ```python
  class AdviceRequest(BaseModel):
      question: str
      metric_names: Optional[List[str]] = None
      days: Optional[int] = 180
      language: Optional[str] = None
      session_id: Optional[int] = None   # ← add this
  ```

  In `AdviceResponse` (around line 761):
  ```python
  class AdviceResponse(BaseModel):
      answer: str
      usedMetrics: List[AdviceMetric]
      disclaimer: bool = True
      session_id: int = 0   # ← add this
  ```

- [ ] **Step 5: Run tests — expect PASS**

  ```bash
  cd backend && python -m pytest tests/test_advice_with_history.py -v
  ```
  Expected: `PASSED` (tests will fail until `get_advice` is updated in Task 5 — this step verifies the helper and models compile without errors first; adjust expectation: partial pass ok here)

- [ ] **Step 6: Commit**

  ```bash
  git add backend/main.py
  git commit -m "feat: add _openai_chat_completion_with_history helper and session_id to AdviceRequest/Response"
  ```

---

## Task 4: Chat Session CRUD Endpoints

**Files:**
- Modify: `backend/main.py`
- Create: `backend/tests/test_chat_sessions.py`

- [ ] **Step 1: Write failing tests**

  Create `backend/tests/test_chat_sessions.py`:

  ```python
  import asyncio
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from fastapi.testclient import TestClient
  from backend.database import Base, User, ChatSession, ChatMessageRecord
  from backend.main import app, get_current_user_id, get_db


  def _setup_db():
      engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
      Base.metadata.create_all(bind=engine)
      return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


  def _make_client(db, user_id):
      app.dependency_overrides[get_db] = lambda: db
      app.dependency_overrides[get_current_user_id] = lambda: user_id
      return TestClient(app)


  def _make_user(db):
      user = User(email="sess@test.local", hashed_password="x", full_name="Test", is_active=True, is_doctor=False)
      db.add(user)
      db.commit()
      db.refresh(user)
      return user


  def test_create_and_list_sessions():
      db = _setup_db()
      user = _make_user(db)
      client = _make_client(db, user.id)

      # Create a session
      r = client.post("/api/chat/sessions", json={"title": "Primera consulta"})
      assert r.status_code == 200
      session_id = r.json()["id"]
      assert session_id > 0

      # List sessions
      r = client.get("/api/chat/sessions")
      assert r.status_code == 200
      items = r.json()
      assert len(items) == 1
      assert items[0]["id"] == session_id
      app.dependency_overrides.clear()
      db.close()


  def test_get_session_messages():
      db = _setup_db()
      user = _make_user(db)
      session = ChatSession(user_id=user.id, title="Test")
      db.add(session)
      db.commit()
      db.refresh(session)
      db.add(ChatMessageRecord(session_id=session.id, role="user", content="Hola"))
      db.add(ChatMessageRecord(session_id=session.id, role="assistant", content="Hola!"))
      db.commit()

      client = _make_client(db, user.id)
      r = client.get(f"/api/chat/sessions/{session.id}/messages")
      assert r.status_code == 200
      msgs = r.json()
      assert len(msgs) == 2
      assert msgs[0]["role"] == "user"
      app.dependency_overrides.clear()
      db.close()


  def test_delete_session_cascades_messages():
      db = _setup_db()
      user = _make_user(db)
      session = ChatSession(user_id=user.id, title="Del")
      db.add(session)
      db.commit()
      db.refresh(session)
      db.add(ChatMessageRecord(session_id=session.id, role="user", content="bye"))
      db.commit()

      client = _make_client(db, user.id)
      r = client.delete(f"/api/chat/sessions/{session.id}")
      assert r.status_code == 200

      remaining = db.query(ChatMessageRecord).filter_by(session_id=session.id).count()
      assert remaining == 0
      app.dependency_overrides.clear()
      db.close()


  def test_cannot_access_other_users_session():
      db = _setup_db()
      user1 = _make_user(db)
      user2 = User(email="other@test.local", hashed_password="x", full_name="Other", is_active=True, is_doctor=False)
      db.add(user2)
      db.commit()
      db.refresh(user2)
      session = ChatSession(user_id=user1.id, title="Private")
      db.add(session)
      db.commit()
      db.refresh(session)

      client = _make_client(db, user2.id)
      r = client.get(f"/api/chat/sessions/{session.id}/messages")
      assert r.status_code == 404
      app.dependency_overrides.clear()
      db.close()
  ```

- [ ] **Step 2: Run tests — expect FAIL**

  ```bash
  cd backend && python -m pytest tests/test_chat_sessions.py -v
  ```
  Expected: `FAILED` — 404 on `/api/chat/sessions`.

- [ ] **Step 3: Add endpoints to `main.py`**

  Add Pydantic models (near other response models):

  ```python
  class ChatSessionCreate(BaseModel):
      title: Optional[str] = None

  class ChatSessionItem(BaseModel):
      id: int
      title: Optional[str]
      updated_at: Optional[str]
      preview: Optional[str] = None

  class ChatSessionMessageItem(BaseModel):
      id: int
      role: str
      content: str
      created_at: str
  ```

  Add endpoints (before `@app.post("/api/advice")`):

  ```python
  @app.get("/api/chat/sessions", response_model=List[ChatSessionItem])
  async def list_chat_sessions(
      user_id: int = Depends(get_current_user_id),
      db: Session = Depends(get_db),
  ):
      sessions = (
          db.query(ChatSession)
          .filter(ChatSession.user_id == user_id, ChatSession.is_archived == False)
          .order_by(ChatSession.updated_at.desc())
          .limit(50)
          .all()
      )
      result = []
      for s in sessions:
          last_msg = (
              db.query(ChatMessageRecord)
              .filter(ChatMessageRecord.session_id == s.id)
              .order_by(ChatMessageRecord.created_at.desc())
              .first()
          )
          result.append(ChatSessionItem(
              id=s.id,
              title=s.title,
              updated_at=s.updated_at.isoformat() if s.updated_at else None,
              preview=(last_msg.content[:80] if last_msg else None),
          ))
      return result


  @app.post("/api/chat/sessions", response_model=ChatSessionItem)
  async def create_chat_session(
      body: ChatSessionCreate,
      user_id: int = Depends(get_current_user_id),
      db: Session = Depends(get_db),
  ):
      session = ChatSession(user_id=user_id, title=body.title or "")
      db.add(session)
      db.commit()
      db.refresh(session)
      return ChatSessionItem(
          id=session.id,
          title=session.title,
          updated_at=session.updated_at.isoformat() if session.updated_at else None,
      )


  @app.get("/api/chat/sessions/{session_id}/messages", response_model=List[ChatSessionMessageItem])
  async def get_session_messages(
      session_id: int,
      user_id: int = Depends(get_current_user_id),
      db: Session = Depends(get_db),
  ):
      session = db.query(ChatSession).filter(
          ChatSession.id == session_id, ChatSession.user_id == user_id
      ).first()
      if not session:
          raise HTTPException(status_code=404, detail="Session not found")
      msgs = (
          db.query(ChatMessageRecord)
          .filter(ChatMessageRecord.session_id == session_id)
          .order_by(ChatMessageRecord.created_at.asc())
          .all()
      )
      return [ChatSessionMessageItem(
          id=m.id, role=m.role, content=m.content,
          created_at=m.created_at.isoformat(),
      ) for m in msgs]


  @app.delete("/api/chat/sessions/{session_id}")
  async def delete_chat_session(
      session_id: int,
      user_id: int = Depends(get_current_user_id),
      db: Session = Depends(get_db),
  ):
      session = db.query(ChatSession).filter(
          ChatSession.id == session_id, ChatSession.user_id == user_id
      ).first()
      if not session:
          raise HTTPException(status_code=404, detail="Session not found")
      db.query(ChatMessageRecord).filter(ChatMessageRecord.session_id == session_id).delete()
      db.delete(session)
      db.commit()
      return {"deleted": session_id}
  ```

  > Note: the test reads `r.json()["id"]` (not `session_id`) — `ChatSessionItem` uses `id` as the primary key field.

- [ ] **Step 4: Run tests — expect PASS**

  ```bash
  cd backend && python -m pytest tests/test_chat_sessions.py -v
  ```
  Expected: all 4 PASSED.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/main.py backend/tests/test_chat_sessions.py
  git commit -m "feat: add chat session CRUD endpoints"
  ```

---

## Task 5: Patient Memory Endpoints

**Files:**
- Modify: `backend/main.py`
- Create: `backend/tests/test_chat_memory.py`

- [ ] **Step 1: Write failing tests**

  Create `backend/tests/test_chat_memory.py`:

  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from fastapi.testclient import TestClient
  from backend.database import Base, User, PatientMemory
  from backend.main import app, get_current_user_id, get_db


  def _setup_db():
      engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
      Base.metadata.create_all(bind=engine)
      return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


  def _make_user(db):
      u = User(email="mem@test.local", hashed_password="x", full_name="Mem", is_active=True, is_doctor=False)
      db.add(u); db.commit(); db.refresh(u)
      return u


  def _make_client(db, user_id):
      app.dependency_overrides[get_db] = lambda: db
      app.dependency_overrides[get_current_user_id] = lambda: user_id
      return TestClient(app)


  def test_list_memory_facts():
      db = _setup_db()
      user = _make_user(db)
      db.add(PatientMemory(user_id=user.id, fact="Toma metformina", category="medical"))
      db.add(PatientMemory(user_id=user.id, fact="No le gustan los consejos sobre agua", category="preference"))
      db.commit()

      client = _make_client(db, user.id)
      r = client.get("/api/chat/memory")
      assert r.status_code == 200
      facts = r.json()
      assert len(facts) == 2
      categories = {f["category"] for f in facts}
      assert "medical" in categories
      app.dependency_overrides.clear()
      db.close()


  def test_delete_memory_fact():
      db = _setup_db()
      user = _make_user(db)
      mem = PatientMemory(user_id=user.id, fact="Dato a borrar", category="medical")
      db.add(mem); db.commit(); db.refresh(mem)

      client = _make_client(db, user.id)
      r = client.delete(f"/api/chat/memory/{mem.id}")
      assert r.status_code == 200
      assert db.query(PatientMemory).filter_by(id=mem.id).first() is None
      app.dependency_overrides.clear()
      db.close()


  def test_cannot_delete_other_users_memory():
      db = _setup_db()
      user1 = _make_user(db)
      user2 = User(email="other2@test.local", hashed_password="x", full_name="Other", is_active=True, is_doctor=False)
      db.add(user2); db.commit(); db.refresh(user2)
      mem = PatientMemory(user_id=user1.id, fact="Privado", category="medical")
      db.add(mem); db.commit(); db.refresh(mem)

      client = _make_client(db, user2.id)
      r = client.delete(f"/api/chat/memory/{mem.id}")
      assert r.status_code == 404
      app.dependency_overrides.clear()
      db.close()
  ```

- [ ] **Step 2: Run tests — expect FAIL**

  ```bash
  cd backend && python -m pytest tests/test_chat_memory.py -v
  ```
  Expected: FAILED — 404 on `/api/chat/memory`.

- [ ] **Step 3: Add memory endpoints and Pydantic models to `main.py`**

  Add Pydantic model:
  ```python
  class PatientMemoryItem(BaseModel):
      id: int
      fact: str
      category: str
      created_at: str
  ```

  Add endpoints (before `@app.post("/api/advice")`):
  ```python
  @app.get("/api/chat/memory", response_model=List[PatientMemoryItem])
  async def list_patient_memory(
      user_id: int = Depends(get_current_user_id),
      db: Session = Depends(get_db),
  ):
      facts = (
          db.query(PatientMemory)
          .filter(PatientMemory.user_id == user_id)
          .order_by(PatientMemory.created_at.desc())
          .all()
      )
      return [PatientMemoryItem(id=f.id, fact=f.fact, category=f.category,
                                created_at=f.created_at.isoformat()) for f in facts]


  @app.delete("/api/chat/memory/{memory_id}")
  async def delete_patient_memory(
      memory_id: int,
      user_id: int = Depends(get_current_user_id),
      db: Session = Depends(get_db),
  ):
      mem = db.query(PatientMemory).filter(
          PatientMemory.id == memory_id, PatientMemory.user_id == user_id
      ).first()
      if not mem:
          raise HTTPException(status_code=404, detail="Memory fact not found")
      db.delete(mem)
      db.commit()
      return {"deleted": memory_id}
  ```

  Also add `PatientMemory` to the import at the top of `main.py` (in the `from backend.database import ...` line).

- [ ] **Step 4: Run tests — expect PASS**

  ```bash
  cd backend && python -m pytest tests/test_chat_memory.py -v
  ```
  Expected: all 3 PASSED.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/main.py backend/tests/test_chat_memory.py
  git commit -m "feat: add patient memory list and delete endpoints"
  ```

---

## Task 6: Updated `get_advice` — Session, History, Caching, New Prompt

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Run existing history tests — expect FAIL**

  ```bash
  cd backend && python -m pytest tests/test_advice_with_history.py -v
  ```
  Expected: FAILED — `get_advice` still uses old logic.

- [ ] **Step 2: Rewrite `get_advice` in `main.py`**

  Replace the body of `get_advice` (lines 2685–2817) with the new implementation below. Keep the function signature identical (`req: AdviceRequest, user_id, db`).

  ```python
  @app.post("/api/advice", response_model=AdviceResponse)
  async def get_advice(
      req: AdviceRequest,
      user_id: int = Depends(get_current_user_id),
      db: Session = Depends(get_db),
  ):
      """Generate wellness-style advice based on recent labs with conversation memory."""
      current_user = db.query(User).filter(User.id == user_id).first()
      if not current_user:
          raise HTTPException(status_code=404, detail="User not found")

      patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
      days = req.days or 180

      # ── 1. Session management ──────────────────────────────────────────────
      if req.session_id:
          session = db.query(ChatSession).filter(
              ChatSession.id == req.session_id,
              ChatSession.user_id == user_id,
          ).first()
          if not session:
              raise HTTPException(status_code=404, detail="Chat session not found")
      else:
          session = ChatSession(user_id=user_id, title="")
          db.add(session)
          db.commit()
          db.refresh(session)

      # ── 2. Save user message ───────────────────────────────────────────────
      db.add(ChatMessageRecord(session_id=session.id, role="user", content=req.question))
      db.commit()

      # ── 3. Load conversation history (last 10 messages) ───────────────────
      history_records = (
          db.query(ChatMessageRecord)
          .filter(ChatMessageRecord.session_id == session.id)
          .order_by(ChatMessageRecord.created_at.asc())
          .limit(10)
          .all()
      )
      history_messages = [{"role": m.role, "content": m.content} for m in history_records]

      # ── 4. Patient memory ─────────────────────────────────────────────────
      memory_facts = (
          db.query(PatientMemory)
          .filter(PatientMemory.user_id == user_id)
          .order_by(PatientMemory.created_at.desc())
          .limit(20)
          .all()
      )
      if memory_facts:
          memory_lines = [f"- [{f.category}] {f.fact}" for f in memory_facts]
          patient_memory_text = "\n".join(memory_lines)
      else:
          patient_memory_text = "Aún no tienes información guardada sobre este paciente."

      # ── 5. Analyte snapshot (Redis cache) ─────────────────────────────────
      cache_key = f"analyte_snapshot:{user_id}"
      r = _get_redis()
      metrics_summary = None
      if r:
          try:
              cached = r.get(cache_key)
              if cached:
                  metrics_summary = json.loads(cached)
          except Exception:
              pass

      if metrics_summary is None:
          metrics_summary = _summarize_metrics_v2(db, user_id=user_id, metric_names=None, days=days)
          if not metrics_summary and patient:
              metrics_summary = _summarize_metrics(db, patient_id=patient.id, metric_names=None, days=days)
          if not metrics_summary:
              metrics_summary = _summarize_metrics_v2(db, user_id=user_id, metric_names=None, days=36500)
          if not metrics_summary and patient:
              metrics_summary = _summarize_metrics(db, patient_id=patient.id, metric_names=None, days=36500)
          if r and metrics_summary:
              try:
                  r.setex(cache_key, 3 * 3600, json.dumps(metrics_summary, ensure_ascii=False))
              except Exception:
                  pass

      if not metrics_summary:
          raise HTTPException(status_code=400, detail="No lab data available for advice.")

      # ── 5b. Select top-5 relevant metrics ─────────────────────────────────
      question_lower = req.question.lower()
      def _relevance_score(name: str) -> int:
          words = name.lower().replace("_", " ").replace("__", " ").split()
          return sum(1 for w in words if w in question_lower)

      sorted_names = sorted(metrics_summary.keys(), key=_relevance_score, reverse=True)
      top_names = sorted_names[:5] if len(sorted_names) > 5 else sorted_names
      relevant_metrics = {k: metrics_summary[k] for k in top_names}
      all_analyte_names = ", ".join(sorted_names)

      # ── 6. Doctor notes ───────────────────────────────────────────────────
      v2_notes = (
          db.query(V2DoctorNote)
          .filter(V2DoctorNote.patient_user_id == user_id, V2DoctorNote.visibility == "patient")
          .order_by(V2DoctorNote.updated_at.desc())
          .limit(5)
          .all()
      )
      notes_lines = []
      for n in v2_notes:
          meta = " · ".join(p for p in [n.analyte_key or "", n.t.isoformat() if n.t else ""] if p)
          notes_lines.append(f"- [{meta}] {n.note}" if meta else f"- {n.note}")
      if patient:
          legacy_notes = (
              db.query(DoctorNote)
              .filter(DoctorNote.patient_id == patient.id)
              .order_by(DoctorNote.created_at.desc())
              .limit(3)
              .all()
          )
          for n in legacy_notes:
              meta_parts = [p for p in [n.metric_name or "", n.metric_time or ""] if p]
              prefix = f"[{' · '.join(meta_parts)}] " if meta_parts else ""
              notes_lines.append(f"- {prefix}{n.text}")

      # ── 7. Build prompts ──────────────────────────────────────────────────
      patient_name = current_user.full_name or "el paciente"
      system_prompt = (
          f"Eres NephroAI, un asistente personal de salud especializado en nefrología y "
          f"nutrición renal. Acompañas al paciente {patient_name} en el seguimiento de sus "
          f"análisis de laboratorio.\n\n"
          "No eres médico, no diagnosticas ni prescribes medicamentos. Pero sí puedes:\n"
          "- Explicar qué significan sus valores de laboratorio en lenguaje sencillo\n"
          "- Dar consejos prácticos de alimentación y estilo de vida\n"
          "- Recordar lo que el paciente ha compartido contigo antes\n"
          "- Notar mejoras o cambios en sus tendencias\n\n"
          "Adapta tu tono y formato según el tipo de pregunta:\n"
          "- Pregunta simple o conversacional → respuesta corta y directa, sin estructura rígida\n"
          "- Pregunta de revisión general → usa estructura clara con puntos clave\n"
          "- Conversación continua → tono cercano, usa el nombre del paciente cuando sea natural\n\n"
          f"Lo que recuerdas del paciente:\n{patient_memory_text}\n\n"
          "Siempre responde en español."
      )

      user_prompt_parts = [
          f"Pregunta: {req.question}",
          f"Período considerado: últimos {days} días.",
          "Métricas relevantes (hasta 5):",
          json.dumps(relevant_metrics, ensure_ascii=False, indent=2),
          f"Todos los análisis disponibles del paciente: {all_analyte_names}",
      ]
      if notes_lines:
          user_prompt_parts.append("Notas del médico (recientes):")
          user_prompt_parts.extend(notes_lines)
      user_prompt = "\n".join(user_prompt_parts)

      # Replace last history entry's content with enriched user_prompt
      if history_messages and history_messages[-1]["role"] == "user":
          history_messages[-1]["content"] = user_prompt
      else:
          history_messages.append({"role": "user", "content": user_prompt})

      # ── 8. Call OpenAI ────────────────────────────────────────────────────
      # history_messages already contains all prior turns + the enriched user_prompt as last entry
      answer = _openai_chat_completion_with_history(system_prompt, history_messages)
      if isinstance(answer, str):
          answer = answer.strip()
      if not answer or _is_low_signal_advice(answer):
          answer = _build_deterministic_advice(metrics_summary, "es", days)

      # ── 9. Save assistant message ─────────────────────────────────────────
      db.add(ChatMessageRecord(session_id=session.id, role="assistant", content=answer))
      if not session.title:
          session.title = req.question[:60]
      session.updated_at = dt.datetime.utcnow()
      db.commit()

      # ── 10. Async memory extraction ───────────────────────────────────────
      from backend.tasks import extract_patient_memory, CELERY_ENABLED as _CELERY_ENABLED
      if _CELERY_ENABLED:
          extract_patient_memory.delay(session.id, user_id)
      else:
          try:
              from backend.tasks import _run_extract_patient_memory
              _run_extract_patient_memory(session.id, user_id)
          except Exception:
              pass

      # ── 11. Build response ────────────────────────────────────────────────
      used_metrics = [
          AdviceMetric(name=name, value=values[0].get("value"), unit=values[0].get("unit"))
          for name, values in metrics_summary.items()
          if values
      ]
      return AdviceResponse(answer=answer, usedMetrics=used_metrics, disclaimer=True, session_id=session.id)
  ```

  > Note: The step "Replace last history entry" has a duplicate call. Clean it up: pass `history_messages` directly (it already has the enriched user_prompt as last entry). Remove the first `answer = ...` call.

- [ ] **Step 3: Run advice history tests**

  ```bash
  cd backend && python -m pytest tests/test_advice_with_history.py tests/test_advice_v2_without_patient.py -v
  ```
  Expected: all PASSED. Fix any issues before proceeding.

- [ ] **Step 4: Commit**

  ```bash
  git add backend/main.py
  git commit -m "feat: update get_advice with session history, memory, Redis cache, and adaptive prompt"
  ```

---

## Task 7: Celery Task `extract_patient_memory`

**Files:**
- Modify: `backend/tasks.py`

- [ ] **Step 1: Add `_run_extract_patient_memory` and the Celery task to `tasks.py`**

  At the top, add imports:
  ```python
  import json
  from backend.database import ChatMessageRecord, PatientMemory
  ```

  Add the core function after `_run_process_pdf_task`:

  ```python
  def _run_extract_patient_memory(session_id: int, user_id: int) -> None:
      """Extract patient facts from the last exchange and save to PatientMemory."""
      from backend.main import _openai_chat_completion  # import here to avoid circular
      session = SessionLocal()
      try:
          msgs = (
              session.query(ChatMessageRecord)
              .filter(ChatMessageRecord.session_id == session_id)
              .order_by(ChatMessageRecord.created_at.desc())
              .limit(2)
              .all()
          )
          if len(msgs) < 2:
              return
          # msgs are desc — reverse to [user, assistant]
          msgs = list(reversed(msgs))
          exchange = f"Paciente: {msgs[0].content}\nAsistente: {msgs[1].content}"

          existing = session.query(PatientMemory).filter(PatientMemory.user_id == user_id).all()
          existing_facts = "\n".join(f"- {m.fact}" for m in existing) if existing else "Ninguno."

          system = "Eres un extractor de hechos médicos. Responde solo con JSON válido."
          user_prompt = (
              f"Analiza este intercambio y extrae hechos nuevos que valga la pena recordar sobre el paciente: "
              f"datos médicos, preferencias, o recomendaciones dadas. "
              f"No dupliques hechos ya existentes.\n\n"
              f"Hechos ya guardados:\n{existing_facts}\n\n"
              f"Intercambio:\n{exchange}\n\n"
              f"Devuelve un JSON array con objetos {{\"fact\": str, \"category\": str}} "
              f"donde category es 'medical', 'preference', o 'recommendation'. "
              f"Si no hay nada nuevo, devuelve []."
          )
          raw = _openai_chat_completion(system, user_prompt)
          # Strip markdown fences if present
          raw = raw.strip()
          if raw.startswith("```"):
              raw = "\n".join(raw.split("\n")[1:])
          if raw.endswith("```"):
              raw = raw.rsplit("```", 1)[0]
          facts = json.loads(raw.strip())
          if not isinstance(facts, list):
              return
          for item in facts:
              if not isinstance(item, dict):
                  continue
              fact = item.get("fact", "").strip()
              category = item.get("category", "medical").strip()
              if not fact or category not in ("medical", "preference", "recommendation"):
                  continue
              session.add(PatientMemory(
                  user_id=user_id, fact=fact, category=category, source_session_id=session_id
              ))
          session.commit()
      except Exception:
          pass  # Never fail silently — memory extraction is best-effort
      finally:
          session.close()
  ```

  Add Celery task registration (following the same `if CELERY_ENABLED / else` pattern as `process_pdf_task`):

  ```python
  if CELERY_ENABLED:

      @celery.task(name="extract_patient_memory")
      def extract_patient_memory(session_id: int, user_id: int):
          return _run_extract_patient_memory(session_id, user_id)

  else:

      class _ExtractMemoryStub:
          def delay(self, *args, **kwargs):
              pass  # silent no-op in dev

          def __call__(self, *args, **kwargs):
              return _run_extract_patient_memory(*args, **kwargs)

      extract_patient_memory = _ExtractMemoryStub()
  ```

- [ ] **Step 2: Verify import**

  ```bash
  python -c "from backend.tasks import extract_patient_memory; print('OK')"
  ```
  Expected: `OK` (run from repo root `medic/`)

- [ ] **Step 3: Run all backend tests**

  ```bash
  cd backend && python -m pytest tests/ -v
  ```
  Expected: all previously passing tests still PASS. Fix any regressions.

- [ ] **Step 4: Commit**

  ```bash
  git add backend/tasks.py
  git commit -m "feat: add extract_patient_memory Celery task"
  ```

---

## Task 8: Frontend Models

**Files:**
- Modify: `frontend/src/app/core/models/advice.model.ts`
- Create: `frontend/src/app/core/models/chat-session.model.ts`

- [ ] **Step 1: Add `session_id` to `AdviceResponseModel`**

  In [advice.model.ts](frontend/src/app/core/models/advice.model.ts), change:
  ```typescript
  export interface AdviceResponseModel {
    answer: string;
    usedMetrics: AdviceMetric[];
    disclaimer: boolean;
    session_id: number;   // ← add
  }
  ```

- [ ] **Step 2: Create `chat-session.model.ts`**

  Create `frontend/src/app/core/models/chat-session.model.ts`:
  ```typescript
  export interface ChatSessionSummary {
    id: number;
    title: string | null;
    updated_at: string | null;
    preview: string | null;
  }

  export interface ChatSessionMessage {
    id: number;
    role: 'user' | 'assistant';
    content: string;
    created_at: string;
  }

  export interface PatientMemoryFact {
    id: number;
    fact: string;
    category: 'medical' | 'preference' | 'recommendation';
    created_at: string;
  }
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/app/core/models/
  git commit -m "feat: add ChatSessionSummary, ChatSessionMessage, PatientMemoryFact models; add session_id to AdviceResponseModel"
  ```

---

## Task 9: Update `advice.service.ts`

**Files:**
- Modify: `frontend/src/app/core/services/advice.service.ts`

- [ ] **Step 1: Rewrite `advice.service.ts`**

  Replace the contents of [advice.service.ts](frontend/src/app/core/services/advice.service.ts):

  ```typescript
  import { Injectable, inject } from '@angular/core';
  import { Observable } from 'rxjs';

  import { ApiService } from './api.service';
  import { AdviceResponseModel } from '../models/advice.model';
  import { ChatSessionSummary, ChatSessionMessage, PatientMemoryFact } from '../models/chat-session.model';

  @Injectable({ providedIn: 'root' })
  export class AdviceClientService {
    private readonly api = inject(ApiService);

    ask(
      question: string,
      metricNames?: string[],
      days?: number,
      language?: 'es' | 'en',
      sessionId?: number,
    ): Observable<AdviceResponseModel> {
      return this.api.post<AdviceResponseModel>('/advice', {
        question,
        metricNames,
        days,
        language,
        session_id: sessionId,
      });
    }

    getSessions(): Observable<ChatSessionSummary[]> {
      return this.api.get<ChatSessionSummary[]>('/chat/sessions');
    }

    createSession(): Observable<ChatSessionSummary> {
      return this.api.post<ChatSessionSummary>('/chat/sessions', {});
    }

    getMessages(sessionId: number): Observable<ChatSessionMessage[]> {
      return this.api.get<ChatSessionMessage[]>(`/chat/sessions/${sessionId}/messages`);
    }

    deleteSession(sessionId: number): Observable<unknown> {
      return this.api.delete<unknown>(`/chat/sessions/${sessionId}`);
    }

    getMemory(): Observable<PatientMemoryFact[]> {
      return this.api.get<PatientMemoryFact[]>('/chat/memory');
    }

    deleteMemory(factId: number): Observable<unknown> {
      return this.api.delete<unknown>(`/chat/memory/${factId}`);
    }
  }
  ```

  > Check that `ApiService` has a `delete<T>()` method. If not, add it: `delete<T>(path: string): Observable<T> { return this.http.delete<T>(this.base + path); }`.

- [ ] **Step 2: Verify `ApiService` has `delete`**

  ```bash
  grep -n "delete" frontend/src/app/core/services/api.service.ts
  ```
  If missing, add it to `api.service.ts`.

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/app/core/services/advice.service.ts frontend/src/app/core/services/api.service.ts
  git commit -m "feat: update AdviceClientService with session and memory methods"
  ```

---

## Task 10: i18n Keys

**Files:**
- Modify: `frontend/src/assets/i18n/es.json`
- Modify: `frontend/src/assets/i18n/en.json`
- Modify: `frontend/src/assets/i18n/ru.json`

- [ ] **Step 1: Add keys to `es.json`**

  In the `"chat"` object, add after the last existing key:
  ```json
  "newChat": "Nuevo chat",
  "today": "Hoy",
  "thisWeek": "Esta semana",
  "thisMonth": "Este mes",
  "earlier": "Anterior",
  "deleteSession": "Eliminar conversacion",
  "memory": "Memoria",
  "memoryTitle": "Lo que recuerda el asistente",
  "memoryEmpty": "El asistente aun no ha guardado informacion sobre ti.",
  "memoryDeleteFact": "Olvidar",
  "memoryMedical": "Datos medicos",
  "memoryPreference": "Preferencias",
  "memoryRecommendation": "Recomendaciones"
  ```

- [ ] **Step 2: Add equivalent keys to `en.json`**

  ```json
  "newChat": "New chat",
  "today": "Today",
  "thisWeek": "This week",
  "thisMonth": "This month",
  "earlier": "Earlier",
  "deleteSession": "Delete conversation",
  "memory": "Memory",
  "memoryTitle": "What the assistant remembers",
  "memoryEmpty": "The assistant hasn't saved any information about you yet.",
  "memoryDeleteFact": "Forget",
  "memoryMedical": "Medical data",
  "memoryPreference": "Preferences",
  "memoryRecommendation": "Recommendations"
  ```

- [ ] **Step 3: Add equivalent keys to `ru.json`**

  ```json
  "newChat": "Новый чат",
  "today": "Сегодня",
  "thisWeek": "На этой неделе",
  "thisMonth": "В этом месяце",
  "earlier": "Ранее",
  "deleteSession": "Удалить разговор",
  "memory": "Память",
  "memoryTitle": "Что помнит ассистент",
  "memoryEmpty": "Ассистент ещё не сохранил информацию о вас.",
  "memoryDeleteFact": "Забыть",
  "memoryMedical": "Медицинские данные",
  "memoryPreference": "Предпочтения",
  "memoryRecommendation": "Рекомендации"
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/assets/i18n/
  git commit -m "feat: add i18n keys for chat sessions and memory panel"
  ```

---

## Task 11: `chat-sidebar` Component

**Files:**
- Create: `frontend/src/app/features/patient/components/chat-sidebar/chat-sidebar.component.ts`
- Create: `frontend/src/app/features/patient/components/chat-sidebar/chat-sidebar.component.html`
- Create: `frontend/src/app/features/patient/components/chat-sidebar/chat-sidebar.component.scss`

- [ ] **Step 1: Create `chat-sidebar.component.ts`**

  ```typescript
  import { Component, EventEmitter, Input, OnChanges, Output } from '@angular/core';
  import { CommonModule } from '@angular/common';
  import { TranslateModule } from '@ngx-translate/core';
  import { ChatSessionSummary } from '../../../../core/models/chat-session.model';

  interface SessionGroup {
    labelKey: string;
    sessions: ChatSessionSummary[];
  }

  @Component({
    selector: 'app-chat-sidebar',
    standalone: true,
    imports: [CommonModule, TranslateModule],
    templateUrl: './chat-sidebar.component.html',
    styleUrls: ['./chat-sidebar.component.scss'],
  })
  export class ChatSidebarComponent implements OnChanges {
    @Input() sessions: ChatSessionSummary[] = [];
    @Input() activeSessionId: number | null = null;

    @Output() selectSession = new EventEmitter<number>();
    @Output() newChat = new EventEmitter<void>();
    @Output() deleteSession = new EventEmitter<number>();

    groups: SessionGroup[] = [];

    ngOnChanges(): void {
      this.groups = this.buildGroups(this.sessions);
    }

    private buildGroups(sessions: ChatSessionSummary[]): SessionGroup[] {
      const now = new Date();
      const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
      const startOfWeek = startOfToday - (now.getDay() || 7) * 86400000 + 86400000;
      const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1).getTime();

      const groups: Record<string, ChatSessionSummary[]> = {
        today: [], thisWeek: [], thisMonth: [], earlier: [],
      };

      for (const s of sessions) {
        const ts = s.updated_at ? Date.parse(s.updated_at) : 0;
        if (ts >= startOfToday) groups['today'].push(s);
        else if (ts >= startOfWeek) groups['thisWeek'].push(s);
        else if (ts >= startOfMonth) groups['thisMonth'].push(s);
        else groups['earlier'].push(s);
      }

      return [
        { labelKey: 'chat.today', sessions: groups['today'] },
        { labelKey: 'chat.thisWeek', sessions: groups['thisWeek'] },
        { labelKey: 'chat.thisMonth', sessions: groups['thisMonth'] },
        { labelKey: 'chat.earlier', sessions: groups['earlier'] },
      ].filter(g => g.sessions.length > 0);
    }

    onSelect(id: number): void { this.selectSession.emit(id); }
    onNew(): void { this.newChat.emit(); }
    onDelete(event: Event, id: number): void {
      event.stopPropagation();
      this.deleteSession.emit(id);
    }

    displayTitle(s: ChatSessionSummary): string {
      return (s.title?.trim() || s.preview?.slice(0, 40) || '...') as string;
    }
  }
  ```

- [ ] **Step 2: Create `chat-sidebar.component.html`**

  ```html
  <aside class="sidebar">
    <button class="new-chat-btn" (click)="onNew()">
      <i class="bi bi-plus-lg"></i>
      <span>{{ 'chat.newChat' | translate }}</span>
    </button>

    <nav class="session-list">
      <ng-container *ngFor="let group of groups">
        <p class="group-label">{{ group.labelKey | translate }}</p>
        <button
          class="session-item"
          *ngFor="let session of group.sessions"
          [class.active]="session.id === activeSessionId"
          (click)="onSelect(session.id)"
        >
          <span class="session-title">{{ displayTitle(session) }}</span>
          <button class="delete-btn" (click)="onDelete($event, session.id)" title="{{ 'chat.deleteSession' | translate }}">
            <i class="bi bi-trash3"></i>
          </button>
        </button>
      </ng-container>
    </nav>
  </aside>
  ```

- [ ] **Step 3: Create `chat-sidebar.component.scss`**

  ```scss
  .sidebar {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }

  .new-chat-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: calc(100% - 1rem);
    margin: 0.75rem 0.5rem;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border-color, rgba(255,255,255,0.15));
    border-radius: 0.5rem;
    background: transparent;
    color: inherit;
    cursor: pointer;
    font-size: 0.875rem;
    transition: background 0.15s;

    &:hover { background: rgba(255,255,255,0.07); }
  }

  .session-list {
    flex: 1;
    overflow-y: auto;
    padding: 0 0.25rem 0.75rem;
  }

  .group-label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    opacity: 0.5;
    padding: 0.5rem 0.75rem 0.25rem;
    margin: 0;
  }

  .session-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 0.45rem 0.75rem;
    border: none;
    background: transparent;
    color: inherit;
    cursor: pointer;
    border-radius: 0.4rem;
    font-size: 0.82rem;
    text-align: left;
    transition: background 0.15s;

    &:hover { background: rgba(255,255,255,0.07); }
    &.active { background: rgba(255,255,255,0.12); }

    .delete-btn {
      display: none;
      padding: 0.15rem 0.3rem;
      border: none;
      background: transparent;
      color: inherit;
      cursor: pointer;
      opacity: 0.5;
      border-radius: 0.25rem;
      &:hover { opacity: 1; }
    }

    &:hover .delete-btn { display: flex; }
  }

  .session-title {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/app/features/patient/components/chat-sidebar/
  git commit -m "feat: add ChatSidebarComponent with session list and date grouping"
  ```

---

## Task 12: `chat-memory-panel` Component

**Files:**
- Create: `frontend/src/app/features/patient/components/chat-memory-panel/chat-memory-panel.component.ts`
- Create: `frontend/src/app/features/patient/components/chat-memory-panel/chat-memory-panel.component.html`
- Create: `frontend/src/app/features/patient/components/chat-memory-panel/chat-memory-panel.component.scss`

- [ ] **Step 1: Create `chat-memory-panel.component.ts`**

  ```typescript
  import { Component, EventEmitter, Input, Output } from '@angular/core';
  import { CommonModule } from '@angular/common';
  import { TranslateModule } from '@ngx-translate/core';
  import { PatientMemoryFact } from '../../../../core/models/chat-session.model';

  @Component({
    selector: 'app-chat-memory-panel',
    standalone: true,
    imports: [CommonModule, TranslateModule],
    templateUrl: './chat-memory-panel.component.html',
    styleUrls: ['./chat-memory-panel.component.scss'],
  })
  export class ChatMemoryPanelComponent {
    @Input() facts: PatientMemoryFact[] = [];
    @Output() deleteFact = new EventEmitter<number>();
    @Output() close = new EventEmitter<void>();

    readonly categories = ['medical', 'preference', 'recommendation'] as const;

    factsForCategory(cat: string): PatientMemoryFact[] {
      return this.facts.filter(f => f.category === cat);
    }

    categoryKey(cat: string): string {
      const map: Record<string, string> = {
        medical: 'chat.memoryMedical',
        preference: 'chat.memoryPreference',
        recommendation: 'chat.memoryRecommendation',
      };
      return map[cat] ?? cat;
    }

    onDelete(id: number): void { this.deleteFact.emit(id); }
    onClose(): void { this.close.emit(); }
  }
  ```

- [ ] **Step 2: Create `chat-memory-panel.component.html`**

  ```html
  <div class="memory-panel">
    <div class="memory-header">
      <h4>{{ 'chat.memoryTitle' | translate }}</h4>
      <button class="close-btn" (click)="onClose()"><i class="bi bi-x-lg"></i></button>
    </div>

    <div class="memory-empty" *ngIf="facts.length === 0">
      {{ 'chat.memoryEmpty' | translate }}
    </div>

    <ng-container *ngFor="let cat of categories">
      <ng-container *ngIf="factsForCategory(cat).length > 0">
        <p class="cat-label">{{ categoryKey(cat) | translate }}</p>
        <div class="fact-item" *ngFor="let fact of factsForCategory(cat)">
          <span class="fact-text">{{ fact.fact }}</span>
          <button class="forget-btn" (click)="onDelete(fact.id)">
            {{ 'chat.memoryDeleteFact' | translate }}
          </button>
        </div>
      </ng-container>
    </ng-container>
  </div>
  ```

- [ ] **Step 3: Create `chat-memory-panel.component.scss`**

  ```scss
  .memory-panel {
    padding: 1rem;
    min-width: 280px;
    max-width: 360px;
  }

  .memory-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    h4 { margin: 0; font-size: 0.95rem; }
  }

  .close-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: inherit;
    opacity: 0.6;
    &:hover { opacity: 1; }
  }

  .memory-empty {
    font-size: 0.85rem;
    opacity: 0.6;
    font-style: italic;
  }

  .cat-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
    opacity: 0.5;
    margin: 0.75rem 0 0.25rem;
  }

  .fact-item {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    font-size: 0.82rem;
  }

  .fact-text { flex: 1; line-height: 1.4; }

  .forget-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: inherit;
    font-size: 0.75rem;
    opacity: 0.5;
    white-space: nowrap;
    &:hover { opacity: 1; color: #ef4444; }
  }
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/app/features/patient/components/chat-memory-panel/
  git commit -m "feat: add ChatMemoryPanelComponent"
  ```

---

## Task 13: Update `chat-page.component` — Session Management

**Files:**
- Modify: `frontend/src/app/features/patient/pages/chat/chat-page.component.ts`
- Modify: `frontend/src/app/features/patient/pages/chat/chat-page.component.html`
- Modify: `frontend/src/app/features/patient/pages/chat/chat-page.component.scss`
- Modify: `frontend/src/app/features/patient/patient.module.ts`

- [ ] **Step 1: Rewrite `chat-page.component.ts`**

  Replace the full contents of [chat-page.component.ts](frontend/src/app/features/patient/pages/chat/chat-page.component.ts):

  ```typescript
  import { Component, OnInit, inject } from '@angular/core';
  import { FormBuilder, Validators } from '@angular/forms';
  import { finalize } from 'rxjs/operators';

  import { AdviceClientService } from '../../../../core/services/advice.service';
  import { AdviceResponseModel } from '../../../../core/models/advice.model';
  import { ChatMessage } from '../../../../core/models/chat.model';
  import { ChatSessionSummary, ChatSessionMessage, PatientMemoryFact } from '../../../../core/models/chat-session.model';
  import { V2AnalyteItemResponse } from '../../../../core/models/v2.model';
  import { V2Service } from '../../../../core/services/v2.service';
  import { getAnalyteDisplayName, V2DashboardLang } from '../../../v2/i18n/analyte-display';

  @Component({
    selector: 'app-patient-chat-page',
    standalone: false,
    templateUrl: './chat-page.component.html',
    styleUrls: ['./chat-page.component.scss'],
  })
  export class PatientChatPageComponent implements OnInit {
    private readonly fb = inject(FormBuilder);
    private readonly adviceService = inject(AdviceClientService);
    private readonly v2Service = inject(V2Service);

    // ── Chat state ─────────────────────────────────────────────────────────
    isLoading = false;
    availableMetrics: string[] = [];
    history: ChatMessage[] = [];
    errorMessage = '';
    language: V2DashboardLang = 'es';

    // ── Session state ──────────────────────────────────────────────────────
    sessions: ChatSessionSummary[] = [];
    activeSessionId: number | null = null;
    sidebarOpen = false;

    // ── Memory state ───────────────────────────────────────────────────────
    memoryFacts: PatientMemoryFact[] = [];
    memoryPanelOpen = false;

    // ── Quick prompts ──────────────────────────────────────────────────────
    quickPrompts: string[] = [];
    private readonly promptCopy: Record<V2DashboardLang, { base: string[]; metricTemplate: string }> = {
      en: {
        base: ['Summarize my recent lab trends.', 'Which metrics are out of range?', 'What should I discuss with my doctor?'],
        metricTemplate: 'How did {{metric}} change recently?',
      },
      es: {
        base: ['Resume mis tendencias recientes de laboratorio.', 'Que metricas estan fuera de rango?', 'Que deberia hablar con mi medico?'],
        metricTemplate: 'Como cambio {{metric}} recientemente?',
      },
    };

    readonly chatForm = this.fb.nonNullable.group({
      question: ['', [Validators.required, Validators.minLength(10)]],
      metricNames: [[] as string[]],
      days: [180],
    });

    ngOnInit(): void {
      this.language = 'es';
      this.loadSessions();
      this.v2Service.listAnalytes().subscribe((analytes) => {
        const sorted = this.sortByRecent(analytes ?? []);
        this.availableMetrics = sorted.map(item => this.getDisplayName(item)).slice(0, 40);
        this.buildPrompts();
      });
    }

    // ── Session management ─────────────────────────────────────────────────
    loadSessions(): void {
      this.adviceService.getSessions().subscribe({
        next: (sessions) => {
          this.sessions = sessions;
          if (sessions.length > 0 && this.activeSessionId === null) {
            this.selectSession(sessions[0].id);
          }
        },
        error: () => {},
      });
    }

    selectSession(id: number): void {
      this.activeSessionId = id;
      this.history = [];
      this.sidebarOpen = false;
      this.adviceService.getMessages(id).subscribe({
        next: (msgs) => { this.history = this.mapApiMessages(msgs); },
        error: () => {},
      });
    }

    startNewChat(): void {
      this.adviceService.createSession().subscribe({
        next: (session) => {
          this.sessions = [session, ...this.sessions];
          this.activeSessionId = session.id;
          this.history = [];
          this.sidebarOpen = false;
        },
        error: () => {},
      });
    }

    deleteSession(id: number): void {
      this.adviceService.deleteSession(id).subscribe({
        next: () => {
          this.sessions = this.sessions.filter(s => s.id !== id);
          if (this.activeSessionId === id) {
            this.history = [];
            this.activeSessionId = this.sessions[0]?.id ?? null;
            if (this.activeSessionId) {
              this.selectSession(this.activeSessionId);
            }
          }
        },
        error: () => {},
      });
    }

    // ── Memory management ──────────────────────────────────────────────────
    toggleMemoryPanel(): void {
      if (!this.memoryPanelOpen) {
        this.adviceService.getMemory().subscribe({
          next: (facts) => { this.memoryFacts = facts; },
          error: () => {},
        });
      }
      this.memoryPanelOpen = !this.memoryPanelOpen;
    }

    closeMemoryPanel(): void { this.memoryPanelOpen = false; }

    deleteMemoryFact(id: number): void {
      this.adviceService.deleteMemory(id).subscribe({
        next: () => { this.memoryFacts = this.memoryFacts.filter(f => f.id !== id); },
        error: () => {},
      });
    }

    // ── Quick prompts ──────────────────────────────────────────────────────
    setPrompt(prompt: string): void { this.chatForm.patchValue({ question: prompt }); }

    // ── Submit ─────────────────────────────────────────────────────────────
    submit(): void {
      if (this.chatForm.invalid) {
        this.chatForm.markAllAsTouched();
        return;
      }

      const { question, metricNames, days } = this.chatForm.getRawValue();
      this.isLoading = true;
      this.errorMessage = '';

      const pendingIndex = this.appendPendingMessage(question);

      this.adviceService
        .ask(question, metricNames?.length ? metricNames : undefined, days, this.language, this.activeSessionId ?? undefined)
        .pipe(finalize(() => {
          this.isLoading = false;
          this.chatForm.patchValue({ question: '' });
        }))
        .subscribe({
          next: (response) => {
            if (response.session_id && !this.activeSessionId) {
              this.activeSessionId = response.session_id;
              this.loadSessions();
            }
            this.handleResponse(question, response, pendingIndex);
          },
          error: (err) => {
            this.removePendingMessage(pendingIndex);
            this.errorMessage = err?.error?.detail ?? 'Failed to get advice. Please try again.';
          },
        });
    }

    // ── Helpers ────────────────────────────────────────────────────────────
    private mapApiMessages(msgs: ChatSessionMessage[]): ChatMessage[] {
      const result: ChatMessage[] = [];
      for (let i = 0; i < msgs.length - 1; i += 2) {
        const userMsg = msgs[i];
        const aiMsg = msgs[i + 1];
        if (userMsg?.role === 'user' && aiMsg?.role === 'assistant') {
          result.push({
            question: userMsg.content,
            answer: aiMsg.content,
            metrics: [],
            disclaimer: true,
            timestamp: new Date(userMsg.created_at),
          });
        }
      }
      return result;
    }

    private handleResponse(question: string, response: AdviceResponseModel, pendingIndex: number): void {
      const updatedMessage: ChatMessage = {
        question,
        answer: this.normalizeAdviceAnswer(response.answer),
        metrics: response.usedMetrics,
        disclaimer: response.disclaimer,
        timestamp: this.history[pendingIndex]?.timestamp ?? new Date(),
      };
      this.upsertPendingMessage(pendingIndex, updatedMessage);
    }

    private appendPendingMessage(question: string): number {
      this.history = [...this.history, { question, answer: '', metrics: [], disclaimer: false, timestamp: new Date() }];
      return this.history.length - 1;
    }

    private upsertPendingMessage(index: number, message: ChatMessage): void {
      if (index < 0 || index >= this.history.length) { this.history = [...this.history, message]; return; }
      const next = [...this.history];
      next[index] = message;
      this.history = next;
    }

    private removePendingMessage(index: number): void {
      if (index < 0 || index >= this.history.length) return;
      this.history = this.history.filter((_, i) => i !== index);
    }

    private buildPrompts(): void {
      const copy = this.promptCopy[this.language] ?? this.promptCopy.es;
      const metricPrompts = this.availableMetrics.slice(0, 3).map(m => copy.metricTemplate.replace('{{metric}}', m));
      this.quickPrompts = [...copy.base, ...metricPrompts].slice(0, 6);
    }

    private getDisplayName(item: V2AnalyteItemResponse): string {
      return getAnalyteDisplayName(item.analyte_key, this.language, item.raw_name);
    }

    private sortByRecent(items: V2AnalyteItemResponse[]): V2AnalyteItemResponse[] {
      return [...items].sort((a, b) => this.dateTimestamp(b.last_date) - this.dateTimestamp(a.last_date));
    }

    private dateTimestamp(v: string | null): number {
      if (!v) return 0;
      const ts = Date.parse(v);
      return Number.isFinite(ts) ? ts : 0;
    }

    private normalizeAdviceAnswer(answer: string | null | undefined): string {
      const text = (answer ?? '').trim();
      return text || 'No pude generar un resumen util con los datos actuales. Intenta con una pregunta mas especifica.';
    }
  }
  ```

- [ ] **Step 2: Rewrite `chat-page.component.html`**

  Replace the contents of [chat-page.component.html](frontend/src/app/features/patient/pages/chat/chat-page.component.html):

  ```html
  <div class="chat-page" [class.sidebar-open]="sidebarOpen">
    <!-- Sidebar overlay (mobile) -->
    <div class="sidebar-backdrop" *ngIf="sidebarOpen" (click)="sidebarOpen = false"></div>

    <!-- Sidebar -->
    <div class="sidebar-wrapper" [class.open]="sidebarOpen">
      <app-chat-sidebar
        [sessions]="sessions"
        [activeSessionId]="activeSessionId"
        (selectSession)="selectSession($event)"
        (newChat)="startNewChat()"
        (deleteSession)="deleteSession($event)"
      ></app-chat-sidebar>
    </div>

    <!-- Main chat area -->
    <div class="chat-main">
      <!-- Top bar (mobile toggle + memory button) -->
      <div class="chat-topbar">
        <button class="topbar-btn" (click)="sidebarOpen = !sidebarOpen" title="Historial">
          <i class="bi bi-layout-sidebar"></i>
        </button>
        <div class="topbar-spacer"></div>
        <button class="topbar-btn" (click)="toggleMemoryPanel()" title="{{ 'chat.memory' | translate }}">
          <i class="bi bi-brain"></i>
        </button>
      </div>

      <!-- Memory panel (overlay) -->
      <div class="memory-overlay" *ngIf="memoryPanelOpen">
        <app-chat-memory-panel
          [facts]="memoryFacts"
          (deleteFact)="deleteMemoryFact($event)"
          (close)="closeMemoryPanel()"
        ></app-chat-memory-panel>
      </div>

      <!-- Chat shell -->
      <app-chat-shell
        [titleKey]="'chat.title'"
        [subtitleKey]="'chat.subtitle'"
        [secureKey]="'chat.secure'"
        [emptyKey]="'chat.empty'"
        [placeholderKey]="'chat.questionPh'"
        [minCharsKey]="'chat.minChars'"
        [youKey]="'chat.you'"
        [aiKey]="'chat.ai'"
        [disclaimerKey]="'chat.disclaimer'"
        [history]="history"
        [isLoading]="isLoading"
        [form]="chatForm"
        [quickPrompts]="quickPrompts"
        (submitMessage)="submit()"
        (selectPrompt)="setPrompt($event)"
      ></app-chat-shell>
    </div>
  </div>
  ```

- [ ] **Step 3: Rewrite `chat-page.component.scss`**

  ```scss
  :host {
    display: block;
    height: 100%;
  }

  .chat-page {
    display: flex;
    height: 100%;
    position: relative;
    overflow: hidden;
  }

  // ── Sidebar ───────────────────────────────────────────────────────────────
  .sidebar-wrapper {
    width: 260px;
    flex-shrink: 0;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    overflow: hidden;

    @media (max-width: 768px) {
      position: absolute;
      left: -260px;
      top: 0;
      bottom: 0;
      z-index: 100;
      background: var(--surface-bg, #1a1a2e);
      transition: left 0.25s ease;
      border-right: 1px solid rgba(255, 255, 255, 0.15);

      &.open { left: 0; }
    }
  }

  .sidebar-backdrop {
    display: none;
    @media (max-width: 768px) {
      display: block;
      position: absolute;
      inset: 0;
      z-index: 99;
      background: rgba(0, 0, 0, 0.4);
    }
  }

  // ── Main area ──────────────────────────────────────────────────────────────
  .chat-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    position: relative;
  }

  .chat-topbar {
    display: flex;
    align-items: center;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    gap: 0.5rem;
  }

  .topbar-spacer { flex: 1; }

  .topbar-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: inherit;
    opacity: 0.6;
    padding: 0.35rem 0.5rem;
    border-radius: 0.4rem;
    font-size: 1rem;
    &:hover { opacity: 1; background: rgba(255, 255, 255, 0.07); }
  }

  // ── Memory overlay ─────────────────────────────────────────────────────────
  .memory-overlay {
    position: absolute;
    top: 2.75rem;
    right: 0.75rem;
    z-index: 50;
    background: var(--surface-bg, #1a1a2e);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 0.75rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    max-height: calc(100% - 4rem);
    overflow-y: auto;
  }
  ```

- [ ] **Step 4: Update `patient.module.ts` to declare new components**

  In [patient.module.ts](frontend/src/app/features/patient/patient.module.ts), add imports:

  ```typescript
  import { ChatSidebarComponent } from './components/chat-sidebar/chat-sidebar.component';
  import { ChatMemoryPanelComponent } from './components/chat-memory-panel/chat-memory-panel.component';
  ```

  Add to `imports` array (alongside `V2SeriesPageComponent`):
  ```typescript
  imports: [SharedModule, PatientRoutingModule, V2SeriesPageComponent, V2MetricSelectorComponent,
            ChatSidebarComponent, ChatMemoryPanelComponent],
  ```

- [ ] **Step 5: Build check**

  ```bash
  cd frontend && npm run build 2>&1 | tail -20
  ```
  Expected: build succeeds with no errors. Fix any TypeScript errors before proceeding.

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/src/app/features/patient/
  git commit -m "feat: add chat sidebar, memory panel, and session management to chat page"
  ```

---

## Task 14: Final Integration Check

- [ ] **Step 1: Run all backend tests**

  ```bash
  cd backend && python -m pytest tests/ -v
  ```
  Expected: all tests PASS.

- [ ] **Step 2: Start dev backend and verify new endpoints**

  ```bash
  cd backend && uvicorn main:app --reload --port 8000
  ```

  In another terminal (replace `TOKEN` with a valid JWT from login):
  ```bash
  # List sessions
  curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/chat/sessions

  # List memory
  curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/chat/memory
  ```
  Expected: both return JSON arrays (empty `[]` is fine).

- [ ] **Step 3: Start dev frontend and smoke test**

  ```bash
  cd frontend && npm start
  ```
  Open browser → navigate to Chat page.
  Verify:
  - Sidebar renders (empty if no sessions)
  - "Nuevo chat" button creates a session
  - Sending a message works and populates the session list
  - Memory icon opens the panel (empty on first use)
  - Mobile: sidebar hidden by default, opens on toggle

- [ ] **Step 4: Final commit**

  ```bash
  git add -A
  git commit -m "chore: final integration check — ai assistant memory and sessions"
  ```

---

## Checklist Summary

- [ ] Task 1: DB models added to `database.py`
- [ ] Task 2: Redis client + cache invalidation
- [ ] Task 3: `_openai_chat_completion_with_history` helper + `AdviceRequest`/`AdviceResponse` updated
- [ ] Task 4: Chat session CRUD endpoints + tests
- [ ] Task 5: Patient memory endpoints + tests
- [ ] Task 6: `get_advice` rewritten with history, memory, caching, new prompt
- [ ] Task 7: Celery task `extract_patient_memory`
- [ ] Task 8: Frontend models (`chat-session.model.ts`, `advice.model.ts`)
- [ ] Task 9: `advice.service.ts` updated
- [ ] Task 10: i18n keys added (es/en/ru)
- [ ] Task 11: `chat-sidebar` component
- [ ] Task 12: `chat-memory-panel` component
- [ ] Task 13: `chat-page` component rewritten + layout + module
- [ ] Task 14: Integration check
