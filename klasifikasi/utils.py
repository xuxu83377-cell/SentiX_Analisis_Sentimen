import os
import re
import pandas as pd
import nltk

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# ==============================
# FIX NLTK (BIAR TIDAK LOOPING)
# ==============================
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# ==============================
# STEMMER & STOPWORD
# ==============================
factory = StemmerFactory()
stemmer = factory.create_stemmer()

stopword = set(stopwords.words('indonesian'))
stopword.update([
    "yg", "jd", "aja", "nya", "nih", "sih",
    "banget", "ga", "gak", "nggak",
    "kalo", "kalau", "amp", "biar"
])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ==============================
# KAMUS NORMALISASI
# ==============================
kamus_normalisasi = {}

with open(os.path.join(BASE_DIR, "Kamuscu.txt"), "r", encoding="utf-8") as f:
    for baris in f:
        kata = baris.strip().split()
        if len(kata) == 2:
            kamus_normalisasi[kata[0]] = kata[1]

# ==============================
# LEXICON (FIX HEADER)
# ==============================
pos_df = pd.read_csv(
    os.path.join(BASE_DIR, "positive.tsv"),
    sep="\t",
    header=None,
    names=["word", "weight"]
)

neg_df = pd.read_csv(
    os.path.join(BASE_DIR, "negative.tsv"),
    sep="\t",
    header=None,
    names=["word", "weight"]
)

# ambil kolom kata
kata_positif = set(pos_df["word"].astype(str))
kata_negatif = set(neg_df["word"].astype(str))

# ==============================
# PREPROCESSING
# ==============================
def preprocessing(teks):
    teks = str(teks).lower()

    teks = re.sub(r'rt\s+', ' ', teks)
    teks = re.sub(r'@[A-Za-z0-9_]+', ' ', teks)
    teks = re.sub(r'#', '', teks)
    teks = re.sub(r'http\S+', ' ', teks)
    teks = re.sub(r'\d+', ' ', teks)

    teks = re.sub(r'[^a-z\s]', ' ', teks)
    teks = re.sub(r'\s+', ' ', teks).strip()

    token = word_tokenize(teks)
    token = [kamus_normalisasi.get(k, k) for k in token]
    token = [k for k in token if k not in stopword]
    token = [stemmer.stem(k) for k in token]
    token = [k for k in token if len(k) > 2]

    return " ".join(token)

# ==============================
# LEXICON LABEL
# ==============================
def lexicon_label(teks):
    skor = 0
    for kata in teks.split():
        if kata in kata_positif:
            skor += 1
        elif kata in kata_negatif:
            skor -= 1

    return "Positif" if skor > 0 else "Negatif"