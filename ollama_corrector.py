"""
Ollama Integration for Arabic Text Correction
"""

import requests
import re
import unicodedata
from typing import Optional, Tuple, List

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
DEFAULT_MODEL = "llama3.2"

# ─── Visual Arabic Detection ──────────────────────────────────────────────────
_PRESENTATION_FORMS_RE = re.compile(r'[\uFB50-\uFDFF\uFE70-\uFEFF]')
_CONTROL_CHARS_RE = re.compile(r'[\u200e\u200f\u202a-\u202e\u2066-\u2069]')


def is_visual_arabic(text: str) -> bool:
    """هل النص يحتوي على Presentation Forms (Visual Arabic من OCR)؟"""
    return bool(_PRESENTATION_FORMS_RE.search(text))


def fix_visual_arabic(text: str) -> str:
    """
    تصليح النص العربي المرئي (Visual Arabic / Presentation Forms)
    الناتج من OCR يقرأ النص RTL كـ LTR ويخزن الحروف معكوسة.

    الخوارزمية لكل سطر:
      1. NFKC  → تحويل FB50-FDFF إلى Unicode عربي قياسي
      2. حذف invisible bidi control chars
      3. تقسيم لـ tokens (كلمات / أرقام / رموز)
      4. عكس حروف الكلمات العربية فقط (إصلاح ترتيب الجليفات)
      5. عكس ترتيب الـ tokens في السطر (إصلاح ترتيب القراءة)
      الأرقام والتواريخ والـ IDs لا تُعكس حروفها — فقط تُعاد لمكانها الصحيح.
    """
    lines = text.split('\n')
    fixed_lines = []

    for line in lines:
        if not line.strip():
            fixed_lines.append(line)
            continue

        norm = unicodedata.normalize('NFKC', line)
        norm = _CONTROL_CHARS_RE.sub('', norm).strip()

        arabic_count = sum(1 for c in norm if '\u0600' <= c <= '\u06FF')
        if arabic_count <= 1:
            fixed_lines.append(norm)
            continue

        tokens = norm.split()
        fixed_tokens = []
        for tok in tokens:
            has_arabic = any('\u0600' <= c <= '\u06FF' for c in tok)
            fixed_tokens.append(tok[::-1] if has_arabic else tok)

        fixed_tokens = fixed_tokens[::-1]
        fixed_lines.append(' '.join(fixed_tokens))

    return '\n'.join(fixed_lines)


def check_ollama_status() -> Tuple[bool, List[str]]:
    """Check if Ollama is running and return available models"""
    try:
        resp = requests.get(OLLAMA_TAGS_URL, timeout=5)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            names = [m['name'] for m in models]
            return bool(names), names
        return False, []
    except:
        return False, []


def send_to_ollama(text: str, model_name: str) -> Optional[str]:
    """
    Send text to Ollama for spell correction.
    Automatically fixes Visual Arabic before sending.
    """
    # ── Pre-processing: تصليح Visual Arabic قبل الإرسال للـ LLM ──────────────
    if is_visual_arabic(text):
        text = fix_visual_arabic(text)

    prompt = f"""أنت مساعد متخصص في تصحيح الأخطاء الإملائية في النصوص العربية.
مهمتك: تصحيح الأخطاء الإملائية فقط دون تغيير المعنى أو المحتوى أو التنسيق.

قواعد مهمة:
- صحح الأخطاء الإملائية فقط
- لا تغير المعنى أو المحتوى
- احتفظ بالتنسيق كما هو
- لا تضف أي تعليقات أو شروحات
- إذا وجدت تاريخاً أو رقم ID أو رقم ملف في النص، استخرجهم وضعهم في أعلى النص داخل مربع بهذا الشكل:
  ┌─────────────────────────────┐
  │ رقم الملف: [القيمة]         │
  │ التاريخ: [القيمة]           │
  └─────────────────────────────┘
- أعد النص المصحح فقط بدون تعليقات

النص:
{text}

النص المصحح:"""

    try:
        data = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "top_p": 0.9}
        }
        resp = requests.post(OLLAMA_URL, json=data, timeout=120)
        if resp.status_code != 200:
            return None

        corrected = resp.json().get('response', '').strip()

        # Remove common preamble lines
        skip_kw = ['النص المصحح', 'التصحيح', 'إليك', 'هنا', 'الإجابة', 'النتيجة']
        lines = [
            l for l in corrected.split('\n')
            if not any(kw in l and len(l) < 50 for kw in skip_kw)
        ]
        corrected = '\n'.join(lines).strip()

        # If result is too short, return the pre-processed text (not original)
        if len(corrected) < len(text) * 0.3:
            return text
        return corrected

    except requests.exceptions.Timeout:
        return None
    except Exception:
        return None


def correct_text_with_ollama(text: str, model_name: str = DEFAULT_MODEL,
                              max_chunk: int = 2000,
                              progress_callback=None) -> Optional[str]:
    """
    Correct Arabic text using Ollama.
    - Automatically fixes Visual Arabic before sending to LLM
    - Splits long texts into chunks automatically
    - progress_callback(current, total) called for each chunk
    """
    if not text.strip():
        return text

    # تصليح Visual Arabic على النص كاملاً قبل التقطيع
    if is_visual_arabic(text):
        text = fix_visual_arabic(text)

    if len(text) <= max_chunk:
        return send_to_ollama(text, model_name)

    # Split into chunks by line
    lines = text.split('\n')
    parts, current = [], ""
    for line in lines:
        if len(current) + len(line) + 1 > max_chunk and current:
            parts.append(current)
            current = line + '\n'
        else:
            current += line + '\n'
    if current:
        parts.append(current)

    corrected_parts = []
    for i, part in enumerate(parts):
        if progress_callback:
            progress_callback(i + 1, len(parts))
        result = send_to_ollama(part, model_name)
        corrected_parts.append(result if result else part)

    return '\n'.join(corrected_parts)
