# CLAUDE.md

**NephroAI** — медицинское SaaS, лабораторные анализы, Эквадор. UI и AI-ответы всегда на испанском.

## Obsidian Knowledge Vault

Хранилище знаний: `C:\Users\jolypab\Documents\CODE\nephroai-vault\`

### При старте сессии
Прочитай `00-home/index.md` и `00-home/текущие-приоритеты.md`.
Если задача касается модуля — прочитай релевантную заметку из `knowledge/`.

### При завершении (пользователь: "сохрани сессию")
1. Создай заметку в `sessions/` с датой
2. Обнови `текущие-приоритеты.md`
3. Если принято решение — создай в `knowledge/decisions/`
4. Если найден баг — создай в `knowledge/debugging/`
5. Обнови `index.md` если появились новые заметки

---

## Стек

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, PostgreSQL (prod) / SQLite (dev), Redis + Celery
- **Frontend:** Angular 20, standalone components, signals, `@ngx-translate/core`
- **Mobile:** Flutter 3.41 (Android), `mobile/lib/core/constants.dart` → API base URL
- **LLM:** OpenAI `gpt-5.2`, `client.responses.parse()` — `backend/v2/`
- **Deploy:** Docker Compose 5 сервисов, GitHub Actions → SCP → SSH, сервер `209.50.54.90`

## Команды

### Backend
```bash
cd backend && uvicorn main:app --reload --port 8000
cd backend && python -m pytest tests/ -v
cd backend && python -m pytest tests/test_foo.py::test_bar -v
```

### Frontend
```bash
cd frontend && npm start        # dev с proxy на :8000
cd frontend && npm run build    # production
```

### Mobile
```bash
cd mobile && flutter run -d <device_id>
cd mobile && flutter build apk --release
```

### Docker (на сервере /root/medic)
```bash
docker compose up -d --build
docker logs medic-api-1
docker logs medic-worker-1
```

## Git

- `main` → автодеплой через GitHub Actions
- Конкретные commit messages: `fix: ...`, `feat: ...`, `refactor: ...`
- Репо должно быть **приватным**

## Критичные детали (не в vault)

- `POST /api/auth/login` возвращает **`accessToken`** (camelCase), не `access_token`
- `backend/main.py` — монолит 3000+ строк, не рефакторить без необходимости
- Legacy: `backend/pdf_parser.py`, `backend/parsing/` — не трогать, только `/api/import`
- Нет Alembic: новые колонки → `ensure_*_columns()` в `database.py` + вызов из `init_db()`
- iOS сборка требует macOS + Xcode; на Windows — только Android APK
