"""
Credit Agency 1 parser (sanitized).
"""

import os
import re
from datetime import datetime
from typing import Dict

import fitz  # PyMuPDF

DATE_FMT = "%m/%d/%Y"
OPTIONS = ["HIGH", "MODERATE-HIGH", "MODERATE", "LOW-MODERATE", "LOW"]


def _int_to_rgb(color_int: int):
    r = (color_int >> 16) & 255
    g = (color_int >> 8) & 255
    b = color_int & 255
    return (r, g, b)


def _extract_numeric_score(text: str, label: str):
    if not text:
        return None
    upper = text.upper()
    lab_upper = label.upper()
    idx = upper.find(lab_upper)
    if idx == -1:
        return None
    start = idx + len(label)
    window = text[start : start + 120]
    m = re.search(r"\b(\d{1,3})\b", window)
    if not m:
        return None
    try:
        val = int(m.group(1))
    except ValueError:
        return None
    if 0 <= val <= 100:
        return val
    return None


def _extract_viability_rating(text: str):
    if not text:
        return None
    upper = text.upper()
    label = "D&B VIABILITY RATING"
    idx = upper.find(label)
    if idx == -1:
        return None
    start = idx + len("Agency 1 Viability Rating")
    window = upper[start : start + 80]
    tokens = re.findall(r"[0-9A-Z]", window)
    if len(tokens) >= 4:
        return "".join(tokens[:4])
    return None


def _extract_bankruptcy_found(text: str):
    if not text:
        return None
    upper = text.upper()
    label = "BANKRUPTCY FOUND"
    idx = upper.find(label)
    if idx == -1:
        return None
    start = idx + len("Bankruptcy Found")
    window = upper[start : start + 40]
    m = re.search(r"\b([YN])\b", window)
    if m:
        return m.group(1)
    return None


def _extract_dnb_rating(text: str):
    if not text:
        return None
    upper = text.upper()
    label = "D&B RATING"
    idx = upper.find(label)
    if idx == -1:
        return None
    start = idx + len("Agency 1 Rating")
    window = upper[start : start + 60]
    if "--" in window:
        return None
    m = re.search(r"\b([0-9A-Z]{2,4})\b", window)
    if m:
        return m.group(1)
    return None


def _detect_selected_risk_and_credit(pdf_path):
    risk_value = None
    credit_value = None
    paydex = None
    delinquency_score = None
    failure_score = None
    viability_rating = None
    bankruptcy_found = None
    dnb_rating = None

    pattern_credit = re.compile(r"([\d,]+)\s*\(USD\)", re.IGNORECASE)

    try:
        with fitz.open(pdf_path) as doc:
            for page_index, page in enumerate(doc):
                text = page.get_text()

                if page_index == 0:
                    if paydex is None:
                        paydex = _extract_numeric_score(text, "PAYDEX (Agency 1)")
                    if delinquency_score is None:
                        delinquency_score = _extract_numeric_score(
                            text, "Delinquency Score"
                        )
                    if failure_score is None:
                        failure_score = _extract_numeric_score(text, "Failure Score")
                    if viability_rating is None:
                        viability_rating = _extract_viability_rating(text)
                    if bankruptcy_found is None:
                        bankruptcy_found = _extract_bankruptcy_found(text)
                    if dnb_rating is None:
                        dnb_rating = _extract_dnb_rating(text)

                if credit_value is None and "MAXIMUM CREDIT RECOMMENDATION" in text.upper():
                    m = pattern_credit.search(text)
                    if m:
                        credit_value = int(m.group(1).replace(",", ""))

                if risk_value is None:
                    rects = page.search_for("Dun & Bradstreet thinks")
                    if rects:
                        search_area = fitz.Rect(
                            rects[0].x0,
                            rects[0].y0,
                            page.rect.width,
                            rects[0].y1 + 200,
                        )
                        data = page.get_text("dict", clip=search_area)
                        for block in data.get("blocks", []):
                            for line in block.get("lines", []):
                                for span in line.get("spans", []):
                                    t = span.get("text", "").strip().upper()
                                    if t in OPTIONS:
                                        rgb = _int_to_rgb(span.get("color", 0))
                                        if rgb == (255, 255, 255):
                                            risk_value = t
                                            break
                            if risk_value:
                                break

                if risk_value and credit_value is not None:
                    if (
                        paydex is not None
                        and delinquency_score is not None
                        and failure_score is not None
                        and viability_rating is not None
                        and bankruptcy_found is not None
                        and dnb_rating is not None
                    ):
                        break
    except Exception:
        pass

    return (
        risk_value,
        credit_value,
        paydex,
        delinquency_score,
        failure_score,
        viability_rating,
        bankruptcy_found,
        dnb_rating,
    )


def _get_pdf_date_str(path: str) -> str:
    try:
        return datetime.fromtimestamp(os.path.getmtime(path)).strftime(DATE_FMT)
    except Exception:
        return ""


def parse_dnb(pdf_path: str) -> Dict[str, str]:
    (
        risk_val,
        credit_val,
        paydex,
        delinquency_score,
        failure_score,
        viability_rating,
        bankruptcy_found,
        dnb_rating,
    ) = _detect_selected_risk_and_credit(pdf_path)

    if not risk_val:
        return {}

    date_str = _get_pdf_date_str(pdf_path)

    return {
        "Agency 1 Score": risk_val,
        "Date of Agency 1 Score": date_str,
        "Max Credit Recommendation (Agency 1)": credit_val if credit_val is not None else "",
        "PAYDEX (Agency 1)": paydex if paydex is not None else "",
        "Delinquency Score": delinquency_score if delinquency_score is not None else "",
        "Failure Score": failure_score if failure_score is not None else "",
        "Agency 1 Viability Rating": viability_rating or "",
        "Bankruptcy Found": bankruptcy_found or "",
        "Agency 1 Rating": dnb_rating or "",
    }
