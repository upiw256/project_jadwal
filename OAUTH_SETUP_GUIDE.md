# OAuth 2.0 Setup Guide untuk jadwal.sman1margaasih.sch.id

## Masalah Saat Ini
Error: `redirect_uri_mismatch`
- Aplikasi mengirim: `redirect_uri=https://jadwal.sman1margaasih.sch.id/`
- Tapi URI ini belum terdaftar di Google Cloud Console

## Solusi: 5 Langkah di Google Cloud Console

### 1. Buka Google Cloud Console
- Buka https://console.cloud.google.com/
- Pilih project: **github-475715**
- Ke menu: **APIs & Services → Credentials**

### 2. Edit OAuth Client (atau buat baru jika belum ada)
- Cari Client ID: `592156539013-43j0juhmoh2casosq3f5vob4cc.apps.googleusercontent.com`
- Klik untuk edit
- **PENTING**: Pastikan type = **"Web application"** (bukan Desktop/Installed)

### 3. Tambah Authorized JavaScript origins
Di bagian "Authorized JavaScript origins", klik **"Add URI"** dan masukkan:
```
https://jadwal.sman1margaasih.sch.id
```

### 4. Tambah Authorized redirect URIs  
Di bagian "Authorized redirect URIs", klik **"Add URI"** dan masukkan (dengan trailing slash):
```
https://jadwal.sman1margaasih.sch.id/
```

### 5. Unduh JSON Baru dan Upload ke Server
- Klik "Download" (atau ikon download di bagian Client secrets)
- File yang diunduh akan berisi:
  ```json
  {
    "web": {
      "client_id": "...",
      "project_id": "github-475715",
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://oauth2.googleapis.com/token",
      "redirect_uris": ["https://jadwal.sman1margaasih.sch.id/"],
      ...
    }
  }
  ```
- **HARUS** ada key `"web"` (bukan `"installed"`), dan redirect_uris harus list berisi URL Anda

## Server Setup (setelah unduh JSON baru)

### 1. Upload file JSON ke server
Ganti `client_secret.json` lama dengan yang baru:
```bash
# copy file ke server (dari local Anda)
scp ~/Downloads/client_secret_*.json administrator@sman1margaasih:/home/administrator/project_jadwal/client_secret.json
```

### 2. Validasi file (di server)
```bash
cd ~/project_jadwal
python3 -c "
import json
with open('client_secret.json', 'r') as f:
    data = json.load(f)
    if 'web' in data:
        print('✓ Client type: web (BENAR)')
        print('✓ Client ID:', data['web'].get('client_id'))
        print('✓ Redirect URIs:', data['web'].get('redirect_uris'))
    else:
        print('✗ ERROR: tidak ada key web - harus download dari Web application client')
"
```

### 3. Restart container
```bash
cd ~/project_jadwal
sudo docker compose down
sudo docker compose up -d --build
```

### 4. Hapus token lama (agar OAuth flow dimulai dari awal)
```bash
sudo docker compose exec tugasku bash -lc "rm -f /app/token.pickle"
```

## Validasi di App
Setelah restart, buka app dan lihat di login panel:
- **Client type in JSON**: harus `web`
- **Client ID in JSON**: harus ada
- **Redirect URIs in client_secret.json**: harus ada `https://jadwal.sman1margaasih.sch.id/`
- **redirect_uri sent to Google**: harus `https://jadwal.sman1margaasih.sch.id/`

Jika semua ✓, klik **"Login dengan Google"** dan seharusnya berhasil!

## Troubleshooting
- Jika masih error `redirect_uri_mismatch`, tunggu 5-10 menit — Google Console membutuhkan waktu propagasi
- Verifikasi ulang di Google Cloud Console bahwa Anda sudah menyimpan (klik "Save")
- Pastikan Anda edit di client yang benar (Web application, bukan Desktop)
