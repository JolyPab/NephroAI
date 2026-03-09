# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NephroAI** — медицинское SaaS-приложение для управления и анализа лабораторных анализов, ориентированное на эквадорский рынок. UI и AI-ответы всегда на испанском.

## Commands

### Backend (Python / FastAPI)

```bash
# Запуск локально (из корня репо)
cd backend && uvicorn main:app --reload --port 8000

# Запуск тестов
cd backend && python -m pytest tests/ -v

# Запуск одного теста
cd backend && python -m pytest tests/test_auth_email_verification.py -v

# Запуск конкретной функции
cd backend && python -m pytest tests/test_v2_documents_management.py::test_list_v2_documents_and_delete_cascades_metrics -v
```

### Frontend (Angular 20)

```bash
cd frontend

# Dev-сервер с proxy на localhost:8000
npm start   # эквивалент ng serve --proxy-config proxy.conf.json

# Production build
npm run build

# Тесты
npm test
```

### Mobile (Flutter)

```bash
cd mobile

# Запустить на подключённом Android устройстве
flutter run -d <device_id>

# Список подключённых устройств
flutter devices

# Собрать release APK
flutter build apk --release
# APK: build/app/outputs/flutter-apk/app-release.apk

# Установить зависимости
flutter pub get

# Hot reload при запущенном flutter run: нажать r в терминале
# Hot restart: нажать R
```

### Docker (production)

```bash
# На сервере: 209.50.54.90, путь /root/medic
docker compose up -d --build   # полный пересборк и запуск
docker compose down            # остановка
docker logs medic-api-1        # логи API
docker logs medic-worker-1     # логи Celery worker
```

### Деплой

Push в `main` → GitHub Actions автоматически:
1. Собирает frontend (`npm run build`)
2. Копирует файлы на сервер по SCP
3. Запускает `docker compose up -d --build`

Конфигурация: `.github/workflows/deploy.yml`.

**Важно:** Репозиторий должен быть **приватным** для безопасности (содержит environment variables).

### Git Workflow

- `main` — production branch, автоматически деплоится
- Коммиты в `main` должны быть проверены и working
- Использовать конкретные commit messages (не "update" или "fix")
- Пример: `fix: prevent chat form from retaining text after API errors`

## Architecture

### Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, PostgreSQL (prod) / SQLite (dev), Redis + Celery
- **Frontend:** Angular 20, standalone components, signals, `@ngx-translate/core`
- **PDF extraction:** OpenAI structured output (`client.responses.parse()`) — `backend/v2/`
- **Email:** Resend SMTP (`smtp.resend.com:587`, user=`resend`)
- **Deploy:** Docker Compose (5 сервисов: db, redis, api, worker, nginx), Cloudflare proxy

### Backend structure

`backend/main.py` — монолит 3000+ строк со всеми роутами. Роуты аутентификации вынесены в `backend/auth_routes.py` (подключён как router), пациенты — в `backend/patient_routes.py`.

**Ключевые модули:**
- `backend/v2/` — V2 пайплайн извлечения данных из PDF: `extractor.py` → `llm_client.py` (OpenAI File API) → `schemas.py` (Pydantic модели с валидацией)
- `backend/database.py` — все SQLAlchemy модели + `init_db()` с ручными миграциями через `ensure_*_columns()`
- `backend/auth.py` — JWT (HS256, 7 дней), PBKDF2 хэширование паролей
- `backend/auth_routes.py` — регистрация с email-верификацией (6-значный код, TTL 10 мин, rate limiting)
- `backend/email_service.py` — SMTP отправка кодов верификации
- `backend/tasks.py` — Celery задача для async обработки PDF

**Нет Alembic** — схема меняется через `ensure_lab_results_columns()` и `ensure_users_columns()` в `database.py`.

### V2 Data Model

Основной флоу данных: PDF → `POST /api/v2/documents` → OpenAI extraction → `V2Document` + `V2Metric` в БД → `/api/v2/series` для time-series графиков.

`V2Metric.analyte_key` — нормализованный идентификатор вида `GLUCOSE__SERUM__NUM`, используется для группировки в серии.

### Frontend structure

Все фичи — lazy-loaded standalone компоненты в `frontend/src/app/features/`:
- `auth/` — логин / регистрация / верификация email
- `patient/` — дашборд пациента, загрузка PDF, чат с AI
- `doctor/` — **B2B панель врача:** список пациентов, графики метрик, заметки на точках данных
- `v2/` — V2 дашборд и детальные серии (основной UI)

