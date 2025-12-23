"""Pydantic models for lab import data."""

from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, Field


class ImportedLabItem(BaseModel):
    """Represents a single lab test result."""
    
    analyte_name: str = Field(..., description="Name of the analyte/test (e.g., 'Glucosa', 'Urea', 'RELACIÓN BUN/CRE')")
    value: Optional[float] = Field(None, description="Test result value (numeric)")
    value_text: Optional[str] = Field(None, description="Test result value (text, e.g., 'NEGATIVO', 'POSITIVO')")
    notes: Optional[str] = Field(None, description="Additional textual notes (color, appearance, comments)")
    unit: Optional[str] = Field(None, description="Unit of measurement (e.g., 'mg/dL', 'mmol/L', 'U/L', 'mL/min/1.73m2')")
    material: Optional[str] = Field(None, description="Sample material (e.g., 'SUERO', 'SANGRE')")
    taken_at: Optional[datetime] = Field(None, description="Date/time when the sample was taken")
    ref_range: Optional[str] = Field(None, description="Reference range (e.g., '70 a 100', '0.62 - 1.11', '10 a 20')")
    ref_min: Optional[float] = Field(None, description="Lower bound of reference range")
    ref_max: Optional[float] = Field(None, description="Upper bound of reference range")


class ImportJson(BaseModel):
    """Container for imported lab results."""
    
    patient_id: Union[str, int] = Field(..., description="Patient identifier")
    items: List[ImportedLabItem] = Field(default_factory=list, description="List of lab test results")
    source_pdf: Optional[str] = Field(None, description="Source PDF filename")
    normalization_method: Optional[str] = Field(None, description="Method used for normalization (llm or rule-based)")
