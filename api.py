from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List, Dict
import json
import os

app = FastAPI(
    title="API Jadwal Sekolah",
    description="API untuk mendapatkan data Guru dan Jadwal Pelajaran.",
    version="1.0.0",
    docs_url="/docs"
)

DB_PATH = "database_jadwal.json"

def get_db():
    if not os.path.exists(DB_PATH):
        return {"guru": {}, "jadwal": []}
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"guru": {}, "jadwal": []}

@app.get("/api/guru", tags=["Guru"])
def get_all_guru():
    """Mendapatkan seluruh daftar guru beserta kodenya."""
    db = get_db()
    return db.get("guru", {})

@app.get("/api/guru/{kode_guru}", tags=["Guru"])
def get_guru_by_kode(kode_guru: str):
    """Mendapatkan detail guru spesifik berdasarkan kode guru."""
    db = get_db()
    guru = db.get("guru", {}).get(kode_guru)
    if not guru:
        raise HTTPException(status_code=404, detail="Guru tidak ditemukan")
    return guru

@app.get("/api/jadwal", tags=["Jadwal"])
def get_semua_jadwal(kelas: Optional[str] = Query(None, description="Filter opsional berdasarkan kelas")):
    """Mendapatkan seluruh jadwal. Bisa difilter dengan query string `?kelas=X-1`."""
    db = get_db()
    jadwal = db.get("jadwal", [])
    if kelas:
        jadwal = [j for j in jadwal if j.get("kelas") == kelas]
    return jadwal

@app.get("/api/jadwal/kelas/{kelas}", tags=["Jadwal"])
def get_jadwal_by_kelas(kelas: str):
    """Mendapatkan jadwal spesifik untuk suatu kelas."""
    db = get_db()
    jadwal = [j for j in db.get("jadwal", []) if j.get("kelas") == kelas]
    if not jadwal:
        raise HTTPException(status_code=404, detail=f"Jadwal untuk kelas {kelas} tidak ditemukan")
    return jadwal

@app.get("/api/jadwal/hari/{hari}", tags=["Jadwal"])
def get_jadwal_by_hari(hari: str):
    """Mendapatkan jadwal spesifik untuk hari tertentu (cth: SENIN)."""
    db = get_db()
    hari_upper = hari.upper()
    jadwal = [j for j in db.get("jadwal", []) if str(j.get("hari", "")).upper() == hari_upper]
    if not jadwal:
        raise HTTPException(status_code=404, detail=f"Jadwal untuk hari {hari} tidak ditemukan")
    return jadwal

@app.get("/api/jadwal/guru/{nama_guru}", tags=["Jadwal"])
def get_jadwal_by_nama_guru(nama_guru: str):
    """Mendapatkan jadwal mengajar seorang guru berdasarkan nama (pencarian fleksibel/tanpa pembedaan huruf besar kecil)."""
    db = get_db()
    
    # 1. Cari kode-kode guru yang namanya mengandung `nama_guru`
    guru_dict = db.get("guru", {})
    target_codes = []
    
    nama_guru_lower = nama_guru.lower()
    for kode, info in guru_dict.items():
        if nama_guru_lower in info.get("nama", "").lower():
            target_codes.append(kode)
            
    if not target_codes:
         raise HTTPException(status_code=404, detail=f"Tidak ditemukan guru dengan nama yang mengandung '{nama_guru}'")

    # 2. Filter jadwal berdasarkan kode-kode dari guru yang cocok
    jadwal_list = db.get("jadwal", [])
    matched_jadwal = []
    target_codes_set = set(target_codes)
    
    for j in jadwal_list:
        kode_guru_di_kelas = set(j.get("list_kode_guru", []))
        if target_codes_set.intersection(kode_guru_di_kelas):
            matched_jadwal.append(j)
            
    if not matched_jadwal:
        raise HTTPException(status_code=404, detail=f"Guru ditemukan, tapi tidak ada jadwal mengajar")
        
    return {
        "guru_terkait": [guru_dict[code]["nama"] for code in target_codes],
        "jadwal": matched_jadwal
    }
