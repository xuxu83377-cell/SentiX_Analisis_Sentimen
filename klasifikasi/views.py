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
            # CRAWLING DATA (FIX)
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
                    check=True
                )

                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)

            except subprocess.CalledProcessError as e:
                error = "Gagal menjalankan crawling."
                print("ERROR:", e.stderr)

            # ==============================
            # CEK HASIL
            # ==============================
            if not os.path.exists(file_path):
                error = "Crawling gagal atau file tidak ditemukan."

            else:
                df = pd.read_csv(file_path)

                if df.empty:
                    error = "Data kosong."

                else:
                    # ==============================
                    # PREPROCESSING
                    # ==============================
                    df['clean'] = df['full_text'].apply(preprocessing)

                    # ==============================
                    # PREDIKSI
                    # ==============================
                    X = vectorizer.transform(df['clean'])
                    pred = model.predict(X)
                    df['Sentimen'] = encoder.inverse_transform(pred)

                    data = df[['full_text', 'Sentimen']].to_dict('records')
                    total = len(df)
                    pos = (df['Sentimen'] == 'Positif').sum()
                    neg = (df['Sentimen'] == 'Negatif').sum()

                    # ==============================
                    # WORDCLOUD
                    # ==============================
                    df_pos = df[df['Sentimen'] == 'Positif']
                    df_neg = df[df['Sentimen'] == 'Negatif']

                    pos_text = " ".join(df_pos['clean'])
                    neg_text = " ".join(df_neg['clean'])

                    if pos_text.strip():
                        wc_pos = WordCloud(width=800, height=400, background_color='white').generate(pos_text)
                        buffer = BytesIO()
                        wc_pos.to_image().save(buffer, format='PNG')
                        wordcloud_pos = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        buffer.close()

                    if neg_text.strip():
                        wc_neg = WordCloud(width=800, height=400, background_color='white').generate(neg_text)
                        buffer = BytesIO()
                        wc_neg.to_image().save(buffer, format='PNG')
                        wordcloud_neg = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        buffer.close()

    return render(request, 'home.html', {
        'data': data,
        'total': total,
        'pos': pos,
        'neg': neg,
        'wordcloud_pos': wordcloud_pos,
        'wordcloud_neg': wordcloud_neg,
        'error': error
    })