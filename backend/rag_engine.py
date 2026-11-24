"""
rag_engine.py – RAG retrieval + LLM generation engine (Gemini & Ollama Qwen2.5-1.5B).

Alur:
  1. Retrieval: TF-IDF similarity dari qa_dataset.json → ambil top-K konteks dari buku teks.
  2. Generation: Kirim konteks dan pertanyaan ke LLM:
     - Ollama Lokal: Qwen2.5:1.5b (100% offline, cepat & hemat kuota)
     - Gemini API: gemini-3.5-flash / gemini-3.5-flash-lite (online)
  3. Hasil: Jawaban lengkap, ramah, dan terstruktur dalam Bahasa Indonesia.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

import numpy as np
import requests
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Muat environment variable dari .env di folder backend
load_dotenv(Path(__file__).parent / ".env")

BASE = Path(__file__).parent
QA_PATH = BASE.parent / "data" / "qa" / "qa_dataset.json"

RAG_THRESHOLD = 0.35
TOP_K = 4

# Konfigurasi LLM
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").strip().lower()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b").strip()

# Model Gemini resmi yang aktif dan didukung API
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-flash-latest",
]

_CITATION_PATTERNS = [
    r"\b[A-Z][a-z]+\s+[A-Z]{1,3},\s+[A-Z][a-z]+\s+[A-Z]{1,3}.*?et\s+al\.?",
    r"\b[A-Z][a-z]+\s+[A-Z]{1,3}.*?et\s+al\.?",
    r"\([A-Z][^)]*,\s*\d{4}[a-z]?\)",
    r"\([A-Z][^)]*et\s+al\.[^)]*\)",
    r"\[\d+(?:,\s*\d+)*\]",
    r"Studi\s+lain\s+seperti\s+yang\s+disebutkan\s+oleh[^.]*\.",
    r"seperti\s+yang\s+disebutkan\s+oleh[^.]*\.",
    r"menurut\s+[A-Z][a-z]+\s+[A-Z]{1,3}[^.]*\.",
]
_CITATION_RE = re.compile("|".join(_CITATION_PATTERNS), re.IGNORECASE)

_FRAGMENT_STARTERS = (
    "menunjukkan", "menyebabkan", "meningkatkan", "menurunkan",
    "mempengaruhi", "mengakibatkan", "memberikan", "menggunakan",
    "dilakukan", "ditemukan", "diketahui", "digunakan",
    "shows", "indicates", "suggests", "demonstrates", "reveals",
)


def _clean_answer(text: str) -> str:
    cleaned = _CITATION_RE.sub("", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\.\s*\.", ".", cleaned)
    return cleaned.strip()


def _is_good_answer(text: str) -> bool:
    cleaned = _clean_answer(text)
    if len(cleaned) < 50:
        return False
    if cleaned and cleaned[0].islower():
        return False
    first_word = cleaned.split()[0].lower().rstrip(",") if cleaned.split() else ""
    if first_word in _FRAGMENT_STARTERS:
        return False
    citation_hits = len(re.findall(r"et\s+al\.|[A-Z]{1,3},\s+[A-Z]{1,3}", cleaned))
    if citation_hits >= 3:
        return False
    return True


class RAGEngine:
    """Retrieval-Augmented Generation menggunakan TF-IDF + Gemini / Ollama Qwen2.5."""

    def __init__(self, qa_path: Path = QA_PATH):
        logger.info("Memuat QA dataset dari %s …", qa_path)
        with open(qa_path, encoding="utf-8") as f:
            raw: list[dict] = json.load(f)

        self._data = [item for item in raw if _is_good_answer(item["answer"])]
        logger.info("QA setelah filter: %d / %d", len(self._data), len(raw))

        self._questions = [item["question"] for item in self._data]
        self._answers = [_clean_answer(item["answer"]) for item in self._data]
        self._pages = [item.get("source_page") for item in self._data]

        logger.info("Membangun TF-IDF index …")
        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), min_df=1, max_df=0.95, sublinear_tf=True,
        )
        self._matrix = self._vectorizer.fit_transform(self._questions)

        self._api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self._ollama_url = OLLAMA_URL
        self._ollama_model = OLLAMA_MODEL
        self._provider = LLM_PROVIDER

        logger.info(
            "RAG Engine siap. Provider default: %s (Ollama: %s | Gemini Key: %s)",
            self._provider,
            self._ollama_model,
            "Ada" if self._api_key else "Tidak ada",
        )

    def _retrieve(
        self, user_text: str, top_k: int = TOP_K, threshold: float = RAG_THRESHOLD
    ) -> list[dict]:
        """Cari referensi Q&A paling relevan dari buku."""
        query_vec = self._vectorizer.transform([user_text])
        scores = cosine_similarity(query_vec, self._matrix).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < threshold:
                break
            results.append({
                "question": self._questions[idx],
                "answer": self._answers[idx],
                "page": self._pages[idx],
                "score": round(score, 3),
            })
        return results

    def _build_prompt(self, user_question: str, contexts: list[dict]) -> str:
        """Susun prompt standar untuk LLM (Gemini atau Ollama)."""
        context_blocks = []
        for i, ctx in enumerate(contexts, 1):
            context_blocks.append(
                f"[Konteks {i} - Hal. {ctx['page']}]\n"
                f"Topik: {ctx['question']}\n"
                f"Informasi Medis: {ctx['answer']}"
            )
        context_str = "\n\n".join(context_blocks)

        return f"""Kamu adalah asisten edukasi kesehatan kehamilan yang ramah, hangat, dan berempati (khusus diabetes melitus gestasional / GDM).

