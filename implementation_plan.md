# Menambahkan API Data Jadwal dengan FastAPI

Permintaan Anda adalah untuk menggunakan `venv` dan menjadikan data di `database_jadwal.json` menjadi API lengkap dengan dokumentasi di rute `/api`.

Karena proyek ini saat ini menggunakan Streamlit (`main.py`), saya mengusulkan pembuatan file servis baru menggunakan framework **FastAPI**, yang sangat ideal untuk pembuatan API di Python karena:
1. Sangat cepat.
2. Otomatis membuat dokumentasi interaktif (Swagger UI) di endpoint `/docs`.
3. Mudah dipisahkan atau digabungkan penggunaannya jika di masa depan ingin dijalankan berdampingan.

## User Review Required
> [!IMPORTANT]
> Mengingat FastAPI adalah sistem _server_ tersendiri, API ini nantinya akan berjalan di _port_ yang berbeda dari Streamlit. Apakah Anda setuju untuk menjalankan secara terpisah (misalnya `uvicorn api:app --port 8000`), atau Anda memiliki preferensi spesifik tentang integrasi Streamlit dengan FastAPI?

## Proposed Changes

### 1. File Dependensi
#### [MODIFY] [requirements.txt](file:///d:/python/project_jadwal/requirements.txt)
- Menambahkan dependensi `fastapi` dan `uvicorn`. Instalasi akan dilakukan di dalam virtual environment (`venv`).

### 2. File Utama API
#### [NEW] [api.py](file:///d:/python/project_jadwal/api.py)
Pembuatan file ini untuk mendeklarasikan Endpoint REST API menggunakan FastAPI. Rute yang disediakan:
- `GET /api/guru` - Mendapatkan semua daftar guru.
- `GET /api/guru/{kode_guru}` - Mendapatkan detail guru spesifik.
- `GET /api/jadwal` - Mendapatkan seluruh jadwal atau difilter berdasarkan kueri (misal `?kelas=X-1`).
- `GET /api/jadwal/kelas/{kelas}` - Mendapatkan spesifik jadwal satu kelas.
- `GET /api/jadwal/hari/{hari}` - Mendapatkan jadwal berdasarkan hari.

## Open Questions

- Apakah diperlukan rute spesifik lainnya, misalnya jadwal spesifik seorang guru (berdasarkan namanya/kodenya)? 
- Streamlit saat ini menyimpan ke `database_jadwal.json`. Kalau Streamlit berjalan berbarengan, API ini akan dapat me-_load_ secara instan data hasil *upload* Streamlit tersebut karena mereka membaca file yang sama. Apakah alur (flow) ini sesuai dengan yang Anda maksud?

## Verification Plan

### Automated Tests
- Menjalankan secara lokal `venv/Scripts/python -m uvicorn api:app --reload`
- Mengecek status `200 OK` via HTTP atau Browser ketika mengunjungi endpoint `http://127.0.0.1:8000/api/...`
- Mengecek ketersediaan dokumentasi di `http://127.0.0.1:8000/docs`

### Manual Verification
- Pengguna bisa mengakses tautan web ke `/docs` Swagger API dan mencoba endpoint secara langsung.
