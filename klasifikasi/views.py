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
    # Coba baca dari file yang disimpan saat build
    if os.path.exists('/tweet-harvest-path.txt'):
        with open('/tweet-harvest-path.txt') as f:
            path = f.read().strip()
            if path and os.path.exists(path):
                print(f"[STARTUP] tweet-harvest dari file: {path}")
                return path

    # Coba lokasi umum
    candidates = [
        "/usr/local/bin/tweet-harvest",
        "/usr/bin/tweet-harvest",
        "/usr/local/lib/node_modules/.bin/tweet-harvest",
        "/usr/lib/node_modules/.bin/tweet-harvest",
    ]
    for path in candidates:
        if os.path.exists(path):
            print(f"[STARTUP] tweet-harvest ditemukan: {path}")
            return path

    # Coba via which
    try:
        result = subprocess.run(
            ["which", "tweet-harvest"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            print(f"[STARTUP] tweet-harvest via which: {path}")
            return path
    except:
        pass

    print("[STARTUP] tweet-harvest TIDAK DITEMUKAN!")
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
        token = request.POST.get("auth_token")

        if not keyword or not token:
            return render_error(request, "Keyword dan Token wajib diisi!")

        if TWEET_HARVEST_BIN is None:
            return render_error(request, "tweet-harvest tidak ditemukan di server.")

        output_dir = os.path.join(BASE_DIR, "tweets-data")
        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, "hasil.csv")

        if os.path.exists(file_path):
            os.remove(file_path)

        query = f"{keyword} lang:id"

        # ==========================
        # CRAWLING
        # ==========================
        try:
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
                    "-l", "100",
                    "-o", file_path,
                ],
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=180,
                env=env,
            )

            if result.returncode != 0:
                stdout_tail = result.stdout[-500:] if result.stdout else "(kosong)"
                stderr_tail = result.stderr[-500:] if result.stderr else "(kosong)"
                return render_error(request, f"STDOUT: {stdout_tail} || STDERR: {stderr_tail}")

            if not os.path.exists(file_path):
                stdout_tail = result.stdout[-500:] if result.stdout else "(kosong)"
                return render_error(request, f"File tidak terbuat. STDOUT: {stdout_tail}")

        except subprocess.TimeoutExpired:
            return render_error(request, "Crawling timeout (>180 detik).")
        except Exception as e:
            return render_error(request, f"Error: {str(e)}")

        # ==========================
        # LOAD CSV
        # ==========================
        try:
            df = pd.read_csv(file_path, sep=";")
        except Exception as e:
            return render_error(request, f"Gagal baca CSV: {str(e)}")

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