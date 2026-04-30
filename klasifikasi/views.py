import subprocess
import os
import json
import pickle
import pandas as pd
from django.shortcuts import render
from django.conf import settings
from .utils import preprocessing
from wordcloud import WordCloud
import base64
from io import BytesIO

BASE_DIR = settings.BASE_DIR

# ==========================
# LOAD MODEL
# ==========================
model = pickle.load(open(os.path.join(BASE_DIR, 'klasifikasi/model/model_svm.pkl'), 'rb'))
vectorizer = pickle.load(open(os.path.join(BASE_DIR, 'klasifikasi/model/tfidf.pkl'), 'rb'))
encoder = pickle.load(open(os.path.join(BASE_DIR, 'klasifikasi/model/encoder.pkl'), 'rb'))

with open(os.path.join(BASE_DIR, 'klasifikasi/model/evaluasi.json')) as f:
    evaluation = json.load(f)

tn = evaluation.get("tn", 0)
fp = evaluation.get("fp", 0)
fn = evaluation.get("fn", 0)
tp = evaluation.get("tp", 0)

# ==========================
# CARI PATH TWEET-HARVEST
# ==========================
def get_tweet_harvest_path():
    if os.path.exists('/tweet-harvest-path.txt'):
        with open('/tweet-harvest-path.txt') as f:
            path = f.read().strip()
            if path and os.path.exists(path):
                return path

    candidates = [
        "/usr/local/bin/tweet-harvest",
        "/usr/bin/tweet-harvest",
        "/usr/local/lib/node_modules/.bin/tweet-harvest",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path

    try:
        result = subprocess.run(["which", "tweet-harvest"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass

    return None

TWEET_HARVEST_BIN = get_tweet_harvest_path()


# ==========================
# HELPER
# ==========================
def render_error(request, error_msg):
    return render(request, "home.html", {
        "error": error_msg,
        "tn": tn, "fp": fp, "fn": fn, "tp": tp,
        "accuracy": evaluation.get("accuracy", 0),
        "precision": evaluation.get("precision", 0),
        "recall": evaluation.get("recall", 0),
        "f1": evaluation.get("f1", 0),
    })


def make_wordcloud(text, color):
    if not text.strip():
        return None
    wc = WordCloud(
        width=800,
        height=400,
        background_color="white",
        colormap=color
    ).generate(text)
    buffer = BytesIO()
    wc.to_image().save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def cari_csv_keyword(keyword, output_dir):
    """Cari file CSV yang namanya mengandung keyword."""
    keyword_lower = keyword.lower().replace(" ", "_")
    if not os.path.exists(output_dir):
        return None
    for f in os.listdir(output_dir):
        if f.endswith(".csv") and keyword_lower in f.lower():
            return os.path.join(output_dir, f)
    # Cari juga file hasil.csv sebagai fallback
    hasil = os.path.join(output_dir, "hasil.csv")
    if os.path.exists(hasil):
        return hasil
    return None


# ==========================
# VIEW
# ==========================
def home(request):
    data = None
    error = None
    total = pos = neg = 0
    wordcloud_pos = None
    wordcloud_neg = None

    if request.method == "POST":

        keyword = request.POST.get("keyword")
        token = request.POST.get("auth_token", "")

        if not keyword:
            return render_error(request, "Keyword wajib diisi!")

        output_dir = "/app/tweets-data"
        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, "hasil.csv")
        keyword_safe = keyword.lower().replace(" ", "_")

        # ==========================
        # COBA CRAWLING DULU
        # ==========================
        crawling_berhasil = False

        if token and TWEET_HARVEST_BIN:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)

                query = f"{keyword} lang:id"
                env = {
                    **os.environ,
                    "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",
                    "DISPLAY": ":99",
                    "PATH": "/usr/local/bin:/usr/bin:/bin:" + os.environ.get("PATH", ""),
                }

                result = subprocess.run(
                    [
                        TWEET_HARVEST_BIN,
                        "--token", token,
                        "-s", query,
                        "-l", "30",
                        "-o", file_path,
                    ],
                    cwd="/app",
                    capture_output=True,
                    text=True,
                    timeout=180,
                    env=env,
                )

                if result.returncode == 0 and os.path.exists(file_path):
                    crawling_berhasil = True
                    print(f"Crawling berhasil: {file_path}")

            except Exception as e:
                print(f"Crawling gagal: {str(e)}")

        # ==========================
        # FALLBACK: CARI CSV LOKAL
        # ==========================
        if not crawling_berhasil:
            print("Crawling gagal/skip, cari CSV lokal...")
            file_path = cari_csv_keyword(keyword, output_dir)

            if file_path is None:
                return render_error(
                    request,
                    f"Data untuk keyword '{keyword}' tidak ditemukan. "
                    f"Silakan masukkan auth token Twitter yang valid."
                )

        # ==========================
        # LOAD CSV
        # ==========================
        try:
            df = pd.read_csv(file_path, sep=",")
        except Exception as e:
            try:
                df = pd.read_csv(file_path, sep=",")
            except Exception as e2:
                return render_error(request, f"Gagal baca CSV: {str(e2)}")

        if "full_text" not in df.columns:
            return render_error(request, f"Kolom full_text tidak ditemukan. Kolom: {list(df.columns)}")

        if df.empty:
            return render_error(request, "Data kosong.")

        # ==========================
        # PREPROCESSING
        # ==========================
        df["clean"] = df["full_text"].apply(preprocessing)
        df = df[df["clean"].str.strip() != ""].dropna(subset=["clean"])

        if df.empty:
            return render_error(request, "Data kosong setelah preprocessing.")

        # ==========================
        # PREDIKSI
        # ==========================
        X = vectorizer.transform(df["clean"])
        pred = model.predict(X)
        df["Sentimen"] = encoder.inverse_transform(pred)

        data = df[["full_text", "Sentimen"]].to_dict("records")

        total = len(df)
        pos = int((df["Sentimen"] == "Positif").sum())
        neg = int((df["Sentimen"] == "Negatif").sum())

        # ==========================
        # WORDCLOUD
        # ==========================
        wordcloud_pos = make_wordcloud(
            " ".join(df[df["Sentimen"] == "Positif"]["clean"]),
            "Greens"
        )
        wordcloud_neg = make_wordcloud(
            " ".join(df[df["Sentimen"] == "Negatif"]["clean"]),
            "Reds"
        )

    return render(request, "home.html", {
        "data": data,
        "total": total,
        "pos": pos,
        "neg": neg,
        "wordcloud_pos": wordcloud_pos,
        "wordcloud_neg": wordcloud_neg,
        "error": error,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "accuracy": evaluation.get("accuracy", 0),
        "precision": evaluation.get("precision", 0),
        "recall": evaluation.get("recall", 0),
        "f1": evaluation.get("f1", 0),
    })