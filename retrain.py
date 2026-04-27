import os
import json
import pickle
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from klasifikasi.utils import preprocessing

print("Loading dataset...")
data = pd.read_csv('dataset_label_lexicon.csv')

print("Preprocessing...")
data['clean'] = data['full_text'].apply(preprocessing)

X = data['clean']
Y = data['Label']

X_train, X_test, y_train, y_test = train_test_split(
    X, Y,
    test_size=0.2,
    random_state=42,
    stratify=Y
)

print("Vectorizing...")
vectorizer = TfidfVectorizer(max_features=5000)
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

encoder = LabelEncoder()
y_train_enc = encoder.fit_transform(y_train)
y_test_enc = encoder.transform(y_test)

print("Training model...")
model = SVC(kernel='linear', class_weight='balanced')
model.fit(X_train_vec, y_train_enc)

y_pred = model.predict(X_test_vec)

acc = accuracy_score(y_test_enc, y_pred)
report = classification_report(y_test_enc, y_pred, output_dict=True)
cm = confusion_matrix(y_test_enc, y_pred)

tn, fp, fn, tp = cm.ravel()

evaluation = {
    "accuracy": acc,
    "precision": report["1"]["precision"],
    "recall": report["1"]["recall"],
    "f1": report["1"]["f1-score"],
    "tp": int(tp),
    "tn": int(tn),
    "fp": int(fp),
    "fn": int(fn)
}

os.makedirs("klasifikasi/model", exist_ok=True)

pickle.dump(model, open('klasifikasi/model/model_svm.pkl', 'wb'))
pickle.dump(vectorizer, open('klasifikasi/model/tfidf.pkl', 'wb'))
pickle.dump(encoder, open('klasifikasi/model/encoder.pkl', 'wb'))

with open("klasifikasi/model/evaluasi.json", "w") as f:
    json.dump(evaluation, f)

print("✅ Model & evaluasi berhasil disimpan!")