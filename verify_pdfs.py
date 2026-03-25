"""
Показывает извлечённые метрики рядом с evidence-цитатой из документа.
Сравнивай evidence с оригинальным PDF глазами.

Запуск:
    backend\.venv\Scripts\python verify_pdfs.py
"""
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("backend/.env")
sys.path.insert(0, str(Path(__file__).parent))
from backend.v2.extractor import extract

FOLDER = Path("pdf_check")


async def verify_pdf(pdf_path: Path):
    print(f"\n{'='*80}")
    print(f"  {pdf_path.name}")
    print(f"{'='*80}")

    try:
        result = await extract(pdf_path.read_bytes())
    except Exception as e:
        print(f"  ПАРСЕР УПАЛ: {e}")
        return

    print(f"  Дата: {result.analysis_date}  |  Пол: {result.patient_sex}  |  Возраст: {result.patient_age}")
    print(f"  Метрик: {len(result.metrics)}")
    if result.warnings:
        print(f"  Предупреждения: {result.warnings}")

    print(f"\n  {'Метрика':<40} {'Значение':<15} {'Ед.':<12}  Evidence (цитата из PDF)")
    print(f"  {'-'*40} {'-'*15} {'-'*12}  {'-'*40}")

    for m in result.metrics:
        val = str(m.value_numeric) if m.value_numeric is not None else repr(m.value_text)
        unit = m.unit or ""
        evidence = (m.evidence or "").replace("\n", " ")[:60]
        print(f"  {m.raw_name:<40} {val:<15} {unit:<12}  {evidence}")


async def main():
    pdfs = sorted(FOLDER.glob("*.pdf"))
    if not pdfs:
        print("Папка pdf_check/ пустая.")
        return
    for pdf_path in pdfs:
        await verify_pdf(pdf_path)


asyncio.run(main())