Сервисы в `frontend/src/app/core/services/`: `auth.service.ts` (signals), `v2.service.ts` (V2 API), `token.service.ts` (localStorage JWT).

**i18n:** `frontend/src/assets/i18n/` — `en.json`, `es.json`, `ru.json`. Язык UI всегда `es` для продакшна.

### Doctor / B2B Feature

**Frontend:**
- `doctor/pages/patients/` — список пациентов с доступом (granted_at, latest_analysis_date)
- `doctor/pages/patient-detail/` — детальный вид с графиками + система заметок врача на конкретные точки

**Backend:**
- `/api/v2/doctor/patients` — список пациентов врача (требует `is_doctor=true`)
- `/api/v2/doctor/patients/{patient_id}/analytes` — метрики пациента
- `/api/v2/doctor/patients/{patient_id}/series` — история значений с графиками
- `/api/v2/notes` — CRUD заметок врача на точки данных
- `DoctorGrant` таблица — регулирует доступ врача к пациентам (врач получает доступ через грант от пациента)
- `_ensure_doctor_access()` хелпер — проверяет врачебный доступ перед возвратом данных

**Важно:** Врачебный доступ проверяется по `DoctorGrant.doctor_id` или `DoctorGrant.doctor_email` (для email-привязанных грантов).

### Authorization pattern

Все защищённые эндпоинты используют `user_id: int = Depends(get_current_user_id)`. Доступ к данным пациента всегда фильтруется по `user_id`. Врачебный доступ через таблицу `DoctorGrant` проверяется хелпером `_ensure_doctor_access()`.

### Environment variables (сервер /root/medic/.env)

```
OPENAI_API_KEY
JWT_SECRET
EMAIL_CODE_SALT
SMTP_HOST / SMTP_PORT / SMTP_USERNAME / SMTP_PASSWORD / SMTP_FROM_EMAIL / SMTP_USE_TLS
PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET / PAYPAL_PLAN_ID / PAYPAL_BASE_URL
DATABASE_URL  # задаётся в docker-compose.yml напрямую
```

### Legacy code (не трогать, но знать)

`backend/pdf_parser.py`, `backend/vision_parser.py`, `backend/parsing/` — старый regex/OCR пайплайн, используется только в `/api/import`. V2 пайплайн (`backend/v2/`) — основной и единственный рекомендуемый путь.

## Known Issues & Fixes

### Chat Form Cleanup (Fixed)
- **Баг:** Форма не очищалась при ошибке API → пользователь повторно отправлял старый preset вопрос
- **Решение:** Используется `finalize()` оператор (RxJS) для гарантии очистки в обоих случаях (success/error)
- **Файл:** `frontend/src/app/features/patient/pages/chat/chat-page.component.ts` (lines 95-99)
- **Дата фикса:** 2026-03-04

### Mobile App (Flutter)

`mobile/` — Flutter проект, реиспользует Backend API без изменений.

**Stack:** Flutter 3.41, Dart, dio (HTTP), shared_preferences (JWT), fl_chart (графики), file_picker (PDF), go_router (навигация).

**API base URL:** `http://209.50.54.90/api` (production) — в `mobile/lib/core/constants.dart`.

**Структура `mobile/lib/`:**
- `core/` — api_client.dart (Dio + JWT interceptor), storage.dart, theme.dart, constants.dart
- `models/` — user, analyte, series, document, advice
- `services/` — auth_service.dart, v2_service.dart, advice_service.dart
- `screens/auth/` — login, register, verify
- `screens/patient/` — dashboard (аналиты), series (график), upload (PDF), chat (AI), profile, share
- `screens/doctor/` — patients list, patient detail
- `widgets/` — AnalyteCard, MetricChart (fl_chart)
- `app.dart` — GoRouter с redirect-логикой (проверка JWT)

**Важно — API response format:**
- `/api/auth/login` возвращает `accessToken` (camelCase), не `access_token`
- `/api/auth/me` возвращает `is_doctor`, `is_verified`

**iOS:** требует macOS + Xcode, на Windows только Android APK.

**Запуск на физическом Android:** включить USB Debugging + Install via USB в Developer Options.

## Future Roadmap

### B2B Enhancements (Priority)
- [ ] Reporting — выгрузка PDF отчетов врачом
- [ ] Invitations — система приглашения пациентов врачом (email)
- [ ] Alerts — уведомления врачу при новых анализах пациента
- [ ] Batch operations — bulk экспорт данных для групп пациентов
