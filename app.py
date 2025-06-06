from flask import Flask, request, jsonify
import pymysql
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics.pairwise import cosine_similarity
import os
from pymysql.cursors import DictCursor
import time
import requests

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# ============================================================================ 
# KONFIGURASI DATABASE
# ============================================================================

# Get database configuration from environment variables with fallbacks
host = os.getenv('DB_HOST', '43.156.249.217')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD', '473N8ZJU25aGsr6K10DWBhCzFo9fHOMA')
database = os.getenv('DB_NAME', 'capstone2')
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

def get_information_id():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name FROM pet_categories")
            real_categories = pd.DataFrame(cursor.fetchall())
            
            cursor.execute("SELECT id, name FROM breeds")
            real_breeds = pd.DataFrame(cursor.fetchall())
            
            cursor.execute("SELECT id, category FROM ages")
            real_ages = pd.DataFrame(cursor.fetchall())

        # Combine all information into a dictionary
        all_data = {
            'jenis': real_categories,
            'breeds': real_breeds,
            'ages': real_ages,
        }

        return all_data
    except Exception as e:
        app.logger.error(f"Error mengambil data: {str(e)}")
        return None

def get_data_from_api():
    try:
        response = requests.get('https://backendcapstoneproject.zeabur.app/api/pets')
        if response.status_code == 200:
            data = response.json()['data']
            df = pd.DataFrame(data)[['id','pet_category_id' ,'pet_name', 'breed_id', 'gender', 'age_id', 'color_count']]

            # Get breed and age mappings
            mappings = get_information_id()
            if mappings:
                # Replace breed_id with breed name
                category_dict = dict(zip(mappings['jenis']['id'], mappings['jenis']['name']))
                df['pet_category_id'] = df['pet_category_id'].map(category_dict)

                breed_dict = dict(zip(mappings['breeds']['id'], mappings['breeds']['name']))
                df['breed'] = df['breed_id'].map(breed_dict)

                # Replace age_id with age category
                age_dict = dict(zip(mappings['ages']['id'], mappings['ages']['category']))
                df['age'] = df['age_id'].map(age_dict)

                # Drop the original ID columns
                df = df.drop(['breed_id', 'age_id'], axis=1)
                df = df[['id', 'pet_name', 'pet_category_id', 'breed', 'gender', 'age', 'color_count']]
                df.columns = ['id', 'nama', 'jenis', 'breed', 'gender', 'usia', 'warna']
                return df
        raise Exception("Failed to fetch data from API or process mappings")
    except Exception as e:
        app.logger.error(f"Error fetching data from API: {str(e)}")
        raise

def initialize_ml_components():
    """Initialize ML components with proper error handling"""
    global df, encoder, feature_vectors, breed_dict
    
    try:
        # Get data from API instead of direct database query
        df = get_data_from_api()
        
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
        return rekomendasi[['id', 'similarity_score']]
    except Exception as e:
        app.logger.error(f"Error in recommendation: {str(e)}")
        raise

# ============================================================================ 
# FUNGSI DATABASE
# ============================================================================

# def save_recommendation_to_db(recommendations):
#     """
#     Menyimpan hasil rekomendasi ke database dengan proper error handling
#     """
#     connection = None
#     try:
#         connection = get_db_connection()
#         with connection.cursor() as cursor:
#             # Query untuk insert data
#             query = """
#             INSERT INTO result
#             (ID, `Skor kemiripan`)
#             VALUES (%s, %s)
#             """
            
#             # Insert setiap rekomendasi
#             for rec in recommendations:
#                 values = (rec['id'], rec['similarity_score'])
#                 cursor.execute(query, values)

#             connection.commit()
#             return True
            
#     except Exception as e:
#         app.logger.error(f"Error saving to database: {str(e)}")
#         if connection:
#             connection.rollback()
#         return False

# ============================================================================ 
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """API root endpoint"""
    return jsonify({
        "status": "ok",
        "message": "Pet Recommendation API is running",
        "endpoints": {
            "health": "/health",
            "recommend": "/api/recommend",
            "get_breeds": "/get_breeds"
        }
    })


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

        hasil_rekomendasi = recommend_by_preferences(user_input, top_n=4)
        recommendations = hasil_rekomendasi.to_dict(orient='records')
        
        # # Simpan ke database
        # if not save_recommendation_to_db(recommendations):
        #     app.logger.warning("Failed to save recommendations to database")
            
        return jsonify(recommendations)

    except Exception as e:
        app.logger.error(f"Error in api_recommend route: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ============================================================================ 
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Get port from environment with fallback
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
