# Quick Reference: Fix redirect_uri_mismatch

## Error Message Artinya
```
Error 400: redirect_uri_mismatch
redirect_uri=https://jadwal.sman1margaasih.sch.id/
```
= URI `https://jadwal.sman1margaasih.sch.id/` belum terdaftar di Google Cloud OAuth client.

## CHECKLIST: Apa yang harus Anda lakukan

### Langkah A: Di Google Cloud Console (UI web, bukan server)
- [ ] Buka https://console.cloud.google.com/
- [ ] Project: `github-475715`
- [ ] Menu: `APIs & Services → Credentials`
- [ ] Cari Client ID: `592156539013-43j0juhmoh2casosq3f5vob4cc...`
- [ ] Klik untuk edit
- [ ] Pastikan type: **Web application** (BUKAN Desktop/Installed)
- [ ] **Authorized JavaScript origins** → Add URI → `https://jadwal.sman1margaasih.sch.id`
- [ ] **Authorized redirect URIs** → Add URI → `https://jadwal.sman1margaasih.sch.id/` (WITH trailing slash!)
- [ ] Klik **SAVE**
- [ ] Download JSON (tombol download di "Client secrets")

### Langkah B: Di server (SSH)

#### 1. Backup dan upload client_secret.json baru
```bash
cd ~/project_jadwal
# Backup file lama
cp client_secret.json client_secret.json.backup

# Upload file baru (dari komputer Anda, jika perlu)
# scp ~/Downloads/client_secret_*.json administrator@sman1margaasih:~/project_jadwal/client_secret.json
```

#### 2. Validasi file
```bash
cd ~/project_jadwal
python3 validate_oauth.py
```
Output harus menunjukkan:
```
✓ Configuration looks good!
✓ Client type: web
✓ https://jadwal.sman1margaasih.sch.id/
```

#### 3. Stop dan restart container dengan JSON baru
```bash
cd ~/project_jadwal
sudo docker compose down
sudo docker compose up -d --build
```

#### 4. Hapus token lama agar login ulang dari awal
```bash
sudo docker compose exec tugasku bash -lc "rm -f /app/token.pickle"
```

#### 5. Verifikasi container running
```bash
sudo docker ps --filter "name=tugasku"
```

### Langkah C: Test di app
1. Buka https://jadwal.sman1margaasih.sch.id
2. Lihat login panel, verifikasi:
   - "Client type in JSON": web
   - "Redirect URIs in client_secret.json": https://jadwal.sman1margaasih.sch.id/
   - "redirect_uri sent to Google": https://jadwal.sman1margaasih.sch.id/
3. Klik "🔐 Login dengan Google"
4. Login dengan akun Google

## Jika Masih Error
- Tunggu 5-10 menit (Google Console perlu waktu propagasi)
- Verifikasi **SAVE** di Google Cloud Console (jangan lupa!)
- Cek tipe client: harus **"Web application"** (bukan Desktop)
- Pastikan trailing slash: `https://jadwal.sman1margaasih.sch.id/**/** (ada slash di akhir)

## Files Penting
- `client_secret.json` - File OAuth dari Google Cloud (harus type: web)
- `validate_oauth.py` - Script untuk validasi config (run: `python3 validate_oauth.py`)
- `OAUTH_SETUP_GUIDE.md` - Panduan lengkap dengan gambar/detail
