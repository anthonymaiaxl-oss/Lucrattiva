"""Leitura de texto dos arquivos de entrada.

Cada formato tem um caminho e um plano B. Se nada funcionar, devolvemos texto
vazio e o pipeline manda para pendências — nunca inventamos conteúdo.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

EXTENSOES_IMAGEM = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def ler(caminho: str | Path, ocr_habilitado: bool = False,
        ocr_idioma: str = "por") -> tuple[str, str]:
    """Devolve (texto, origem) onde origem ∈ NATIVO | OCR | PLANILHA | VAZIO."""
    p = Path(caminho)
    ext = p.suffix.lower()

    if ext == ".txt":
        return p.read_text(encoding="utf-8", errors="ignore"), "NATIVO"
    if ext in (".xls", ".xlsx", ".xlsm", ".csv"):
        return _ler_planilha(p), "PLANILHA"
    if ext == ".pdf":
        texto = _ler_pdf(p)
        if texto.strip():
            return texto, "NATIVO"
        if ocr_habilitado:
            return _ocr_pdf(p, ocr_idioma), "OCR"
        return "", "VAZIO"
    if ext in EXTENSOES_IMAGEM:
        if ocr_habilitado:
            return _ocr_imagem(p, ocr_idioma), "OCR"
        return "", "VAZIO"
    return "", "VAZIO"


def _ler_pdf(p: Path) -> str:
    try:                                     # 1ª opção: pypdf (pip, leve)
        from pypdf import PdfReader
        return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
    except ImportError:
        pass
    except Exception:
        return ""
    try:                                     # 2ª opção: pdfplumber
        import pdfplumber
        with pdfplumber.open(str(p)) as pdf:
            return "\n".join((pg.extract_text() or "") for pg in pdf.pages)
    except Exception:
        pass
    try:                                     # 3ª opção: binário pdftotext (poppler)
        return subprocess.run(["pdftotext", "-layout", str(p), "-"],
                              capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""


def _ler_planilha(p: Path) -> str:
    if p.suffix.lower() == ".csv":
        return p.read_text(encoding="utf-8", errors="ignore")
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(p), data_only=True, read_only=True)
        linhas = []
        for aba in wb.worksheets:
            for linha in aba.iter_rows(values_only=True):
                linhas.append(" ".join(str(c) for c in linha if c is not None))
        return "\n".join(linhas)
    except Exception:
        return ""


def _ocr_pdf(p: Path, idioma: str) -> str:
    try:
        import pytesseract
        from pdf2image import convert_from_path
        return "\n".join(pytesseract.image_to_string(img, lang=idioma)
                         for img in convert_from_path(str(p), dpi=300))
    except Exception:
        return ""


def _ocr_imagem(p: Path, idioma: str) -> str:
    try:
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(Image.open(str(p)), lang=idioma)
    except Exception:
        return ""
