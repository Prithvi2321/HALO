"""
OCR Fallback using RapidOCR and PyPDFium2 page rendering.
Complies with Section 8 & 9 of prompt.md.
"""

import numpy as np
from PIL import Image
import pypdfium2 as pdfium
from rapidocr import RapidOCR

_engine = None


def get_ocr_engine():
    global _engine
    if _engine is None:
        _engine = RapidOCR()
    return _engine


def ocr_page(pdf_path: str, page_idx: int) -> tuple[str, float]:
    """
    Renders a PDF page to high-res bitmap and runs RapidOCR.
    Returns (extracted_text, average_confidence).
    """
    doc = pdfium.PdfDocument(pdf_path)
    page = doc[page_idx]
    # Render at 300 DPI (scale=300/72 ~ 4.16)
    bitmap = page.render(scale=300 / 72)
    pil_image = bitmap.to_pil()
    img_np = np.array(pil_image)

    ocr = get_ocr_engine()
    result, elapse_list = ocr(img_np)

    if not result:
        return "", 0.0

    lines = []
    scores = []
    for line in result:
        text, score = line[1], float(line[2])
        lines.append(text)
        scores.append(score)

    avg_score = sum(scores) / len(scores) if scores else 0.0
    return "\n".join(lines), avg_score
