#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
KidneyAgent - Extracción y revisión de resultados de laboratorio desde PDF.

- Compatible con Pydantic v2 (no usa langchain_core.pydantic_v1)
- Arregla el crash de with_structured_output(List[...]) usando modelos Pydantic v2
- Suprime warnings molestos (urllib3/LibreSSL, deprecations)
- Funciona "solo con regex" si no hay API; si hay API, usa LLM para normalizar y revisar.

Uso:
  python KA.py ruta/al/archivo.pdf --model gpt-4o-mini
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import warnings
from dataclasses import dataclass
from typing import Optional, Iterable

# --- Atenuar warnings ruidosos (opcional, no afecta lógica) ---
try:
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.simplefilter("ignore", category=NotOpenSSLWarning)
except Exception:
    pass

warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- Pydantic v2 ---
from pydantic import BaseModel, Field, ValidationError, TypeAdapter

# --- PDF lectura: usa pdfplumber si está, si no, PyPDF2 como fallback ---
def _read_pdf_text(path: str) -> str:
    text_parts = []
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                text_parts.append(txt)
    except Exception:
        # Fallback muy básico con PyPDF2
        try:
            from PyPDF2 import PdfReader  # type: ignore
            reader = PdfReader(path)
            for page in reader.pages:
                txt = page.extract_text() or ""
                text_parts.append(txt)
        except Exception as e:
            raise RuntimeError(f"No se pudo leer el PDF: {e}")
    return "\n".join(text_parts)


# -------------------------------
# MODELOS ESTRUCTURADOS (Pydantic v2)
# -------------------------------
class LabMeasurement(BaseModel):
    name: str = Field(..., description="Nombre del analito, ej. 'CREATININA'")
    value: str = Field(..., description="Valor reportado tal cual (puede incluir signos como '>' o '<')")
    unit: Optional[str] = Field(None, description="Unidad, ej. 'mg/dL', 'mmol/L'")
    ref_range: Optional[str] = Field(None, description="Rango de referencia en texto")
    flagged: Optional[bool] = Field(
        default=None, description="True si está fuera de rango, False si dentro, None si desconocido"
    )
    notes: Optional[str] = Field(None, description="Notas o comentarios del modelo")

class LabExtraction(BaseModel):
    measurements: list[LabMeasurement]


# -------------------------------
# EXTRACCIÓN BÁSICA (regex offline)
# -------------------------------
_ANALYTE_ROW = re.compile(
    r"""
    ^\s*                                   # inicio de línea
    (?P<name>[A-ZÁÉÍÓÚÑ/ \-\.\(\)0-9]+?)   # nombre del analito
    \s{1,}                                 # al menos un espacio
    (?P<value>[<>\=\~]?\s*\d+(?:[.,]\d+)?) # valor (permite >, < y decimales)
    \s{0,}
    (?P<unit>(mg/dL|g/dL|mmol/L|UI/L|U/L|ng/mL|µg/dL|ug/dL|mg/L|mL/min/1\.73m2|mL/min|%|fL|pg|gr/dL|Cel./µL|mmol/L|U/l))?
    \b
    """,
    re.VERBOSE | re.IGNORECASE | re.MULTILINE,
)

# Algunas líneas del PDF traen el rango a continuación; capturamos “VALORES DE REFERENCIA” o bloques conocidos.
_RANGE_HINT = re.compile(
    r"(VALORES?\s+DE\s+REFERENCIA.*?$|[<>\=\~]?\s*\d+(?:[.,]\d+)?\s*a\s*[<>\=\~]?\s*\d+(?:[.,]\d+)?(?:\s*\w+)?(?:\s*[A-Za-zÁÉÍÓÚÑ]+)?)",
    re.IGNORECASE | re.MULTILINE,
)


def basic_regex_extract(text: str) -> LabExtraction:
    """
    Intenta extraer filas 'nombre valor unidad' del PDF.
    No es perfecto, pero suele capturar muchas determinaciones.
    """
    measurements: list[LabMeasurement] = []
    lines = text.splitlines()

    # Un buffer de las últimas 2-3 líneas para adivinar ref_range
    window: list[str] = []

    for raw in lines:
        line = raw.strip()
        if not line:
            window = []
            continue

        window.append(line)
        if len(window) > 4:
            window.pop(0)

        m = _ANALYTE_ROW.search(line)
        if not m:
            continue

        name = " ".join(m.group("name").split())
        value = m.group("value").replace(" ", "")
        unit = m.group("unit")
        ref_range = None

        # Mirar en ventana por pistas de referencia
        for w in window:
            # Evitar duplicar la propia línea exacta
            if w == line:
                continue
            rr = _RANGE_HINT.search(w)
            if rr:
                ref_range = rr.group(0)
                break

        measurements.append(
            LabMeasurement(
                name=name.upper(),
                value=value.replace(",", "."),
                unit=unit,
                ref_range=ref_range,
            )
        )

    return LabExtraction(measurements=measurements)


# -------------------------
