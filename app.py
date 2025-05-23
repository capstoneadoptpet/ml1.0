from flask import Flask, render_template, request, jsonify
import pymysql
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics.pairwise import cosine_similarity

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# ============================================================================ 
# KONFIGURASI DATABASE
# ============================================================================

host = '43.156.249.217'  # Ganti dengan host database Anda
user = 'root'  # Ganti dengan username Anda
password = '473N8ZJU25aGsr6K10DWBhCzFo9fHOMA'  # Ganti dengan password Anda
database = 'ml'  # Ganti dengan nama database Anda
port = 30201

# ============================================================================ 
# PERSIAPAN DATA DAN MODEL
# ============================================================================

# Fungsi untuk mengambil data dari database
def get_data_from_db():
    try:
        # Membuat koneksi menggunakan pymysql
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )
        # Jika koneksi berhasil
        print("Koneksi ke database berhasil!")
        
        query = "SELECT id, nama, jenis, breed, gender, usia, warna FROM Dataset"
        # Menggunakan cursor untuk mengeksekusi query
        with connection.cursor() as cursor:
            cursor.execute(query)
            # Mengambil semua hasil query
            results = cursor.fetchall()
            
            # Mengonversi hasil menjadi DataFrame Pandas
            df = pd.DataFrame(results, columns=['id', 'nama', 'jenis', 'breed', 'gender', 'usia', 'warna'])
        
        # Menutup koneksi
        connection.close()
        return df
        
    except pymysql.MySQLError as e:
        print(f"Terjadi kesalahan saat menghubungkan ke database: {e}")
        return None

# Membaca dataset dari database
df = get_data_from_db()
if df is None:
    raise Exception("Gagal mengambil data dari database")

# Mendefinisikan fitur untuk model
categorical_features = ['jenis', 'breed', 'gender', 'usia']
numeric_features = ['warna']

# Inisialisasi dan fit OneHotEncoder
encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
encoded_cat = encoder.fit_transform(df[categorical_features])
numeric_array = df[numeric_features].to_numpy()
feature_vectors = np.hstack([encoded_cat, numeric_array])

# Membuat dictionary mapping jenis hewan ke breed-nya
breed_dict = df.groupby('jenis')['breed'].unique().apply(list).to_dict()

# ============================================================================ 
# FUNGSI REKOMENDASI
# ============================================================================

def recommend_by_preferences(preferences: dict, top_n=5):
    """
    Menghasilkan rekomendasi hewan berdasarkan preferensi pengguna
    
    Args:
        preferences (dict): Dictionary berisi preferensi pengguna
        top_n (int): Jumlah rekomendasi yang diinginkan
        
    Returns:
        DataFrame: Hasil rekomendasi dengan skor kemiripan
    """
    # Transformasi input pengguna
    user_df = pd.DataFrame([preferences])
    encoded_user_cat = encoder.transform(user_df[categorical_features])
    user_num = np.array([[preferences['warna']]])
    user_vector = np.hstack([encoded_user_cat, user_num])
    
    # Hitung similarity dan ambil top-n rekomendasi
    similarity_scores = cosine_similarity(user_vector, feature_vectors)[0]
    top_indices = similarity_scores.argsort()[::-1][:top_n]
    
    # Siapkan hasil rekomendasi
    rekomendasi = df.iloc[top_indices].copy()
    rekomendasi['similarity_score'] = similarity_scores[top_indices]
    return rekomendasi[['id', 'nama', 'jenis', 'breed', 'gender', 'usia', 'warna', 'similarity_score']]

# ============================================================================ 
# FUNGSI DATABASE
# ============================================================================

def save_recommendation_to_db(recommendations):
    """
    Menyimpan hasil rekomendasi ke database
    
    Args:
        recommendations (list): List hasil rekomendasi untuk disimpan
        
    Returns:
        bool: Status keberhasilan penyimpanan
    """
    try:
        # Koneksi menggunakan pymysql
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )
        
        cursor = connection.cursor()
        
        # Query untuk insert data
        query = """
        INSERT INTO result
        (ID, Nama, Jenis, Breed, Gender, Usia, Warna, `Skor kemiripan`)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Insert setiap rekomendasi
        for rec in recommendations:
            values = (
                rec['id'], rec['nama'], rec['jenis'], rec['breed'],
                rec['gender'], rec['usia'], rec['warna'], rec['similarity_score']
            )
            cursor.execute(query, values)

        connection.commit()
        return True
        
    except Exception as e:
        print(f"Error saving to database: {str(e)}")
        return False
        
    finally:
        if 'connection' in locals() and connection.open:
            cursor.close()
            connection.close()

# ============================================================================ 
# ROUTES
# ============================================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    """Halaman utama dengan form input"""
    rekomendasi = None
    if request.method == 'POST':
        user_input = {
            'jenis': request.form['jenis'],
            'breed': request.form['breed'],
            'gender': request.form['gender'],
            'usia': request.form['usia'],
            'warna': int(request.form['warna'])
        }
        rekomendasi = recommend_by_preferences(user_input, top_n=10).to_dict(orient='records')
        save_recommendation_to_db(rekomendasi)

    jenis_list = list(breed_dict.keys())
    return render_template('index.html', rekomendasi=rekomendasi, jenis_list=jenis_list)

@app.route('/get_breeds')
def get_breeds():
    """Endpoint AJAX untuk mendapatkan breed berdasarkan jenis"""
    jenis = request.args.get('jenis')
    breeds = breed_dict.get(jenis, [])
    return jsonify(breeds)

@app.route('/api/recommend', methods=['POST'])
def api_recommend():
    """Endpoint API untuk rekomendasi via POST JSON"""
    data = request.get_json()

    # Validasi input
    required_fields = ['jenis', 'breed', 'gender', 'usia', 'warna']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing one or more required fields.'}), 400

    try:
        user_input = {
            'jenis': data['jenis'],
            'breed': data['breed'],
            'gender': data['gender'],
            'usia': data['usia'],
            'warna': int(data['warna'])
        }

        hasil_rekomendasi = recommend_by_preferences(user_input, top_n=10)
        recommendations = hasil_rekomendasi.to_dict(orient='records')
        
        # Simpan ke database
        save_recommendation_to_db(recommendations)
        return jsonify(recommendations)

    except Exception as e:
        print("error: ", e)
        return jsonify({'error': str(e)}), 500

# ============================================================================ 
# MAIN
# ============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)