Tugasmu: Jawab pertanyaan pengguna dengan jelas, menenangkan, dan mudah dipahami berdasarkan referensi buku teks medis berikut.

REFERENSI BUKU TEKS MEDIS (DALAM BAHASA INGGRIS):
{context_str}

PERTANYAAN PENGGUNA:
{user_question}

ATURAN UTAMA JAWABAN:
1. WAJIB 100% MENJAWAB DALAM BAHASA INDONESIA. Dilarang keras menjawab dalam Bahasa Inggris meskipun referensi di atas berbahasa Inggris.
2. Jawab langsung ke intinya dengan bahasa yang hangat, jelas, dan ramah (misal menyapa 'Bunda').
3. Gunakan poin-poin (bullet points) jika ada daftar angka, gejala, atau langkah-langkah agar mudah dibaca.
4. Terjemahkan semua istilah medis ke Bahasa Indonesia yang mudah dipahami, tetapi sebutkan angka/target aslinya jika ada (misal: mg/dL).
5. Jangan menyebut 'Berdasarkan konteks 1' atau 'Menurut referensi'. Bicaralah seperti seorang edukator kesehatan profesional.
6. Hindari membungkus kalimat dengan tanda bintang ganda (**) berlebihan. Tulis kalimat mengalir secara alami dan bersih.
7. Jika konteks tidak memuat jawaban yang relevan, katakan dengan sopan bahwa Anda belum memiliki informasi lengkap mengenai hal tersebut dalam panduan GDM ini.
"""

    def _generate_with_ollama(self, user_question: str, contexts: list[dict]) -> Optional[str]:
        """Panggil Ollama lokal (Qwen2.5:1.5b) via REST API."""
        prompt = self._build_prompt(user_question, contexts)
        payload = {
            "model": self._ollama_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.3,
            },
        }

        try:
            resp = requests.post(self._ollama_url, json=payload, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content", "").strip()
                if content:
                    logger.info("Jawaban berhasil dibuat oleh Ollama: %s", self._ollama_model)
                    return content
            else:
                logger.warning("Ollama status %d: %s", resp.status_code, resp.text[:150])
        except Exception:
            # Ollama lokal tidak aktif/tidak merespons, lewati dengan cepat
            pass

        return None

    def _generate_with_gemini(self, user_question: str, contexts: list[dict]) -> Optional[str]:
        """Panggil Gemini REST API untuk merangkum dan menjelaskan konteks medis."""
        if not self._api_key:
            return None

        prompt = self._build_prompt(user_question, contexts)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 800,
            },
        }

        for model_name in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self._api_key}"
            try:
                resp = requests.post(url, json=payload, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text.strip():
                            logger.info("Jawaban berhasil dibuat oleh Gemini: %s", model_name)
                            return text.strip()
                elif resp.status_code == 503:
                    logger.warning("Model %s 503 (sibuk), mencoba model berikutnya...", model_name)
                    continue
                else:
                    logger.warning("Model %s status %d", model_name, resp.status_code)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning("Koneksi/timeout ke Gemini API (%s). Melewati ke model lokal.", model_name)
                break
            except Exception as e:
                logger.warning("Gagal request ke %s: %s", model_name, e)
                continue

        return None

    def query(
        self,
        user_text: str,
        search_query: Optional[str] = None,
        top_k: int = TOP_K,
        threshold: float = RAG_THRESHOLD,
    ) -> Optional[dict]:
        # Gunakan search_query (terjemahan Inggris) untuk pencarian jika ada
        lookup_query = search_query if search_query else user_text
        contexts = self._retrieve(lookup_query, top_k=top_k, threshold=threshold)

        # Jika belum dapat dan ada variasi query lain, coba user_text asli
        if not contexts and search_query and search_query != user_text:
            contexts = self._retrieve(user_text, top_k=top_k, threshold=threshold)

        if not contexts:
            return None

        # Strategi eksekusi sesuai LLM_PROVIDER
        ai_reply = None
        source_name = "tfidf"

        if self._provider == "ollama":
            # 1. Selalu coba Ollama Qwen terlebih dahulu
            ai_reply = self._generate_with_ollama(user_text, contexts)
            if ai_reply:
                source_name = f"ollama ({self._ollama_model})"
            elif self._api_key:
                ai_reply = self._generate_with_gemini(user_text, contexts)
                if ai_reply:
                    source_name = "gemini"
        elif self._provider == "gemini":
            # 2. Selalu coba Gemini API terlebih dahulu
            ai_reply = self._generate_with_gemini(user_text, contexts)
            if ai_reply:
                source_name = "gemini"
            else:
                ai_reply = self._generate_with_ollama(user_text, contexts)
                if ai_reply:
                    source_name = f"ollama ({self._ollama_model})"
        else:
            # 3. Mode 'auto': Coba Gemini, fallback ke Ollama Qwen
            ai_reply = self._generate_with_gemini(user_text, contexts)
            if ai_reply:
                source_name = "gemini"
            else:
                ai_reply = self._generate_with_ollama(user_text, contexts)
                if ai_reply:
                    source_name = f"ollama ({self._ollama_model})"

        if ai_reply:
            return {
                "answer": ai_reply,
                "page": contexts[0]["page"],
                "score": contexts[0]["score"],
                "source": source_name,
            }

        # 4. Fallback jika semua LLM offline
        best = contexts[0]
        return {
            "answer": best["answer"],
            "page": best["page"],
            "score": best["score"],
            "source": "tfidf",
        }


# Singleton instance
_engine: Optional[RAGEngine] = None


def get_engine() -> RAGEngine:
    global _engine
    if _engine is None:
        _engine = RAGEngine()
    return _engine
