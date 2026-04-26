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
            error = "Keyword dan Token wajib diisi!"
            return render(request, "home.html", {"error": error})

        output_dir = os.path.join(BASE_DIR, "tweets-data")
        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, "hasil.csv")
        backup_path = os.path.join(output_dir, "backup.csv")

        # Hapus file lama agar tidak terbaca data sebelumnya
        if os.path.exists(file_path):
            os.remove(file_path)

        query = f"{keyword} lang:id"

        # ==========================
        # CRAWLING + FALLBACK
        # ==========================
        try:
            # Cek apakah npx tersedia
            check_npx = subprocess.run(
                ["which", "npx"],
                capture_output=True,
                text=True
            )

            if check_npx.returncode != 0:
                print("NPX tidak ditemukan, pakai backup")
                file_path = backup_path
            else:
                result = subprocess.run(
                    [
                        "npx", "--yes", "tweet-harvest@latest",
                        "--token", token,       # FIX: -t → --token
                        "-s", query,
                        "-l", "100",            # FIX: naikkan dari 10 → 100
                        "-o", file_path,
                        "--headless", "true"    # WAJIB: agar jalan di Railway/server
                    ],
                    cwd=output_dir,
                    capture_output=True,
                    text=True,
                    timeout=120,               # FIX: dari 15 → 120 detik
                    env={
                        **os.environ,
                        # Path Chromium di Docker Railway
                        "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",
                        # Paksa headless, tidak butuh display
                        "DISPLAY": "",
                    }
                )

                print("===== STDOUT =====")
                print(result.stdout)

                print("===== STDERR =====")
                print(result.stderr)

                # Kalau crawling gagal → fallback ke backup
                if result.returncode != 0:
                    print("Crawling gagal (returncode != 0), pakai backup")
                    file_path = backup_path

                # Kalau file tidak terbuat walau returncode 0 → fallback
                elif not os.path.exists(file_path):
                    print("File output tidak ditemukan walau returncode 0, pakai backup")
                    file_path = backup_path

        except subprocess.TimeoutExpired:
            print("Crawling timeout (>120 detik), pakai backup")
            file_path = backup_path

        except FileNotFoundError:
            print("npx tidak ditemukan di PATH, pakai backup")
            file_path = backup_path

        except Exception as e:
            print(f"Error tidak terduga saat crawling: {str(e)}")
            file_path = backup_path

        # ==========================
        # CEK FILE HASIL
        # ==========================
        if not os.path.exists(file_path):
            error = "Crawling gagal dan file backup tidak ditemukan."
            return render(request, "home.html", {
                "error": error,
                "tn": tn, "fp": fp, "fn": fn, "tp": tp,
                "accuracy": evaluation.get("accuracy", 0),
                "precision": evaluation.get("precision", 0),
                "recall": evaluation.get("recall", 0),
                "f1": evaluation.get("f1", 0),
            })

        # ==========================
        # BACA CSV
        # ==========================
        try:
            df = pd.read_csv(file_path, sep=";")  # tweet-harvest pakai separator ";"
        except Exception as e:
            error = f"Gagal membaca file CSV: {str(e)}"
            return render(request, "home.html", {
                "error": error,
                "tn": tn, "fp": fp, "fn": fn, "tp": tp,
                "accuracy": evaluation.get("accuracy", 0),
                "precision": evaluation.get("precision", 0),
                "recall": evaluation.get("recall", 0),
                "f1": evaluation.get("f1", 0),
            })

        # Cek kolom full_text tersedia
        if "full_text" not in df.columns:
            error = f"Kolom 'full_text' tidak ditemukan. Kolom tersedia: {list(df.columns)}"
            return render(request, "home.html", {
                "error": error,
                "tn": tn, "fp": fp, "fn": fn, "tp": tp,
                "accuracy": evaluation.get("accuracy", 0),
                "precision": evaluation.get("precision", 0),
                "recall": evaluation.get("recall", 0),
                "f1": evaluation.get("f1", 0),
            })

        if df.empty:
            error = "Data kosong, tidak ada tweet yang ditemukan."
            return render(request, "home.html", {
                "error": error,
                "tn": tn, "fp": fp, "fn": fn, "tp": tp,
                "accuracy": evaluation.get("accuracy", 0),
                "precision": evaluation.get("precision", 0),
                "recall": evaluation.get("recall", 0),
                "f1": evaluation.get("f1", 0),
            })

        # ==========================
        # PREPROCESSING
        # ==========================
        df["clean"] = df["full_text"].apply(preprocessing)

        # Hapus baris dengan hasil clean kosong
        df = df[df["clean"].str.strip() != ""]
        df = df.dropna(subset=["clean"])

        if df.empty:
            error = "Semua tweet kosong setelah preprocessing."
            return render(request, "home.html", {
                "error": error,
                "tn": tn, "fp": fp, "fn": fn, "tp": tp,
                "accuracy": evaluation.get("accuracy", 0),
                "precision": evaluation.get("precision", 0),
                "recall": evaluation.get("recall", 0),
                "f1": evaluation.get("f1", 0),
            })

        # ==========================
        # PREDIKSI SENTIMEN
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
        df_pos = df[df["Sentimen"] == "Positif"]
        df_neg = df[df["Sentimen"] == "Negatif"]

        def make_wc(text, color):
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

        wordcloud_pos = make_wc(" ".join(df_pos["clean"].tolist()), "Greens")
        wordcloud_neg = make_wc(" ".join(df_neg["clean"].tolist()), "Reds")

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