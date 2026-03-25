"""
Прогоняет все PDF из папки pdf_check/ через парсер и печатает результат.

Запуск (из корня репо):
    backend\.venv\Scripts\python check_pdfs.py
"""
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv("backend/.env")

sys.path.insert(0, str(Path(__file__).parent))
from backend.v2.extractor import extract

FOLDER = Path("pdf_check")


async def check_all():
    pdfs = sorted(FOLDER.glob("*.pdf"))
    if not pdfs:
        print("Папка pdf_check/ пустая — положи туда PDF и запусти снова.")
        return

    for pdf_path in pdfs:
        print(f"\n{'='*60}")
        print(f"  {pdf_path.name}")
        print(f"{'='*60}")
        try:
            result = await extract(pdf_path.read_bytes())
            print(f"  Дата анализа : {result.analysis_date}")
            print(f"  Пациент      : пол={result.patient_sex}, возраст={result.patient_age}")
            print(f"  Метрик       : {len(result.metrics)}")
            if result.warnings:
                print(f"  Предупреждения: {result.warnings}")
            print()
            for m in result.metrics:
                val = m.value_numeric if m.value_numeric is not None else repr(m.value_text)
                ref = ""
                if m.reference:
                    if m.reference.type.value == "range":
                        ref = f"  [{m.reference.min} – {m.reference.max}]"
                    elif m.reference.type.value in ("max", "min"):
                        ref = f"  [threshold={m.reference.threshold}]"
                print(f"  {m.raw_name:<40} {val} {m.unit or ''}{ref}")
        except Exception as e:
            print(f"  ОШИБКА: {e}")

asyncio.run(check_all())
