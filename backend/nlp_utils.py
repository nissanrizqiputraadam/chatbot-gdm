import re

# Leksikon slang (Pertemuan 2): bentuk tidak baku -> bentuk baku
SLANG = {
    "gk": "tidak", "ga": "tidak", "gak": "tidak", "nggak": "tidak",
    "tdk": "tidak", "bgt": "banget", "yg": "yang", "dgn": "dengan",
    "utk": "untuk", "krn": "karena", "sy": "saya", "aq": "saya",
    "bumil": "ibu hamil", "knp": "kenapa", "gmn": "bagaimana",
    "gimana": "bagaimana", "emg": "memang", "udh": "sudah",
}

_stemmer = None


def _get_stemmer():
    """Stemmer Sastrawi dibuat sekali saja (pembuatannya lambat)."""
    global _stemmer
    if _stemmer is None:
        from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
        _stemmer = StemmerFactory().create_stemmer()
    return _stemmer


def clean_text(text, use_stemming=False):
    text = str(text).lower()                              # 1. case folding
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)    # 2. hapus URL
    text = re.sub(r"[^a-z0-9\s]", " ", text)              # 3. hapus tanda baca, ANGKA DIPERTAHANKAN
    text = re.sub(r"\s+", " ", text).strip()              # 4. rapikan spasi
    tokens = [SLANG.get(t, t) for t in text.split()]      # 5. tokenisasi + normalisasi slang
    if use_stemming:
        stem = _get_stemmer().stem
        tokens = [stem(t) for t in tokens]
    return " ".join(tokens)