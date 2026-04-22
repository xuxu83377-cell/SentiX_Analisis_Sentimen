import os
import re
import pandas as pd
import nltk

nltk.download('stopwords')
nltk.download('punkt')

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

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
# LEXICON (FIX FINAL)
# ==============================
pos_df = pd.read_csv(os.path.join(BASE_DIR, "positive.tsv"), sep="\t", engine="python")
neg_df = pd.read_csv(os.path.join(BASE_DIR, "negative.tsv"), sep="\t", engine="python")

print("Kolom positif:", pos_df.columns)
print("Kolom negatif:", neg_df.columns)

# FLEXIBLE COLUMN (word / kata)
if "word" in pos_df.columns:
    kata_positif = set(pos_df["word"])
elif "kata" in pos_df.columns:
    kata_positif = set(pos_df["kata"])
else:
    kata_positif = set(pos_df.iloc[:, 0])

if "word" in neg_df.columns:
    kata_negatif = set(neg_df["word"])
elif "kata" in neg_df.columns:
    kata_negatif = set(neg_df["kata"])
else:
    kata_negatif = set(neg_df.iloc[:, 0])

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

    teks = re.sub(
        "["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002700-\U000027BF"
        u"\U000024C2-\U0001F251"
        "]+",
        "",
        teks
    )

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