# Lab Import Backend Module

Модуль для импорта лабораторных анализов из PDF файлов.

**Новое:** Поддержка LLM-based нормализации через AITunnel! См. [README_LLM.md](README_LLM.md)

## Установка

```bash
pip install -r requirements.txt
```

### Опциональная конфигурация LLM

Если хотите использовать LLM-нормализацию (улучшенная точность):

1. Получите API ключ на https://docs.aitunnel.ru
2. Создайте файл `.env` в папке `backend/`:

```env
USE_LLM_NORMALIZATION=true
AITUNNEL_API_KEY=sk-aitunnel-your-key
AITUNNEL_MODEL=deepseek-r1
```

Подробнее см. [README_LLM.md](README_LLM.md)

## Структура модуля

- `models.py` - Pydantic модели данных (ImportedLabItem, ImportJson)
- `pdf_parser.py` - Извлечение текста из PDF и парсинг анализов
- `database.py` - SQLAlchemy модели и функции для работы с БД
- `main.py` - FastAPI приложение с эндпоинтами
- `test_pdf_parser.py` - Юнит-тесты

## Использование

### Запуск API сервера

```bash
uvicorn main:app --reload
```

API будет доступен на `http://127.0.0.1:8000`

### Интерактивная документация

После запуска сервера доступна автоматическая документация:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **Главная страница**: http://127.0.0.1:8000 (с инструкциями)

### Эндпоинты

#### POST /api/preview

Предварительный просмотр результатов парсинга без сохранения в БД.

**Параметры:**
- `file`: PDF файл (multipart/form-data)
- `patient_id`: ID пациента (string, form-data)

**Ответ:**
```json
{
  "patient_id": "123",
  "items": [
    {
      "analyte_name": "Glucosa",
      "value": 94.2,
      "unit": "mg/dL",
      "material": null,
      "taken_at": null,
      "ref_range": "70 a 100"
    }
  ],
  "source_pdf": "report.pdf"
}
```

#### POST /api/import

Импорт результатов и сохранение в БД.

**Параметры:**
- `file`: PDF файл (multipart/form-data)
- `patient_id`: ID пациента (string, form-data)

**Ответ:**
```json
{
  "status": "ok",
  "items_count": 5
}
```

## Тестирование

### Юнит-тесты

Запуск тестов:

```bash
pytest test_pdf_parser.py -v
```

### Тестирование API

1. **Через Swagger UI** (рекомендуется):
   - Откройте http://127.0.0.1:8000/docs
   - Выберите эндпоинт и нажмите "Try it out"
   - Загрузите PDF файл и укажите patient_id

2. **Через curl**:
   ```bash
   curl -X POST "http://127.0.0.1:8000/api/preview" \
     -F "file=@report.pdf" \
     -F "patient_id=123"
   ```

3. **Через Python скрипт**:
   ```bash
   python test_api.py report.pdf 123
   ```

## Ограничения

- Работает только с PDF, имеющими текстовый слой
- Если PDF содержит только изображения (без текстового слоя), будет выброшено исключение `NoTextLayerError`
- OCR не используется (согласно требованиям)

## Пример использования

```python
from pdf_parser import parse_pdf_to_import_json

with open("report.pdf", "rb") as f:
    pdf_bytes = f.read()

import_data = parse_pdf_to_import_json(
    pdf_bytes=pdf_bytes,
    patient_id="123",
    source_pdf="report.pdf"
)

print(f"Parsed {len(import_data.items)} items")
for item in import_data.items:
    print(f"{item.analyte_name}: {item.value} {item.unit or ''}")
```

