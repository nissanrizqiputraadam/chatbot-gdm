"""
summary.py – Text summarization untuk ringkasan akhir percakapan.

Strategi:
1. Kumpulkan semua teks jawaban bot (buang disclaimer & referensi).
2. Abstractive: kirim ke Gemini API → dapatkan satu kesimpulan singkat (~3-5 kalimat).
3. Extractive fallback (jika Gemini offline): TF-IDF sentence scoring → pilih
   kalimat paling informatif, maksimal 3 kalimat.
"""

import os
import re
import logging
from pathlib import Path

import numpy as np
import requests
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv(Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.8-flash",
]

SARAN_UMUM = [
    "Bawa catatan ringkasan ini saat berkonsultasi dengan dokter atau bidan.",
    "Segera hubungi tenaga kesehatan bila muncul keluhan yang mengkhawatirkan.",
]

# Kalimat/frasa yang tidak informatif – dibuang sebelum summarization
_SKIP_PATTERNS = [
    r"halo\s+bunda[^.]*\.",
    r"salam\s+hangat[^.]*\.",
    r"terima\s+kasih\s+sudah\s+bertanya[^.]*\.",
    r"semoga\s+bermanfaat[^.]*\.",
    r"jangan\s+ragu\s+untuk[^.]*\.",
    r"informasi\s+ini\s+bersifat\s+edukatif[^.]*\.",
    r"bukan\s+pengganti\s+konsultasi[^.]*\.",
    r"jawaban\s+ini\s+bersumber[^.]*\.",
    r"📖\s*referensi[^.]*\.",
    r"untuk\s+menilai\s+angka\s+milik\s+anda[^.]*\.",
    r"tetap\s+tenang[^.]*\.",
    r"semoga\s+persalinan[^.]*\.",
]
_SKIP_RE = re.compile("|".join(_SKIP_PATTERNS), re.IGNORECASE | re.DOTALL)


# ------------------------------------------------------------------
# Langkah 1 – Bersihkan teks jawaban
# ------------------------------------------------------------------
def _bersihkan(paragraphs: list[str]) -> str:
    """Gabungkan paragraf jawaban menjadi teks bersih tanpa disclaimer/sapaan."""
    teks = " ".join(p.strip() for p in paragraphs if p.strip())
    teks = _SKIP_RE.sub("", teks)
    teks = re.sub(r"\s{2,}", " ", teks).strip()
    return teks


