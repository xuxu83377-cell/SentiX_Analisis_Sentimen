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

kamus_path = os.path.join(BASE_DIR, "Kamuscu.txt")
if os.path.exists(kamus_path):
    with open(kamus_path, "r", encoding="utf-8") as f:
        for baris in f:
            kata = baris.strip().split()
            if len(kata) == 2:
                kamus_normalisasi[kata[0]] = kata[1]

# ==============================
# LEXICON (FIX AMAN)
# ==============================
def load_lexicon(file_path):
    try:
        df = pd.read_csv(file_path, sep="\t")

        # kalau kolom aneh → fallback
        if len(df.columns) < 2:
            raise ValueError("Format salah")

    except:
        # fallback kalau file tanpa header
        df = pd.read_csv(file_path, sep="\t", header=None)
        df.columns = ['word', 'weight']

    return df

pos_path = os.path.join(BASE_DIR, "positive.tsv")
neg_path = os.path.join(BASE_DIR, "negative.tsv")

pos_df = load_lexicon(pos_path)
neg_df = load_lexicon(neg_path)

print("Kolom positif:", pos_df.columns)
print("Kolom negatif:", neg_df.columns)

# ==============================
# FLEXIBLE COLUMN
# ==============================
def ambil_kata(df):
    if "word" in df.columns:
        return set(df["word"].astype(str))
    elif "kata" in df.columns:
        return set(df["kata"].astype(str))
    else:
        return set(df.iloc[:, 0].astype(str))

kata_positif = ambil_kata(pos_df)
kata_negatif = ambil_kata(neg_df)

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