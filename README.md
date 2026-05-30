# Arabic OCR API

FastAPI service للـ OCR العربي — جاهز للـ deploy على Railway.

## الـ Endpoints

| Method | URL | الوصف |
|--------|-----|-------|
| GET | `/health` | حالة السيرفر و Ollama |
| POST | `/ocr/image` | OCR من صورة (multipart file) |
| POST | `/ocr/pdf` | OCR من PDF |
| POST | `/ocr/docx` | استخراج نص من Word |
| POST | `/ocr/base64` | OCR من صورة Base64 |
| POST | `/correct` | تصحيح إملائي بـ Ollama |
| POST | `/fix-visual-arabic` | تصليح Visual Arabic بدون Ollama |
| POST | `/ocr-and-correct/image` | OCR + تصحيح في request واحد |

---

## أمثلة استخدام

### OCR من صورة
```http
POST /ocr/image
Content-Type: multipart/form-data

file: <image_file>
language: ara          # اختياري — لو مش موجود بيكشفها تلقائي
```

**Response:**
```json
{
  "success": true,
  "text": "قسم الطوارئ والرعاية الحرجة",
  "detected_language": "ara",
  "word_count": 5,
  "char_count": 32
}
```

---

### OCR + تصحيح في خطوة واحدة
```http
POST /ocr-and-correct/image
Content-Type: multipart/form-data

file: <image_file>
language: ara
model_name: llama3.2
```

**Response:**
```json
{
  "success": true,
  "detected_language": "ara",
  "raw_text": "...",
  "corrected_text": "...",
  "ollama_used": true,
  "word_count": 42
}
```

---

### تصليح Visual Arabic (بدون Ollama)
```http
POST /fix-visual-arabic
Content-Type: application/json

{
  "text": "ﺔﺟﺮﺤﻟﺍ ﺔﻳﺎﻋﺮﻟﺍﻭ ﺉﺭﺍﻮﻄﻟﺍ ﻢﺴﻗ"
}
```

**Response:**
```json
{
  "success": true,
  "was_visual_arabic": true,
  "original": "ﺔﺟﺮﺤﻟﺍ ...",
  "fixed": "قسم الطوارئ والرعاية الحرجة"
}
```

---

## Deploy على Railway

### 1. رفع الكود على GitHub
```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USER/ocr-api.git
git push -u origin main
```

### 2. إنشاء مشروع على Railway
1. روح [railway.app](https://railway.app) وسجّل دخول
2. **New Project → Deploy from GitHub repo**
3. اختار الـ repo
4. Railway هيعمل build تلقائي من الـ Dockerfile

### 3. الـ URL
بعد الـ deploy هتلاقي URL زي:
```
https://ocr-api-production-xxxx.up.railway.app
```

---

## ملاحظة عن Ollama

Ollama بيشتغل **locally** — مش على Railway.  
لو الباك اند عنده Ollama شغّال، ابعت الـ text لـ `/correct`.  
لو لأ، استخدم `/fix-visual-arabic` (بدون AI) أو `/ocr/image` بس.

---

## هيكل الملفات

```
ocr_api/
├── main.py              # FastAPI app
├── ocr_processor.py     # OCR engine
├── ollama_corrector.py  # Ollama + Visual Arabic fix
├── requirements.txt
├── Dockerfile
├── railway.toml
└── README.md
```
