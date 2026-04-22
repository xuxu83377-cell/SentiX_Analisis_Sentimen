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
from tabulate import tabulate
import textwrap

BASE_DIR = settings.BASE_DIR

# ==============================
# LOAD MODEL
# ==============================
model = pickle.load(open(os.path.join(BASE_DIR, 'klasifikasi/model/model_svm.pkl'), 'rb'))
vectorizer = pickle.load(open(os.path.join(BASE_DIR, 'klasifikasi/model/tfidf.pkl'), 'rb'))
encoder = pickle.load(open(os.path.join(BASE_DIR, 'klasifikasi/model/encoder.pkl'), 'rb'))

# ==============================
# LOAD EVALUASI
# ==============================
with open(os.path.join(BASE_DIR, 'klasifikasi/model/evaluasi.json')) as f:
    evaluation = json.load(f)

tn = evaluation.get("tn", 0)
fp = evaluation.get("fp", 0)
fn = evaluation.get("fn", 0)
tp = evaluation.get("tp", 0)

# ==============================
# VIEW
# ==============================
def home(request):

    data = None
    error = None
    total = 0
    pos = 0
    neg = 0
    wordcloud_pos = None
    wordcloud_neg = None

    if request.method == 'POST':

        keyword = request.POST.get('keyword')
        token = request.POST.get('auth_token')

        query = f"{keyword} lang:id"

        if not keyword or not token:
            error = "Keyword dan Token tidak boleh kosong."

        else:
            tweets_folder = os.path.join(BASE_DIR, "tweets-data")
            os.makedirs(tweets_folder, exist_ok=True)

            file_path = os.path.join(tweets_folder, "hasil.csv")

            if os.path.exists(file_path):
                os.remove(file_path)

            # ==============================
            # CRAWLING DATA (FIX TOTAL)
            # ==============================
            try:
                result = subprocess.run(
                    [
                        "npx",
                        "tweet-harvest",
                        "-t", token,
                        "-s", query,
                        "-l", "10",
                        "-o", "hasil.csv"
                    ],
                    cwd=BASE_DIR,
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)

                if result.returncode != 0:
                    error = "Crawling gagal dijalankan."

            except subprocess.TimeoutExpired:
                error = "Crawling timeout."
            except FileNotFoundError:
                error = "npx tidak ditemukan. Install Node.js."
            except Exception as e:
                error = str(e)

            # ==============================
            # CEK HASIL
            # ==============================
            if not error and os.path.exists(file_path):

                df = pd.read_csv(file_path)

                if not df.empty:

                    df['clean'] = df['full_text'].apply(preprocessing)

                    X = vectorizer.transform(df['clean'])
                    pred = model.predict(X)
                    df['Sentimen'] = encoder.inverse_transform(pred)

                    data = df[['full_text', 'Sentimen']].to_dict('records')
                    total = len(df)
                    pos = (df['Sentimen'] == 'Positif').sum()
                    neg = (df['Sentimen'] == 'Negatif').sum()

                    # WORDCLOUD
                    df_pos = df[df['Sentimen'] == 'Positif']
                    df_neg = df[df['Sentimen'] == 'Negatif']

                    pos_text = " ".join(df_pos['clean'])
                    neg_text = " ".join(df_neg['clean'])

                    if pos_text.strip():
                        wc = WordCloud(width=800, height=400, background_color='white').generate(pos_text)
                        buffer = BytesIO()
                        wc.to_image().save(buffer, format='PNG')
                        wordcloud_pos = base64.b64encode(buffer.getvalue()).decode('utf-8')

                    if neg_text.strip():
                        wc = WordCloud(width=800, height=400, background_color='white').generate(neg_text)
                        buffer = BytesIO()
                        wc.to_image().save(buffer, format='PNG')
                        wordcloud_neg = base64.b64encode(buffer.getvalue()).decode('utf-8')

                else:
                    error = "Data kosong dari crawling."

            else:
                if not error:
                    error = "File hasil.csv tidak ditemukan."

    return render(request, 'home.html', {
        'data': data,
        'total': total,
        'pos': pos,
        'neg': neg,
        'wordcloud_pos': wordcloud_pos,
        'wordcloud_neg': wordcloud_neg,
        'error': error
    })