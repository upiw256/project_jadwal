from fastapi import FastAPI, HTTPException
import json
import os

app = FastAPI(title="API Jadwal TugasKu")
DB_FILE = "database_jadwal.json"

def muat_data():
    if not os.path.exists(DB_FILE):
        return None
    with open(DB_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return None

@app.get("/jadwal/kelas/{nama_kelas}")
def get_jadwal_per_hari(nama_kelas: str):
    data = muat_data()
    if not data:
        raise HTTPException(status_code=404, detail="Database tidak ditemukan")

    # Ambil kamus guru dan daftar jadwal dari database
    dict_guru = data.get('guru', {})
    jadwal_mentah = data.get('jadwal', [])

    # 1. Filter data hanya untuk kelas yang diminta (misal: X-1)
    jadwal_kelas = [j for j in jadwal_mentah if j['kelas'].upper() == nama_kelas.upper()]
    
    if not jadwal_kelas:
        raise HTTPException(status_code=404, detail=f"Jadwal kelas {nama_kelas} tidak ditemukan")

    # 2. Urutan hari kerja
    LIST_HARI = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT"]
    hasil_akhir = {}

    for hari in LIST_HARI:
        # Filter jadwal per hari dan urutkan berdasarkan jam
        items_hari = [j for j in jadwal_kelas if j['hari'].upper() == hari]
        items_hari.sort(key=lambda x: x['jam_ke_clean'])
        
        jadwal_hari_ini = []
        for item in items_hari:
            detail_kegiatan = []
            for kode in item.get('list_kode_guru', []):
                # PROSES LOOKUP: Cek apakah kode ada di daftar guru
                if kode in dict_guru:
                    g = dict_guru[kode]
                    detail_kegiatan.append({
                        "guru": g['nama'],   # Mengambil nama asli
                        "mapel": g['mapel']  # Mengambil mata pelajaran
                    })
                else:
                    # Jika kodenya teks (seperti "UPACARA", "ISTIRAHAT")
                    detail_kegiatan.append({
                        "guru": kode,
                        "mapel": "-"
                    })

            jadwal_hari_ini.append({
                "jam_ke": item['jam_ke_clean'],
                "waktu": item['waktu'],
                "kegiatan": detail_kegiatan
            })

        hasil_akhir[hari] = jadwal_hari_ini

    return {
        "kelas": nama_kelas.upper(),
        "data_per_hari": hasil_akhir
    }