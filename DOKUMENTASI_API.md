# 📚 Dokumentasi REST API - Jadwal SMAN 1 Margaasih

Dokumentasi resmi penggunaan REST API untuk sistem Jadwal Pelajaran dan Data Guru SMAN 1 Margaasih berbasis **FastAPI**.

---

## 📌 Daftar Isi
1. [Tentang API](#-tentang-api)
2. [Base URL & Endpoint Dokumentasi](#-base-url--endpoint-dokumentasi)
3. [Panduan Integrasi Reverse Proxy (Nginx)](#-panduan-integrasi-reverse-proxy-nginx)
4. [Panduan Menjalankan Server API](#-panduan-menjalankan-server-api)
5. [Struktur Data](#-struktur-data)
6. [Daftar Endpoint](#-daftar-endpoint)
   - [A. Modul Guru](#a-modul-guru)
     - [`GET /api/guru`](#1-get-apiguru)
     - [`GET /api/guru/{kode_guru}`](#2-get-apigurukode_guru)
   - [B. Modul Jadwal](#b-modul-jadwal)
     - [`GET /api/jadwal`](#3-get-apijadwal)
     - [`GET /api/jadwal/kelas/{kelas}`](#4-get-apijadwalkelaskelas)
     - [`GET /api/jadwal/hari/{hari}`](#5-get-apijadwalharihari)
     - [`GET /api/jadwal/guru/{nama_guru}`](#6-get-apijadwalgurunama_guru)
7. [Kode Status HTTP](#-kode-status-http)
8. [Contoh Integrasi Klien](#-contoh-integrasi-klien)
   - [cURL](#curl)
   - [JavaScript (Fetch API)](#javascript-fetch-api)
   - [Python (Requests)](#python-requests)
   - [PHP](#php-curl)
9. [Tips & Praktik Terbaik](#-tips--praktik-terbaik)

---

## 📖 Tentang API

API ini menyediakan akses programmatic ke data guru dan jadwal pelajaran SMAN 1 Margaasih yang bersumber dari `database_jadwal.json`. Dibangun menggunakan framework modern **FastAPI**, API ini cepat, ringan, terverifikasi otomatis, dan menyediakan dokumentasi interaktif bawaan (Swagger UI dan ReDoc).

---

## 🌐 Base URL & Endpoint Dokumentasi

### 1. Base URL

| Lingkungan (Environment) | URL Endpoint | Catatan |
| :--- | :--- | :--- |
| **Produksi (HTTPS - Domain Resmi)** | `https://jadwal.sman1margaasih.sch.id` | Direkomendasikan (via Nginx Reverse Proxy) |
| **Produksi (Akses Port Langsung)** | `http://jadwal.sman1margaasih.sch.id:8000` | Port container API langsung |
| **Lokal (Development)** | `http://127.0.0.1:8000` | Pengujian lokal pada komputer pengembang |

---

### 2. Dokumentasi Interaktif

Anda dapat langsung mencoba semua endpoint secara visual melalui browser:

- **Swagger UI (Uji coba interaktif langsung):**  
  👉 [`https://jadwal.sman1margaasih.sch.id/docs`](https://jadwal.sman1margaasih.sch.id/docs)  
  *(Lokal: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs))*

- **ReDoc (Tampilan dokumentasi teknis & skema):**  
  👉 [`https://jadwal.sman1margaasih.sch.id/redoc`](https://jadwal.sman1margaasih.sch.id/redoc)  
  *(Lokal: [`http://127.0.0.1:8000/redoc`](http://127.0.0.1:8000/redoc))*

- **OpenAPI Schema (Spesifikasi JSON baku):**  
  👉 [`https://jadwal.sman1margaasih.sch.id/openapi.json`](https://jadwal.sman1margaasih.sch.id/openapi.json)

---

## ⚙️ Panduan Integrasi Reverse Proxy (Nginx)

Karena web UI Streamlit berjalan di port **7025** dan REST API FastAPI berjalan di port **8000**, konfigurasi Nginx berikut memungkinkan keduanya diakses mulus di bawah satu domain `https://jadwal.sman1margaasih.sch.id/` tanpa perlu membuka port tambahan di firewall publik:

```nginx
server {
    server_name jadwal.sman1margaasih.sch.id;

    # -----------------------------------------------------------
    # 1. Routing REST API & Dokumentasi FastAPI (Port 8000)
    # -----------------------------------------------------------
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # -----------------------------------------------------------
    # 2. Routing Aplikasi Utama Streamlit (Port 7025)
    # -----------------------------------------------------------
    location / {
        proxy_pass http://127.0.0.1:7025/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Mendukung WebSocket Streamlit
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    # Konfigurasi SSL managed by Certbot / Let's Encrypt
    listen 443 ssl; 
    # ssl_certificate ...
    # ssl_certificate_key ...
}
```

---

## 🚀 Panduan Menjalankan Server API

### Opsi 1: Menjalankan dengan Docker Compose (VPS / Server Produksi)

Layanan API telah terdaftar pada file `docker-compose.yml` dengan nama `tugasku_api`:

```bash
# Menjalankan container API di latar belakang (background)
docker compose up -d tugasku_api

# Memeriksa log aktivitas API
docker compose logs -f tugasku_api

# Mematikan container API
docker compose stop tugasku_api

# Restart container API jika ada perubahan konfigurasi
docker compose restart tugasku_api
```

### Opsi 2: Menjalankan Langsung dengan Python (Lokal / Development)

Pastikan virtual environment telah aktif:

```powershell
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Windows Command Prompt (cmd):
.\venv\Scripts\activate.bat
```

Jalankan server Uvicorn:
```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```
> Server akan otomatis memuat ulang (*hot-reload*) ketika ada perubahan kode file `api.py`.

---

## 🧱 Struktur Data

### 1. Objek Guru
| Field | Tipe Data | Deskripsi |
| :--- | :--- | :--- |
| `nama` | `string` | Nama lengkap guru beserta gelar akademik |
| `mapel` | `string` | Mata pelajaran yang diampu oleh guru tersebut |

### 2. Objek Jadwal
| Field | Tipe Data | Deskripsi |
| :--- | :--- | :--- |
| `jam_ke_clean` | `integer` | Nomor jam pelajaran (misal: `1`, `2` ... `10`). Nilai `0` untuk Upacara dan `99` untuk Istirahat |
| `hari` | `string` | Nama hari dalam huruf kapital (`SENIN`, `SELASA`, `RABU`, `KAMIS`, `JUMAT`) |
| `waktu` | `string` | Rentang waktu pelajaran (contoh: `"07.10 - 07.50"`) |
| `kelas` | `string` | Nama rombel / kelas (contoh: `"X-1"`, `"XI-4"`, `"XII-12"`) |
| `list_kode_guru` | `array[string]` | Daftar kode guru pengajar atau label kegiatan (contoh: `["19"]`, `["UPACARA", "BENDERA"]`, `["ISTIRAHAT", "PERTAMA"]`) |

---

## 📡 Daftar Endpoint

### A. Modul Guru

---

#### 1. `GET /api/guru`
Mendapatkan seluruh daftar guru beserta kode uniknya.

- **Method:** `GET`
- **URL:** `https://jadwal.sman1margaasih.sch.id/api/guru`
- **Headers:** `Accept: application/json`
- **Query Parameter:** *Tidak ada*

**Contoh Request (cURL):**
```bash
curl -X GET "https://jadwal.sman1margaasih.sch.id/api/guru" \
     -H "Accept: application/json"
```

**Contoh Response `200 OK`:**
```json
{
  "1": {
    "nama": "Toteng Suhara, S.Pd., M.M.Pd.",
    "mapel": "Kep.Sekolah"
  },
  "32A": {
    "nama": "Lukman Firmansyah, S.Kom",
    "mapel": "Informatika"
  },
  "32B": {
    "nama": "Lukman Firmansyah, S.Kom",
    "mapel": "PKWU"
  },
  "55A": {
    "nama": "Ida Farida, S.Pd.",
    "mapel": "Biologi"
  }
}
```

---

#### 2. `GET /api/guru/{kode_guru}`
Mendapatkan informasi detail guru spesifik berdasarkan kode guru.

- **Method:** `GET`
- **URL:** `https://jadwal.sman1margaasih.sch.id/api/guru/{kode_guru}`
- **Path Parameter:**
  - `kode_guru` *(wajib, string)*: Kode guru (contoh: `1`, `32A`, `55A`).

**Contoh Request (cURL):**
```bash
curl -X GET "https://jadwal.sman1margaasih.sch.id/api/guru/32A" \
     -H "Accept: application/json"
```

**Contoh Response `200 OK`:**
```json
{
  "nama": "Lukman Firmansyah, S.Kom",
  "mapel": "Informatika"
}
```

**Contoh Response `404 Not Found`:**
```json
{
  "detail": "Guru tidak ditemukan"
}
```

---

### B. Modul Jadwal

---

#### 3. `GET /api/jadwal`
Mendapatkan seluruh data jadwal pelajaran sekolah. Mendukung filter opsional berdasarkan nama kelas melalui query parameter.

- **Method:** `GET`
- **URL:** `https://jadwal.sman1margaasih.sch.id/api/jadwal`
- **Query Parameter:**
  - `kelas` *(opsional, string)*: Filter hanya untuk kelas tertentu (contoh: `?kelas=X-1`).

**Contoh Request - Semua Jadwal:**
```bash
curl -X GET "https://jadwal.sman1margaasih.sch.id/api/jadwal" \
     -H "Accept: application/json"
```

**Contoh Request - Filter Kelas X-1:**
```bash
curl -X GET "https://jadwal.sman1margaasih.sch.id/api/jadwal?kelas=X-1" \
     -H "Accept: application/json"
```

**Contoh Response `200 OK`:**
```json
[
  {
    "jam_ke_clean": 0,
    "hari": "SENIN",
    "waktu": "06.30 - 07.10",
    "kelas": "X-1",
    "list_kode_guru": ["UPACARA", "BENDERA"]
  },
  {
    "jam_ke_clean": 1,
    "hari": "SENIN",
    "waktu": "07.10 - 07.50",
    "kelas": "X-1",
    "list_kode_guru": ["19"]
  },
  {
    "jam_ke_clean": 2,
    "hari": "SENIN",
    "waktu": "07.50 - 08.30",
    "kelas": "X-1",
    "list_kode_guru": ["19"]
  }
]
```

---

#### 4. `GET /api/jadwal/kelas/{kelas}`
Mendapatkan seluruh jadwal pelajaran khusus untuk kelas tertentu.

- **Method:** `GET`
- **URL:** `https://jadwal.sman1margaasih.sch.id/api/jadwal/kelas/{kelas}`
- **Path Parameter:**
  - `kelas` *(wajib, string)*: Nama rombel / kelas (contoh: `X-1`, `XI-2`, `XII-12`).

**Contoh Request (cURL):**
```bash
curl -X GET "https://jadwal.sman1margaasih.sch.id/api/jadwal/kelas/XI-2" \
     -H "Accept: application/json"
```

**Contoh Response `200 OK`:**
```json
[
  {
    "jam_ke_clean": 1,
    "hari": "SENIN",
    "waktu": "07.10 - 07.50",
    "kelas": "XI-2",
    "list_kode_guru": ["17"]
  },
  {
    "jam_ke_clean": 2,
    "hari": "SENIN",
    "waktu": "07.50 - 08.30",
    "kelas": "XI-2",
    "list_kode_guru": ["17"]
  }
]
```

**Contoh Response `404 Not Found`:**
```json
{
  "detail": "Jadwal untuk kelas XI-99 tidak ditemukan"
}
```

---

#### 5. `GET /api/jadwal/hari/{hari}`
Mendapatkan jadwal pelajaran untuk semua kelas pada hari tertentu. Pencarian fleksibel (*case-insensitive*).

- **Method:** `GET`
- **URL:** `https://jadwal.sman1margaasih.sch.id/api/jadwal/hari/{hari}`
- **Path Parameter:**
  - `hari` *(wajib, string)*: Nama hari (contoh: `senin`, `SELASA`, `rabu`, `kamis`, `jumat`).

**Contoh Request (cURL):**
```bash
curl -X GET "https://jadwal.sman1margaasih.sch.id/api/jadwal/hari/senin" \
     -H "Accept: application/json"
```

**Contoh Response `200 OK`:**
```json
[
  {
    "jam_ke_clean": 1,
    "hari": "SENIN",
    "waktu": "07.10 - 07.50",
    "kelas": "X-1",
    "list_kode_guru": ["19"]
  },
  {
    "jam_ke_clean": 1,
    "hari": "SENIN",
    "waktu": "07.10 - 07.50",
    "kelas": "X-2",
    "list_kode_guru": ["18"]
  }
]
```

**Contoh Response `404 Not Found`:**
```json
{
  "detail": "Jadwal untuk hari MINGGU tidak ditemukan"
}
```

---

#### 6. `GET /api/jadwal/guru/{nama_guru}`
Mendapatkan daftar jadwal mengajar seorang guru berdasarkan nama.  
Pencarian bersifat parsial (*substring*) dan *case-insensitive*, sehingga cukup memasukkan nama depan, tengah, atau panggilan guru.

- **Method:** `GET`
- **URL:** `https://jadwal.sman1margaasih.sch.id/api/jadwal/guru/{nama_guru}`
- **Path Parameter:**
  - `nama_guru` *(wajib, string)*: Kata kunci nama guru (contoh: `Lukman`, `Farida`, `Toteng`).

**Contoh Request (cURL):**
```bash
curl -X GET "https://jadwal.sman1margaasih.sch.id/api/jadwal/guru/Lukman" \
     -H "Accept: application/json"
```

**Contoh Response `200 OK`:**
```json
{
  "guru_terkait": [
    "Lukman Firmansyah, S.Kom"
  ],
  "jadwal": [
    {
      "jam_ke_clean": 1,
      "hari": "SENIN",
      "waktu": "07.10 - 07.50",
      "kelas": "X-7",
      "list_kode_guru": ["32B"]
    },
    {
      "jam_ke_clean": 3,
      "hari": "SENIN",
      "waktu": "08.30 - 09.10",
      "kelas": "X-4",
      "list_kode_guru": ["32A"]
    }
  ]
}
```

**Contoh Response `404 Not Found` (Nama tidak ditemukan):**
```json
{
  "detail": "Tidak ditemukan guru dengan nama yang mengandung 'Budianto'"
}
```

**Contoh Response `404 Not Found` (Guru ada tapi tidak memiliki jam pelajaran):**
```json
{
  "detail": "Guru ditemukan, tapi tidak ada jadwal mengajar"
}
```

---

## 🚦 Kode Status HTTP

API ini menggunakan kode status HTTP standar:

| Status Code | Label | Penjelasan |
| :---: | :--- | :--- |
| `200` | **OK** | Permintaan berhasil diproses dan data dikembalikan. |
| `404` | **Not Found** | Data guru, jadwal kelas, atau jadwal hari yang dicari tidak ditemukan. |
| `422` | **Unprocessable Entity** | Parameter request tidak memenuhi format validasi FastAPI. |
| `500` | **Internal Server Error** | Terjadi kendala internal pada server saat mengakses database. |

---

## 💻 Contoh Integrasi Klien

### cURL

```bash
# 1. Ambil semua data guru
curl -s "https://jadwal.sman1margaasih.sch.id/api/guru"

# 2. Ambil detail guru kode 32A
curl -s "https://jadwal.sman1margaasih.sch.id/api/guru/32A"

# 3. Ambil jadwal kelas X-1
curl -s "https://jadwal.sman1margaasih.sch.id/api/jadwal/kelas/X-1"

# 4. Cari jadwal mengajar guru dengan nama Lukman
curl -s "https://jadwal.sman1margaasih.sch.id/api/jadwal/guru/Lukman"
```

---

### JavaScript (Fetch API)

```javascript
const BASE_URL = "https://jadwal.sman1margaasih.sch.id";

// 1. Fungsi mengambil jadwal per kelas
async function getJadwalKelas(kelas) {
  try {
    const res = await fetch(`${BASE_URL}/api/jadwal/kelas/${encodeURIComponent(kelas)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    console.log(`Jadwal Kelas ${kelas}:`, data);
    return data;
  } catch (err) {
    console.error("Gagal mengambil jadwal kelas:", err);
  }
}

// 2. Fungsi mencari jadwal per guru
async function getJadwalGuru(namaGuru) {
  try {
    const res = await fetch(`${BASE_URL}/api/jadwal/guru/${encodeURIComponent(namaGuru)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    console.log("Jadwal Guru:", data);
    return data;
  } catch (err) {
    console.error("Gagal mengambil jadwal guru:", err);
  }
}

// Pemanggilan contoh:
getJadwalKelas("X-1");
getJadwalGuru("Lukman");
```

---

### Python (Requests)

```python
import requests

BASE_URL = "https://jadwal.sman1margaasih.sch.id"

def get_daftar_guru():
    response = requests.get(f"{BASE_URL}/api/guru")
    if response.status_code == 200:
        return response.json()
    print("Error:", response.json())
    return None

def cari_jadwal_guru(nama: str):
    response = requests.get(f"{BASE_URL}/api/jadwal/guru/{nama}")
    if response.status_code == 200:
        return response.json()
    print("Error:", response.json())
    return None

if __name__ == "__main__":
    guru_dict = get_daftar_guru()
    print(f"Total guru terdata: {len(guru_dict)}")

    hasil = cari_jadwal_guru("Lukman")
    if hasil:
        print("Guru:", hasil["guru_terkait"])
        print(f"Total sesi mengajar: {len(hasil['jadwal'])}")
```

---

### PHP (cURL)

```php
<?php
$baseUrl = "https://jadwal.sman1margaasih.sch.id";

function getJadwalKelas($kelas) {
    global $baseUrl;
    $url = $baseUrl . "/api/jadwal/kelas/" . urlencode($kelas);
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Accept: application/json']);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode === 200) {
        return json_decode($response, true);
    }
    return null;
}

// Pengujian
$jadwal = getJadwalKelas("X-1");
print_r($jadwal);
?>
```

---

## 💡 Tips & Praktik Terbaik

1. **Sinkronisasi Data Real-Time:**  
   API membaca berkas `database_jadwal.json` secara dinamis. Apabila admin memperbarui atau mengunggah data jadwal baru melalui antarmuka web Streamlit, endpoint API akan langsung menyajikan data terbaru seketika tanpa memerlukan restart container.

2. **Gunakan URL Encoding:**  
   Bila nilai parameter URL mengandung spasi atau karakter khusus (misalnya nama guru: `Toteng Suhara`), pastikan klien melakukan URL encoding (`Toteng%20Suhara`).

3. **CORS & Konsumsi Lintas Platform:**  
   FastAPI siap diintegrasikan untuk aplikasi Web Frontend (React, Vue, Angular, Svelte), Aplikasi Mobile (Flutter, React Native, Kotlin), maupun Bot messaging (WhatsApp Bot / Telegram Bot) sekolah.
