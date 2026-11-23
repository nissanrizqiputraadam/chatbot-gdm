import json
import logging
import os
import re
from pathlib import Path

import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from nlp_utils import clean_text
from rag_engine import get_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent
model = joblib.load(BASE / "model" / "intent_model.joblib")
with open(BASE / "model" / "answers.json", encoding="utf-8") as f:
    ANSWERS = json.load(f)

THRESHOLD = 0.45          # threshold intent classifier (ML lama)
RAG_THRESHOLD = 0.40      # threshold RAG similarity

DISCLAIMER_MARKER = "Informasi ini bersifat edukatif"

EMERGENCY_KEYWORDS = [
    "pendarahan", "perdarahan", "pingsan", "kejang", "sesak napas",
    "nyeri dada", "gerakan bayi berkurang", "bayi tidak bergerak",
    "tidak sadar", "muntah terus",
]

FALLBACK = [
    "Maaf, saya belum bisa menjawab pertanyaan itu. Saya hanya membahas diabetes gestasional (GDM).",
    "Coba tanyakan tentang: apa itu GDM, faktor risiko, cara diagnosis, target gula darah, atau pemantauan gula darah.",
]
EMERGENCY_REPLY = [
    "Gejala yang Anda sebutkan bisa menjadi tanda kondisi yang perlu penanganan segera.",
    "Segera hubungi dokter, bidan, atau datang ke IGD terdekat. Chatbot ini tidak dapat menggantikan pemeriksaan langsung.",
]
PERSONAL_NOTE = (
    "Untuk menilai angka milik Anda sendiri, silakan konsultasikan hasil "
    "pemeriksaan Anda ke dokter atau tenaga kesehatan."
)
DISCLAIMER_RAG = (
    "Jawaban ini bersumber dari buku teks medis. "
    "Informasi ini bersifat edukatif dan bukan pengganti konsultasi dokter."
)

app = FastAPI(title="Chatbot GDM + RAG")
frontend_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Muat RAG engine saat startup
rag = get_engine()
if not rag._api_key:
    logger.warning("=" * 60)
    logger.warning("⚠️  PERINGATAN: File backend/.env belum ada atau GEMINI_API_KEY kosong!")
    logger.warning("Tanpa Gemini API Key atau Ollama, chatbot akan fallback ke kutipan buku teks bahasa Inggris.")
    logger.warning("Silakan buat file backend/.env sesuai petunjuk di CATATAN_RUN_PROJECT.md.")
    logger.warning("=" * 60)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


def to_paragraphs(text, per=2):
    """Buang disclaimer, lalu pecah jawaban per 2 kalimat."""
    body = text.split(DISCLAIMER_MARKER)[0].strip()
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", body)
    return [" ".join(sentences[i:i + per]) for i in range(0, len(sentences), per)]


def rag_to_paragraphs(answer: str, page: int | None, source: str = "tfidf") -> list[str]:
    """Format jawaban RAG menjadi paragraf-paragraf yang bersih."""
    result = []
    if source != "tfidf":
        # Baik Gemini maupun Ollama Qwen sudah menghasilkan paragraf & poin-poin yang terstruktur rapi
        paragraphs = [p.strip() for p in answer.strip().split("\n\n") if p.strip()]
        result.extend(paragraphs)
    else:
        # Untuk fallback tfidf mentah, pisahkan per 2 kalimat
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", answer.strip())
        sentences = [s.strip() for s in sentences if s.strip()]
        for i in range(0, len(sentences), 2):
            para = " ".join(sentences[i:i + 2])
            if para:
                result.append(para)

    if page:
        result.append(f"📖 Referensi: Textbook of Diabetes and Pregnancy, halaman {page}.")

    result.append(DISCLAIMER_RAG)
    return result


@app.get("/")
def health():
    return {"status": "ok", "rag_loaded": True, "qa_count": len(rag._data)}


