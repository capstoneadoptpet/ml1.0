import requests

url = "http://localhost:5000/api/recommend"

payload = {
    "jenis": "kelinci",
    "breed": "anggora",
    "gender": "jantan",
    "usia": "muda",
    "warna": 3
}

response = requests.post(url, json=payload)

print("Status:", response.status_code)
print("Hasil rekomendasi:")
for item in response.json():
    print(item)
