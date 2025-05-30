import pymysql

# Tentukan konfigurasi koneksi ke database
host = '43.156.249.217'  # Ganti dengan host database Anda
user = 'root'  # Ganti dengan username Anda
password = '473N8ZJU25aGsr6K10DWBhCzFo9fHOMA'  # Ganti dengan password Anda
database = 'capstone2'  # Ganti dengan nama database Anda
port = 30201

try:
    # Membuat koneksi ke database
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port
    )
    
    # Jika koneksi berhasil
    print("Koneksi ke database berhasil!")

    # with connection.cursor() as cursor:
    #     # Menjalankan query untuk mengambil seluruh data dari tabel adopsi_pets
    #     query = "SELECT * FROM Dataset"
    #     cursor.execute(query)

    #     # Mendapatkan semua hasil
    #     results = cursor.fetchall()

    #     # Menampilkan hasil
    #     for row in results:
    #         print(row)


    # # Menutup koneksi setelah selesai
    # # connection.close()

except pymysql.MySQLError as e:
    print(f"Terjadi kesalahan saat menghubungkan ke database: {e}")

finally:
    if connection:
        connection.close()  # Pastikan koneksi ditutup setelah selesai