@app.post("/chat")
def chat(req: ChatRequest):
    cleaned = clean_text(req.message)
    original = req.message.strip()

    # 1. Filter darurat — didahulukan sebelum apapun
    if any(k in cleaned for k in EMERGENCY_KEYWORDS):
        return {
            "reply": EMERGENCY_REPLY,
            "intent": None,
            "confidence": 1.0,
            "type": "emergency",
            "source": None,
        }

    # 2. Coba RAG (prioritas: teks asli → teks bersih → terjemahan kunci)
    # Dataset Q&A banyak berbahasa Inggris, jadi coba variasi kata kunci
    # PENTING: frasa panjang harus lebih dulu dari kata tunggal agar tidak terpotong
    _id_to_en = [
        # Frasa topik utama (termasuk tombol topik cepat di UI)
        ("target kadar gula darah",      "recommended blood glucose levels target pregnancy"),
        ("target gula darah",           "recommended blood glucose levels target pregnancy"),
        ("kadar gula darah",             "blood glucose levels"),
        ("gula darah",                   "blood glucose"),
        ("seberapa sering cek gula darah", "frequency blood glucose monitoring pregnancy"),
        ("seberapa sering",              "how often frequency"),
        ("cek gula darah",               "blood glucose monitoring pregnancy"),
        ("periksa gula darah",           "blood glucose monitoring pregnancy"),
        ("faktor risikonya",             "gestational diabetes risk factors"),
        ("faktor risiko",                "gestational diabetes risk factors"),
        ("cara diagnosisnya",            "gestational diabetes diagnosis screening"),
        ("cara diagnosis",               "gestational diabetes diagnosis screening"),
        ("diagnosisnya",                 "gestational diabetes diagnosis screening"),
        ("gejala dan tanda",             "gestational diabetes signs symptoms"),
        ("tanda dan gejala",             "gestational diabetes signs symptoms"),
        ("gejalanya",                    "gestational diabetes symptoms"),
        ("gejala",                       "gestational diabetes symptoms"),
        ("penyebabnya",                  "gestational diabetes causes"),
        ("penyebab",                     "gestational diabetes causes"),
        ("cara mencegah",                "gestational diabetes prevention"),
        ("pencegahan",                   "gestational diabetes prevention"),
        ("ibu hamil",                    "pregnant women"),
        ("saat kehamilan",               "during pregnancy"),
        ("selama kehamilan",             "during pregnancy"),
        ("pada kehamilan",               "during pregnancy"),
        ("diabetes melitus gestasional", "gestational diabetes mellitus"),
        ("diabetes gestasional",         "gestational diabetes mellitus"),
        ("berat badan",                  "body weight"),
        ("tekanan darah",                "blood pressure"),
        ("kehamilan",                    "pregnancy"),
        ("hamil",                        "pregnancy"),
        ("gdm",                          "gestational diabetes mellitus"),
        ("diagnosis",                    "diagnosis"),
        ("skrining",                     "screening"),
        ("pengobatan",                   "treatment"),
        ("terapi",                       "therapy"),
        ("insulin",                      "insulin"),
        ("diet",                         "diet"),
        ("bayi",                         "baby"),
        ("janin",                        "fetus"),
        ("persalinan",                   "delivery"),
        ("komplikasi",                   "complications"),
        ("pemantauan",                   "monitoring"),
        ("target",                       "recommended level"),
        ("kadar",                        "level"),
        ("anak",                         "child"),
        ("obesitas",                     "obesity"),
        ("plasenta",                     "placenta"),
        ("saat",                         "during"),
        ("cara",                         "how to"),
        ("bagaimana",                    "how"),
        ("apa itu",                      "what is"),
        ("apakah",                       "what is"),
    ]

    # Gatekeeper fleksibel: mencakup kata dasar / imbuhan seputar GDM & kehamilan
    _GDM_TOPIC_STEMS = [
        "diabet", "gdm", "gula", "glukos", "insulin", "hamil", "janin", "bayi",
        "plasenta", "salin", "trimester", "kandung", "hormon", "pankreas",
        "hba1c", "hipo", "hiper", "obes", "diet", "nutrisi", "makan", "karbo",
        "berat", "bmi", "tensi", "darah", "preeklamps", "komplikasi", "diagnos",
        "skrining", "ogtt", "pantau", "terapi", "obat", "cegah", "gejala",
        "tanda", "risiko", "sebab", "faktor", "cek", "tes", "usia", "anak",
        "gestation", "pregnan", "fetus", "fetal", "screen", "glucose",
    ]

    def _is_on_topic(text: str) -> bool:
        """Cek apakah teks mengandung topik medis / kehamilan / GDM."""
        lowered = text.lower()
        return any(stem in lowered for stem in _GDM_TOPIC_STEMS)

    rag_result = None
    if _is_on_topic(original) or _is_on_topic(cleaned):
        # Buat query pencarian Inggris dari kata kunci bahasa Indonesia
        translated = cleaned
        for id_word, en_word in _id_to_en:
            translated = translated.replace(id_word, en_word)

        # Cari dengan terjemahan kata kunci (paling akurat dengan buku teks bahasa Inggris)
        search_target = translated if translated != cleaned else original
        rag_result = rag.query(user_text=original, search_query=search_target, threshold=RAG_THRESHOLD)

        # Jika belum cocok, coba pakai teks asli
        if rag_result is None and search_target != original:
            rag_result = rag.query(user_text=original, search_query=original, threshold=RAG_THRESHOLD)

    if rag_result is not None:
        paragraphs = rag_to_paragraphs(
            rag_result["answer"],
            rag_result["page"],
            rag_result.get("source", "tfidf"),
        )
        # Tambahkan catatan personal jika user menyebut angka miliknya sendiri
        if re.search(r"\d", cleaned) and "saya" in cleaned.split():
            paragraphs.append(PERSONAL_NOTE)

        return {
            "reply": paragraphs,
            "intent": "rag",
            "confidence": rag_result["score"],
            "type": "rag",
            "source": {
                "page": rag_result["page"],
                "score": rag_result["score"],
                "engine": rag_result.get("source", "tfidf"),  # "gemini" | "tfidf"
            },
        }
    # 3. Fallback ke intent classifier (model ML lama)
    proba = model.predict_proba([cleaned])[0]
    best = int(proba.argmax())
    intent = model.classes_[best]
    confidence = float(proba[best])

    if confidence < THRESHOLD:
        return {
            "reply": FALLBACK,
            "intent": None,
            "confidence": round(confidence, 3),
            "type": "fallback",
            "source": None,
        }

    paragraphs = to_paragraphs(ANSWERS[intent])
    if re.search(r"\d", cleaned) and "saya" in cleaned.split():
        paragraphs.append(PERSONAL_NOTE)

    return {
        "reply": paragraphs,
        "intent": intent,
        "confidence": round(confidence, 3),
        "type": "intent",
        "source": None,
    }
