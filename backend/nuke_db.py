import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 1. Загружаем переменные окружения
load_dotenv()

# 2. Берем URL из .env или подставляем твой локальный дефолт
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/medic"

print(f"Попытка подключения к: {DATABASE_URL}")

# 3. Создаем движок
engine = create_engine(DATABASE_URL)

def nuke():
    print("Начинаю снос таблиц...")
    try:
        with engine.connect() as conn:
            # Выполняем удаление таблиц
            # CASCADE снесет таблицу, даже если на неё ссылаются другие
            conn.execute(text("DROP TABLE IF EXISTS lab_results CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS patient_imports CASCADE;"))
            
            # В SQLAlchemy 2.0+ нужно обязательно делать commit
            conn.commit()
            
        print("✓ ТАБЛИЦЫ УДАЛЕНЫ УСПЕШНО.")
        print("Теперь запускай бэкенд: uvicorn main:app --reload")
    except Exception as e:
        print(f"❌ Ошибка при удалении: {e}")

if __name__ == "__main__":
    nuke()