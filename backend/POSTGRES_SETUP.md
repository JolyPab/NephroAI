## PostgreSQL setup guide

Ниже пошагово, чтобы можно было «за ручку» перейти с SQLite на PostgreSQL и не бояться сломать окружение.

### 1. Поднять базу через Docker

1. Установи Docker Desktop (если ещё не установлен).
2. В корне репозитория выполни:
   ```bash
   docker compose up -d postgres
   ```
   Это создаст контейнер с PostgreSQL 16, пробросит порт `5432` и поднимет volume `postgres-data`.

### 2. Настроить `.env`

В `backend/.env` укажи строку подключения (можно просто заменить существующий `DB_URL`):
```env
DB_URL=postgresql+psycopg2://medic:medic@localhost:5432/medic
```
При необходимости можно завести отдельные значения `DATABASE_URL` / `DB_URL` для dev и prod.

### 3. Установить зависимости

```bash
cd backend
pip install -r requirements.txt
```
Добавлен пакет `psycopg2-binary`, без него SQLAlchemy не сможет говорить с Postgres.

### 4. Применить миграции (пока создаём схему «с нуля»)

Раз ты не переносишь старые данные, достаточно один раз запустить приложение, чтобы `init_db()` создал таблицы:
```bash
uvicorn main:app --reload
```
В логах появится `[INFO] ... Connection established`, после чего можно остановить `uvicorn`.

### 5. Проверить

- Создай тестового пользователя через `POST /api/auth/register`.
- Залогинься, попробуй загрузить PDF или расшарить данные врачу.
- Убедись, что в базе (`docker exec -it medic-postgres-1 psql ...`) появились строки.

### 6. Остановка / перезапуск Postgres

```bash
docker compose stop postgres
docker compose start postgres
```
Volume `postgres-data` сохраняет содержимое между перезапусками.

### 7. Полезные команды

- Подключиться к базе:
  ```bash
  docker exec -it medic-postgres-1 psql -U medic -d medic
  ```
- Посмотреть логи Postgres:
  ```bash
  docker logs -f medic-postgres-1
  ```

Эти шаги работают одинаково как на Windows, так и на macOS/Linux (если установлен Docker). Когда дойдём до продакшена, укажем уже боевой `DB_URL` с адресом хостинга.
