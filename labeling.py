<<<<<<< HEAD
import pandas as pd
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

nltk.download('punkt')
nltk.download('stopwords')

# DATA HASIL CRAWLING
data = pd.read_csv("mbg_baru.csv")
data = data[['full_text']]
data = data.dropna()


# LEXICON
positive = pd.read_csv("positive.tsv", sep='\t')
negative = pd.read_csv("negative.tsv", sep='\t')

positive_words = set(positive['word'])
negative_words = set(negative['word'])


# PREPROCESSING

factory = StemmerFactory()
stemmer = factory.create_stemmer()
stopword_list = set(stopwords.words('indonesian'))

def preprocessing(teks):
    teks = str(teks).lower()
    teks = re.sub(r'rt\s+', ' ', teks)
    teks = re.sub(r'@[A-Za-z0-9_]+', ' ', teks)
    teks = re.sub(r'#[A-Za-z0-9_]+', ' ', teks)
    teks = re.sub(r'http\S+', ' ', teks)
    teks = re.sub(r'[0-9]+', ' ', teks)
    teks = re.sub(r'[^\w\s]', ' ', teks)
    teks = re.sub(r'\s+', ' ', teks).strip()

    tokens = word_tokenize(teks)
    tokens = [w for w in tokens if w not in stopword_list]
    tokens = [stemmer.stem(w) for w in tokens]

    return tokens


# PROSES LABELING

labels = []
clean_text = []

for teks in data['full_text']:
    tokens = preprocessing(teks)

    pos_score = 0
    neg_score = 0

    for word in tokens:
        if word in positive_words:
            pos_score += 1
        if word in negative_words:
            neg_score += 1

    if pos_score > neg_score:
        labels.append("Positif")
        clean_text.append(" ".join(tokens))
    elif neg_score > pos_score:
        labels.append("Negatif")
        clean_text.append(" ".join(tokens))
    else:
        # buang netral
        labels.append(None)
        clean_text.append(None)

data['clean'] = clean_text
data['Label'] = labels

# Buang data netral
data = data.dropna()

print("Distribusi Label Setelah Lexicon:")
print(data['Label'].value_counts())

# =========================
# SIMPAN DATA BARU
# =========================
data.to_csv("dataset_label_lexicon.csv", index=False)

=======
import pandas as pd
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

nltk.download('punkt')
nltk.download('stopwords')

# DATA HASIL CRAWLING
data = pd.read_csv("mbg_baru.csv")
data = data[['full_text']]
data = data.dropna()


# LEXICON
positive = pd.read_csv("positive.tsv", sep='\t')
negative = pd.read_csv("negative.tsv", sep='\t')

positive_words = set(positive['word'])
negative_words = set(negative['word'])


# PREPROCESSING

factory = StemmerFactory()
stemmer = factory.create_stemmer()
stopword_list = set(stopwords.words('indonesian'))

def preprocessing(teks):
    teks = str(teks).lower()
    teks = re.sub(r'rt\s+', ' ', teks)
    teks = re.sub(r'@[A-Za-z0-9_]+', ' ', teks)
    teks = re.sub(r'#[A-Za-z0-9_]+', ' ', teks)
    teks = re.sub(r'http\S+', ' ', teks)
    teks = re.sub(r'[0-9]+', ' ', teks)
    teks = re.sub(r'[^\w\s]', ' ', teks)
    teks = re.sub(r'\s+', ' ', teks).strip()

    tokens = word_tokenize(teks)
    tokens = [w for w in tokens if w not in stopword_list]
    tokens = [stemmer.stem(w) for w in tokens]

    return tokens


# PROSES LABELING

labels = []
clean_text = []

for teks in data['full_text']:
    tokens = preprocessing(teks)

    pos_score = 0
    neg_score = 0

    for word in tokens:
        if word in positive_words:
            pos_score += 1
        if word in negative_words:
            neg_score += 1

    if pos_score > neg_score:
        labels.append("Positif")
        clean_text.append(" ".join(tokens))
    elif neg_score > pos_score:
        labels.append("Negatif")
        clean_text.append(" ".join(tokens))
    else:
        # buang netral
        labels.append(None)
        clean_text.append(None)

data['clean'] = clean_text
data['Label'] = labels

# Buang data netral
data = data.dropna()

print("Distribusi Label Setelah Lexicon:")
print(data['Label'].value_counts())

# =========================
# SIMPAN DATA BARU
# =========================
data.to_csv("dataset_label_lexicon.csv", index=False)

>>>>>>> 8b62899785ea80fbaa1d0bbd208941b25e9a4417
print("\nDataset berhasil dibuat: dataset_label_lexicon.csv")