"""Intermediate data structures for PDF parsing."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RawCell:
    """A single cell extracted from PDF with coordinates."""
    page: int
    x0: float
    x1: float
    y0: float
    y1: float
    text: str


@dataclass
class RawRow:
    """A row of cells from PDF table."""
    page: int
    cells: List[RawCell]
    y0: float  # Top y-coordinate of the row
    y1: float  # Bottom y-coordinate of the row


@dataclass
class RawAnalyte:
    """Intermediate representation of a parsed analyte before final normalization."""
    id: str  # e.g. f"{page}-{row_index}"
    page: int
    row_index: int
    section: Optional[str]
    analyte_raw: str
    value_raw: Optional[str]
    unit_raw: Optional[str]
    ref_range_raw: Optional[str]
    extra_raw: Optional[str] = None
    original_cells: List[RawCell] = None  # Keep reference to original cells for debugging
    
    def __post_init__(self):
        if self.original_cells is None:
            self.original_cells = []

