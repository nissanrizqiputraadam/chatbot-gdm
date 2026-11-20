import json
import os
import re
from pathlib import Path

import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from nlp_utils import clean_text

BASE = Path(__file__).parent
model = joblib.load(BASE / "model" / "intent_model.joblib")
with open(BASE / "model" / "answers.json", encoding="utf-8") as f:
    ANSWERS = json.load(f)

THRESHOLD = 0.45  # SESUAIKAN dengan hasil Cell 8 di notebook

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
PERSONAL_NOTE = ("Untuk menilai angka milik Anda sendiri, silakan konsultasikan hasil "
                 "pemeriksaan Anda ke dokter atau tenaga kesehatan.")

app = FastAPI(title="Chatbot GDM")
frontend_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    # Untuk development lokal; domain production diatur lewat FRONTEND_ORIGINS.
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


def to_paragraphs(text, per=2):
    """Buang disclaimer (ditampilkan tetap di UI), lalu pecah jawaban per 2 kalimat."""
    body = text.split(DISCLAIMER_MARKER)[0].strip()
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", body)
    return [" ".join(sentences[i:i + per]) for i in range(0, len(sentences), per)]


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    cleaned = clean_text(req.message)

    # 1. Aturan darurat: didahulukan sebelum model
    if any(k in cleaned for k in EMERGENCY_KEYWORDS):
        return {"reply": EMERGENCY_REPLY, "intent": None, "confidence": 1.0, "type": "emergency"}

    # 2. Prediksi intent + tingkat keyakinan
    proba = model.predict_proba([cleaned])[0]
    best = int(proba.argmax())
    intent = model.classes_[best]
    confidence = float(proba[best])

    # 3. Terlalu ragu -> fallback
    if confidence < THRESHOLD:
        return {"reply": FALLBACK, "intent": None,
                "confidence": round(confidence, 3), "type": "fallback"}

    # 4. Ambil jawaban dari dataset
    paragraphs = to_paragraphs(ANSWERS[intent])
    if re.search(r"\d", cleaned) and "saya" in cleaned.split():
        paragraphs.append(PERSONAL_NOTE)   # pertanyaan berisi angka pribadi

    return {"reply": paragraphs, "intent": intent,
            "confidence": round(confidence, 3), "type": "answer"}
