from flask import Flask, render_template, request, jsonify
import pymysql
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics.pairwise import cosine_similarity
import os
from pymysql.cursors import DictCursor
import time

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# ============================================================================ 
# KONFIGURASI DATABASE
# ============================================================================

# Get database configuration from environment variables with fallbacks
host = os.getenv('DB_HOST', '43.156.249.217')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD', '473N8ZJU25aGsr6K10DWBhCzFo9fHOMA')
database = os.getenv('DB_NAME', 'ml')
port = int(os.getenv('DB_PORT', '30201'))

# Database connection pool configuration
DB_POOL = None
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

def get_db_connection():
    """Get a database connection from the pool with retry mechanism"""
    global DB_POOL
    
    for attempt in range(MAX_RETRIES):
        try:
            if DB_POOL is None:
                DB_POOL = pymysql.connect(
                    host=host,
                    user=user,
                    password=password,
                    database=database,
                    port=port,
                    cursorclass=DictCursor,
                    connect_timeout=5,
                    read_timeout=30,
                    write_timeout=30
                )
            elif not DB_POOL.open:
                DB_POOL.ping(reconnect=True)
            return DB_POOL
        except pymysql.Error as e:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(RETRY_DELAY)
            continue

# ============================================================================ 
# HEALTH CHECK
# ============================================================================

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT 1')
        return jsonify({"status": "healthy", "database": "connected"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# ============================================================================ 
# PERSIAPAN DATA DAN MODEL
# ============================================================================

# Global variables for ML model
df = None
encoder = None
feature_vectors = None
breed_dict = None
# Define feature columns globally
categorical_features = ['jenis', 'breed', 'gender', 'usia']
numeric_features = ['warna']

def initialize_ml_components():
    """Initialize ML components with proper error handling"""
    global df, encoder, feature_vectors, breed_dict
    
    try:
        # Membuat koneksi menggunakan pymysql
        connection = get_db_connection()
        
        query = "SELECT id, nama, jenis, breed, gender, usia, warna FROM Dataset"
        # Menggunakan cursor untuk mengeksekusi query
        with connection.cursor() as cursor:
            cursor.execute(query)
            # Mengambil semua hasil query
            results = cursor.fetchall()
            
            # Mengonversi hasil menjadi DataFrame Pandas
            df = pd.DataFrame(results)
        
        # Inisialisasi dan fit OneHotEncoder
        encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
        encoded_cat = encoder.fit_transform(df[categorical_features])
        numeric_array = df[numeric_features].to_numpy()
        feature_vectors = np.hstack([encoded_cat, numeric_array])

        # Membuat dictionary mapping jenis hewan ke breed-nya
        breed_dict = df.groupby('jenis')['breed'].unique().apply(list).to_dict()
        
        return True
        
    except Exception as e:
        app.logger.error(f"Error initializing ML components: {str(e)}")
        return False

# Initialize ML components on startup
if not initialize_ml_components():
    raise RuntimeError("Failed to initialize ML components")

# ============================================================================ 
# FUNGSI REKOMENDASI
# ============================================================================

def recommend_by_preferences(preferences: dict, top_n=5):
    """
    Menghasilkan rekomendasi hewan berdasarkan preferensi pengguna
    """
    try:
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
    except Exception as e:
        app.logger.error(f"Error in recommendation: {str(e)}")
        raise

# ============================================================================ 
# FUNGSI DATABASE
# ============================================================================

def save_recommendation_to_db(recommendations):
    """
    Menyimpan hasil rekomendasi ke database dengan proper error handling
    """
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
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
        app.logger.error(f"Error saving to database: {str(e)}")
        if connection:
            connection.rollback()
        return False

# ============================================================================ 
# ROUTES
# ============================================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    """Halaman utama dengan form input"""
    try:
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
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/get_breeds')
def get_breeds():
    """Endpoint AJAX untuk mendapatkan breed berdasarkan jenis"""
    try:
        jenis = request.args.get('jenis')
        breeds = breed_dict.get(jenis, [])
        return jsonify(breeds)
    except Exception as e:
        app.logger.error(f"Error in get_breeds route: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/recommend', methods=['POST'])
def api_recommend():
    """Endpoint API untuk rekomendasi via POST JSON"""
    try:
        data = request.get_json()

        # Validasi input
        required_fields = ['jenis', 'breed', 'gender', 'usia', 'warna']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing one or more required fields.'}), 400

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
        if not save_recommendation_to_db(recommendations):
            app.logger.warning("Failed to save recommendations to database")
            
        return jsonify(recommendations)

    except Exception as e:
        app.logger.error(f"Error in api_recommend route: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ============================================================================ 
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Disable debug mode in production
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=False)
