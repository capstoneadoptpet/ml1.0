# Recommendation System Hewan

Aplikasi ini adalah sistem rekomendasi hewan peliharaan berbasis Flask yang memberikan rekomendasi hewan berdasarkan preferensi pengguna menggunakan content-based filtering dan cosine similarity.

## Fitur

- Rekomendasi hewan peliharaan berdasarkan input pengguna (jenis, breed, gender, usia, warna).
- API endpoint untuk integrasi dengan aplikasi lain.
- Penyimpanan hasil rekomendasi ke database.
- AJAX endpoint untuk mendapatkan daftar breed berdasarkan jenis hewan.

## Prasyarat

- Python 3.8+
- MySQL server (atau akses ke database yang sudah disediakan)
- Paket Python: lihat `requirements.txt`

## Instalasi

1. **Clone repository**

   ```sh
   git clone <repo-url>
   cd "Recommendation System hewan"
   ```

2. **Install dependencies**

   ```sh
   pip install -r requirements.txt
   ```

3. **Konfigurasi Database**

   Pastikan file [app.py](app.py) sudah berisi konfigurasi database yang benar:

   ```python
   config = {
       'host': '43.156.249.217',
       'user': 'root',
       'password': '473N8ZJU25aGsr6K10DWBhCzFo9fHOMA',
       'database': 'ml',
       'port': 30201,
   }
   ```

   > **Catatan:** Ganti konfigurasi jika menggunakan database sendiri.

4. **Jalankan aplikasi**
   ```sh
   python app.py
   ```
   Aplikasi akan berjalan di `http://localhost:5000` (atau port lain jika diubah).

## Cara Penggunaan

### 1. Melalui Web Interface

- Buka browser ke `http://localhost:5000`
- Isi form preferensi hewan:
  - Jenis (misal: kucing, anjing)
  - Breed (ras)
  - Gender (jantan/betina)
  - Usia (muda/dewasa/tua)
  - Warna (jumlah warna, numerik)
- Klik submit untuk mendapatkan rekomendasi hewan terbaik.
- Hasil rekomendasi akan ditampilkan di halaman dan otomatis disimpan ke database.

### 2. Melalui API

#### a. Mendapatkan rekomendasi (POST)

- Endpoint: `POST /api/recommend`
- Content-Type: `application/json`
- Body:
  ```json
  {
    "jenis": "kucing",
    "breed": "anggora",
    "gender": "jantan",
    "usia": "muda",
    "warna": 2
  }
  ```
- Response:
  ```json
  [
    {"id": 12, "similarity_score": 0.98},
    {"id": 7, "similarity_score": 0.95},
    ...
  ]
  ```

#### b. Mendapatkan daftar breed berdasarkan jenis (GET)

- Endpoint: `GET /get_breeds?jenis=kucing`
- Response:
  ```json
  ["anggora", "persia", "domestik"]
  ```

### 3. Penyimpanan Hasil

Setiap hasil rekomendasi yang diberikan akan otomatis disimpan ke tabel `result` pada database MySQL dengan kolom `ID` dan `Skor kemiripan`.

## Struktur Folder

- `app.py` : Main Flask app
- `templates/index.html` : Template halaman utama (form input & hasil)
- `requirements.txt` : Daftar dependensi Python

## Troubleshooting

- Jika gagal koneksi database, pastikan konfigurasi sudah benar dan database dapat diakses.
- Jika API eksternal tidak bisa diakses, cek koneksi internet/server API.

## Author

Bagas Rizky Ramadhan

---

Lisensi: MIT
