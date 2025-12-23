import asyncio
import os
from dotenv import load_dotenv
from vision_parser import parse_pdf_vision

load_dotenv()

async def test():
    # Укажи путь к тому PDF, что ты мне скидывал
    with open("013241970006.pdf", "rb") as f:
        pdf_bytes = f.read()
    
    print("Начинаю магию парсинга через ИИ...")
    result = parse_pdf_vision(pdf_bytes)
    print("\n--- КРАСИВЫЙ РЕЗУЛЬТАТ ---")
    for item in result.items:
        print(f"Анализ: {item.analyte_name} | Значение: {item.value} {item.unit} | Референс: {item.ref_range}")

if __name__ == "__main__":
    asyncio.run(test())