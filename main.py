"""
Arabic OCR API - FastAPI
Deploy on Railway | Endpoints for any backend
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import io
import base64
from typing import Optional
from PIL import Image

from ocr_processor import (
    OCRProcessor,
    PDF_IMAGE_SUPPORT,
    PYPDF_SUPPORT,
    DOCX_READ_SUPPORT,
)
from ollama_corrector import (
    check_ollama_status,
    correct_text_with_ollama,
    fix_visual_arabic,
    is_visual_arabic,
)

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Arabic OCR API",
    description="استخراج وتصحيح النصوص العربية من الصور والـ PDF",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # غيّر لدومين الباك اند في الـ production
    allow_methods=["*"],
    allow_headers=["*"],
)

processor = OCRProcessor()


# ─── Models ───────────────────────────────────────────────────────────────────
class CorrectTextRequest(BaseModel):
    text: str
    model_name: Optional[str] = "llama3.2"


class FixVisualRequest(BaseModel):
    text: str


# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "service": "Arabic OCR API"}


@app.get("/health")
def health():
    ollama_ok, models = check_ollama_status()
    return {
        "status": "ok",
        "tesseract": True,
        "ollama": ollama_ok,
        "ollama_models": models,
        "pdf_support": PDF_IMAGE_SUPPORT,
        "pypdf_support": PYPDF_SUPPORT,
        "docx_support": DOCX_READ_SUPPORT,
    }


# ─── OCR Endpoints ────────────────────────────────────────────────────────────
@app.post("/ocr/image")
async def ocr_image(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    """
    استخراج نص من صورة (PNG, JPG, BMP, TIFF, WEBP)
    - language: ara | eng | ara+eng | null (كشف تلقائي)
    """
    ext = file.filename.split(".")[-1].lower()
    if ext not in ("png", "jpg", "jpeg", "bmp", "tiff", "webp"):
        raise HTTPException(400, "نوع الملف غير مدعوم. استخدم: png, jpg, bmp, tiff, webp")

    try:
        contents = await file.read()
        pil = Image.open(io.BytesIO(contents))
        text, detected_lang = processor.extract_from_pil(pil, language or None)
        return {
            "success": True,
            "text": text,
            "detected_language": detected_lang,
            "word_count": len(text.split()),
            "char_count": len(text),
        }
    except Exception as e:
        raise HTTPException(500, f"خطأ في المعالجة: {str(e)}")


@app.post("/ocr/pdf")
async def ocr_pdf(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    """
    استخراج نص من PDF (نصي أو ممسوح ضوئياً)
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "الملف لازم يكون PDF")

    try:
        contents = await file.read()
        text, detected_lang = processor.extract_from_pdf(
            contents, language or None
        )
        return {
            "success": True,
            "text": text,
            "detected_language": detected_lang,
            "word_count": len(text.split()),
            "char_count": len(text),
        }
    except Exception as e:
        raise HTTPException(500, f"خطأ في المعالجة: {str(e)}")


@app.post("/ocr/docx")
async def ocr_docx(file: UploadFile = File(...)):
    """
    استخراج نص من ملف Word (.docx)
    """
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(400, "الملف لازم يكون .docx")

    try:
        contents = await file.read()
        text, detected_lang = processor.extract_from_docx(contents)
        return {
            "success": True,
            "text": text,
            "detected_language": detected_lang,
            "word_count": len(text.split()),
            "char_count": len(text),
        }
    except Exception as e:
        raise HTTPException(500, f"خطأ في المعالجة: {str(e)}")


@app.post("/ocr/base64")
async def ocr_base64(
    image_base64: str = Form(...),
    language: Optional[str] = Form(None),
):
    """
    استخراج نص من صورة مرسلة كـ Base64 string
    مفيد لو الباك اند بيبعت الصورة كـ string مش كـ file
    """
    try:
        image_data = base64.b64decode(image_base64)
        pil = Image.open(io.BytesIO(image_data))
        text, detected_lang = processor.extract_from_pil(pil, language or None)
        return {
            "success": True,
            "text": text,
            "detected_language": detected_lang,
            "word_count": len(text.split()),
            "char_count": len(text),
        }
    except Exception as e:
        raise HTTPException(500, f"خطأ: {str(e)}")


# ─── Correction Endpoints ─────────────────────────────────────────────────────
@app.post("/correct")
def correct_text(req: CorrectTextRequest):
    """
    تصحيح إملائي للنص العربي باستخدام Ollama
    - text: النص المراد تصحيحه
    - model_name: اسم النموذج (افتراضي: llama3.2)
    """
    ollama_ok, _ = check_ollama_status()
    if not ollama_ok:
        raise HTTPException(503, "Ollama غير متاح حالياً")

    result = correct_text_with_ollama(req.text, model_name=req.model_name)
    if result is None:
        raise HTTPException(500, "فشل التصحيح")

    return {
        "success": True,
        "original": req.text,
        "corrected": result,
    }


@app.post("/fix-visual-arabic")
def fix_visual(req: FixVisualRequest):
    """
    تصليح النص العربي المعكوس (Visual Arabic / Presentation Forms)
    الناتج من OCR — بدون الحاجة لـ Ollama
    """
    detected = is_visual_arabic(req.text)
    fixed = fix_visual_arabic(req.text) if detected else req.text
    return {
        "success": True,
        "was_visual_arabic": detected,
        "original": req.text,
        "fixed": fixed,
    }


# ─── Combined: OCR + Correct ──────────────────────────────────────────────────
@app.post("/ocr-and-correct/image")
async def ocr_and_correct(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    model_name: Optional[str] = Form("llama3.2"),
):
    """
    الـ endpoint الأكثر استخداماً:
    رفع صورة → OCR → تصحيح إملائي بـ Ollama → النتيجة
    """
    ext = file.filename.split(".")[-1].lower()
    if ext not in ("png", "jpg", "jpeg", "bmp", "tiff", "webp"):
        raise HTTPException(400, "نوع الملف غير مدعوم")

    try:
        contents = await file.read()
        pil = Image.open(io.BytesIO(contents))
        raw_text, detected_lang = processor.extract_from_pil(pil, language or None)
    except Exception as e:
        raise HTTPException(500, f"خطأ في OCR: {str(e)}")

    corrected_text = raw_text
    ollama_ok, _ = check_ollama_status()
    if ollama_ok:
        result = correct_text_with_ollama(raw_text, model_name=model_name)
        if result:
            corrected_text = result

    return {
        "success": True,
        "detected_language": detected_lang,
        "raw_text": raw_text,
        "corrected_text": corrected_text,
        "ollama_used": ollama_ok,
        "word_count": len(corrected_text.split()),
    }