# ------------------------------------------------------------------
# Langkah 2a – Abstractive summarization via Gemini
# ------------------------------------------------------------------
def _gemini_summarize(qa_pairs: list[dict]) -> str | None:
    """Minta Gemini membuat kesimpulan singkat dari kumpulan Q&A percakapan."""
    if not GEMINI_API_KEY:
        return None

    # Susun blok Q&A untuk dikirim ke Gemini
    blok = []
    for i, p in enumerate(qa_pairs, 1):
        blok.append(f"Pertanyaan {i}: {p['pertanyaan']}")
        blok.append(f"Jawaban {i}: {p['jawaban_bersih']}\n")
    percakapan = "\n".join(blok)

    prompt = f"""Kamu adalah asisten kesehatan yang membantu merangkum percakapan edukatif tentang diabetes gestasional (GDM).

Berikut adalah percakapan yang terjadi antara pengguna dan chatbot:

{percakapan}

Tugasmu:
Buat KESIMPULAN SINGKAT dalam Bahasa Indonesia (3–5 kalimat) yang:
- Merangkum poin-poin medis PENTING yang telah dibahas
- Ditulis dalam kalimat yang mengalir, mudah dipahami orang awam
- TIDAK menyebut "percakapan", "chatbot", "pertanyaan 1", dsb.
- TIDAK mengulang sapaan atau disclaimer
- Langsung ke inti informasi medis tentang GDM

Kesimpulan:"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 300,
        },
    }

    for model in GEMINI_MODELS:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={GEMINI_API_KEY}"
        )
        try:
            resp = requests.post(url, json=payload, timeout=20)
            if resp.status_code == 200:
                candidates = resp.json().get("candidates", [])
                if candidates:
                    text = (
                        candidates[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                        .strip()
                    )
                    if len(text) > 40:
                        logger.info("Ringkasan dibuat oleh Gemini (%s)", model)
                        return text
            elif resp.status_code == 503:
                continue
        except Exception as exc:
            logger.warning("Gemini summarize gagal (%s): %s", model, exc)
            continue

    return None


# ------------------------------------------------------------------
# Langkah 2b – Extractive fallback (TF-IDF sentence scoring)
# ------------------------------------------------------------------
def _extractive_summarize(teks_gabung: str, n_kalimat: int = 3) -> str:
    """
    Pilih n_kalimat paling informatif dari gabungan teks menggunakan TF-IDF.
    Ini adalah pendekatan extractive summarization standar NLP.
    """
    # Tokenisasi kalimat sederhana
    kalimat_all = re.split(r"(?<=[.!?])\s+", teks_gabung.strip())
    kalimat = [k.strip() for k in kalimat_all if len(k.strip()) > 30]

    if not kalimat:
        return teks_gabung[:400] + ("…" if len(teks_gabung) > 400 else "")

    if len(kalimat) <= n_kalimat:
        return " ".join(kalimat)

    # TF-IDF: hitung skor setiap kalimat terhadap dokumen keseluruhan
    try:
        vect = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
        matrix = vect.fit_transform(kalimat)

        # Skor = rata-rata cosine similarity dengan semua kalimat lain (centrality)
        sim = cosine_similarity(matrix)
        skor = sim.mean(axis=1)

        # Ambil top-n, pertahankan urutan asli
        top_idx = sorted(np.argsort(skor)[-n_kalimat:])
        hasil = " ".join(kalimat[i] for i in top_idx)
        return hasil
    except Exception:
        # Ultra-fallback: potong saja
        return " ".join(kalimat[:n_kalimat])


# ------------------------------------------------------------------
# Fungsi utama
# ------------------------------------------------------------------
def build_summary(items):
    """
    Membangun ringkasan percakapan dengan text summarization.

    items: list[SummaryItem] dengan field:
      - question (str)
      - intent (str|None)
      - type (str)
      - answer (list[str])
    """
    qa_pairs = []
    darurat = False
    di_luar = 0
    ada_angka_pribadi = False

    for it in items:
        tipe = getattr(it, "type", "answer")

        if tipe == "emergency":
            darurat = True

        if tipe == "fallback":
            di_luar += 1
            continue

        jawaban_raw = getattr(it, "answer", None) or []
        jawaban_bersih = _bersihkan(jawaban_raw)

        if jawaban_bersih:
            qa_pairs.append({
                "pertanyaan": it.question,
                "jawaban_bersih": jawaban_bersih,
            })

        # Cek angka pribadi
        q_low = it.question.lower()
        if re.search(r"\d", q_low) and "saya" in q_low.split():
            ada_angka_pribadi = True

    # --- Proses summarization ---
    total = len(items)
    dijawab = len(qa_pairs)

    if dijawab == 0:
        kesimpulan_teks = (
            "Belum ada pertanyaan yang terjawab pada sesi ini. "
            "Coba tanyakan tentang pengertian GDM, faktor risiko, diagnosis, "
            "atau pemantauan gula darah."
        )
        sumber = "none"
    else:
        # Gabungkan semua teks jawaban bersih
        semua_teks = " ".join(p["jawaban_bersih"] for p in qa_pairs)

        # Coba abstractive (Gemini)
        hasil_gemini = _gemini_summarize(qa_pairs)
        if hasil_gemini:
            kesimpulan_teks = hasil_gemini
            sumber = "gemini"
        else:
            # Fallback extractive TF-IDF
            kesimpulan_teks = _extractive_summarize(semua_teks, n_kalimat=3)
            sumber = "extractive"

    # --- Header ringkasan ---
    if dijawab == 0:
        ringkasan = ""
    elif dijawab == 1:
        ringkasan = f"Anda membahas 1 topik dalam sesi ini."
    else:
        ringkasan = (
            f"Anda membahas {dijawab} topik dalam sesi ini "
            f"(dari {total} pertanyaan yang diajukan)."
        )

    # --- Catatan khusus ---
    catatan = []
    if darurat:
        catatan.append(
            "⚠️ Anda menyebut gejala yang dapat memerlukan penanganan segera. "
            "Hubungi dokter, bidan, atau datang ke IGD terdekat."
        )
    if ada_angka_pribadi:
        catatan.append(
            "Anda menyebut angka pemeriksaan pribadi. "
            "Chatbot ini tidak dapat menilai hasil lab Anda — "
            "konsultasikan langsung ke dokter atau bidan."
        )
    if di_luar:
        catatan.append(
            f"{di_luar} pertanyaan di luar topik GDM tidak dapat dijawab oleh chatbot ini."
        )

    return {
        "ringkasan": ringkasan,
        "kesimpulan": kesimpulan_teks,
        "sumber": sumber,          # "gemini" | "extractive" | "none"
        "saran": SARAN_UMUM,
        "catatan": catatan,
    }
