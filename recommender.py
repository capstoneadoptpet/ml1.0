import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics.pairwise import cosine_similarity
import osimport

# === Load dataset ===
df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'modified_dataframe.csv'))

# === Fitur yang digunakan ===
categorical_features = ['jenis', 'breed', 'gender', 'usia']
numeric_features = ['warna']

# === One-Hot Encoding ===
encoder = OneHotEncoder(sparse_output=False)
encoded_cat = encoder.fit_transform(df[categorical_features])
numeric_array = df[numeric_features].to_numpy()
feature_vectors = np.hstack([encoded_cat, numeric_array])

# === Fungsi rekomendasi berdasarkan preferensi user ===
def recommend_by_preferences(preferences: dict, top_n=5):
    """
    Memberikan rekomendasi hewan berdasarkan preferensi user.

    Parameters:
        preferences (dict): Referensi fitur user, misal:
            {
                'jenis': 'kucing',
                'breed': 'anggora',
                'gender': 'jantan',
                'usia': 'muda',
                'warna': 2
            }
        top_n (int): Jumlah hasil rekomendasi teratas.

    Returns:
        pd.DataFrame: DataFrame berisi hewan yang direkomendasikan beserta skor kemiripan.
    """
    user_df = pd.DataFrame([preferences])
    encoded_user_cat = encoder.transform(user_df[categorical_features])
    user_num = np.array([[preferences['warna']]])
    user_vector = np.hstack([encoded_user_cat, user_num])

    similarity_scores = cosine_similarity(user_vector, feature_vectors)[0]
    top_indices = similarity_scores.argsort()[::-1][:top_n]

    rekomendasi = df.iloc[top_indices].copy()
    rekomendasi['similarity_score'] = similarity_scores[top_indices]
    return rekomendasi.drop_duplicates(subset=categorical_features)

# === Contoh penggunaan lokal ===
if __name__ == "__main__":
    user_input = {
        'jenis': 'kucing',
        'breed': 'anggora',
        'gender': 'jantan',
        'usia': 'muda',
        'warna': 2
    }

    hasil = recommend_by_preferences(user_input, top_n=5)
    print(hasil[['id', 'nama', 'jenis', 'breed', 'similarity_score']])
