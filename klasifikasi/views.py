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

    # ==============================
    # JALANKAN SAAT FORM DIKIRIM
    # ==============================
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
            # CRAWLING DATA
            # ==============================
            #subprocess.run(
                [
                    r"C:\Program Files\nodejs\npx.cmd",
                    "tweet-harvest",
                    "-t", token,
                    "-s", query,
                    "-l", "10",
                    "-o", "hasil.csv"
                ],
                cwd=BASE_DIR

            # ==============================
            # CEK HASIL
            # ==============================
            if not os.path.exists(file_path):
                error = "Crawling gagal."

            else:
                df = pd.read_csv(file_path)

                if df.empty:
                    error = "Data kosong."

                else:
                    # ==============================
                    # PREPROCESSING
                    # ==============================
                    df['clean'] = df['full_text'].apply(preprocessing)

                    print("\n===== HASIL PREPROCESSING =====\n")

                    def wrap_text(text, width=40):
                        return "\n".join(textwrap.wrap(str(text), width))

                    df_display = df[['full_text', 'clean']].head(10).copy()
                    df_display['full_text'] = df_display['full_text'].apply(lambda x: wrap_text(x, 40))
                    df_display['clean'] = df_display['clean'].apply(lambda x: wrap_text(x, 40))

                    print(tabulate(
                        df_display,
                        headers=['Tweet Asli', 'Hasil Preprocessing'],
                        tablefmt='fancy_grid',
                        showindex=False
                    ))

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
                    # PRINT KE TERMINAL (PENTING 🔥)
                    # ==============================
                    print("\n==============================")
                    print("     CONFUSION MATRIX")
                    print("==============================")
                    print(f"TP (True Positive)  : {tp}")
                    print(f"TN (True Negative)  : {tn}")
                    print(f"FP (False Positive) : {fp}")
                    print(f"FN (False Negative) : {fn}")

                    print("\n==============================")
                    print("     EVALUASI MODEL")
                    print("==============================")
                    print(f"Accuracy  : {evaluation.get('accuracy', 0):.4f}")
                    print(f"Precision : {evaluation.get('precision', 0):.4f}")
                    print(f"Recall    : {evaluation.get('recall', 0):.4f}")
                    print(f"F1 Score  : {evaluation.get('f1', 0):.4f}")
                    print("==============================\n")

                    # ==============================
                    # WORDCLOUD
                    # ==============================
                    df_pos = df[df['Sentimen'] == 'Positif']
                    df_neg = df[df['Sentimen'] == 'Negatif']

                    pos_words = " ".join(df_pos['clean']).split()
                    neg_words = " ".join(df_neg['clean']).split()

                    pos_set = set(pos_words)
                    neg_set = set(neg_words)

                    pos_unique = [w for w in pos_words if w not in neg_set]
                    neg_unique = [w for w in neg_words if w not in pos_set]

                    pos_text = " ".join(pos_unique)
                    neg_text = " ".join(neg_unique)

                    # Wordcloud Positif
                    if pos_text.strip():
                        wc_pos = WordCloud(
                            width=800,
                            height=400,
                            background_color='white',
                            colormap='Greens',
                            collocations=False
                        ).generate(pos_text)

                        buffer = BytesIO()
                        wc_pos.to_image().save(buffer, format='PNG')
                        wordcloud_pos = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        buffer.close()

                    # Wordcloud Negatif
                    if neg_text.strip():
                        wc_neg = WordCloud(
                            width=800,
                            height=400,
                            background_color='white',
                            colormap='Reds',
                            collocations=False
                        ).generate(neg_text)

                        buffer = BytesIO()
                        wc_neg.to_image().save(buffer, format='PNG')
                        wordcloud_neg = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        buffer.close()

    # ==============================
    # RETURN KE HTML
    # ==============================
    return render(request, 'home.html', {
        'data': data,
        'total': total,
        'pos': pos,
        'neg': neg,
        'wordcloud_pos': wordcloud_pos,
        'wordcloud_neg': wordcloud_neg,
        'error': error
    })
