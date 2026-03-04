"""
Credit Agency 2 parser (sanitized).
"""

import os
import re
from datetime import datetime
from typing import Dict

import fitz  # PyMuPDF

DATE_FMT = "%m/%d/%Y"


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").upper().replace("\xa0", " ")).strip()


def _extract_text_from_pdf(file_path: str, first_page_only: bool = True) -> str:
    try:
        with fitz.open(file_path) as doc:
            if first_page_only:
                return doc[0].get_text()
            return "\n".join(page.get_text() for page in doc)
    except Exception:
        return ""


def _extract_ansonia_score(text: str):
    m = re.search(r"RISK\s*SCORE[:\s]+(\d{2,3})\b", text, re.IGNORECASE)
    if not m:
        return None
    try:
        score = int(m.group(1))
        if 20 <= score <= 100:
            return score
    except ValueError:
        pass
    return None


def _extract_ansonia_rating(text: str):
    m = re.search(r"RATING[:\s]+(\d+[A-Z])\s*-\s*(\d{1,3})\b", text, re.IGNORECASE)
    if not m:
        return None
    left = m.group(1)
    right = m.group(2)
    return f"{left} - {right}"


def _is_credit_report(text: str) -> bool:
    n = _normalize_text(text)
    if "SUMMARY TOTALS" in n or "LIVE REPORT ACTIVE" in n:
        return False
    return "RISK SCORE" in n


def _get_pdf_date_str(path: str) -> str:
    try:
        return datetime.fromtimestamp(os.path.getmtime(path)).strftime(DATE_FMT)
    except Exception:
        return ""


def parse_ansonia(pdf_path: str) -> Dict[str, str]:
    first_page_text_raw = _extract_text_from_pdf(pdf_path, first_page_only=True)
    if not first_page_text_raw:
        return {}

    first_page_norm = _normalize_text(first_page_text_raw)
    if not _is_credit_report(first_page_norm):
        return {}

    score = _extract_ansonia_score(first_page_norm)
    if score is None:
        return {}

    rating = _extract_ansonia_rating(first_page_norm)
    date_str = _get_pdf_date_str(pdf_path)

    return {
        "Agency 2 Score": score,
        "Date of Agency 2 Score": date_str,
        "Agency 2 Rating": rating or "",
    }
