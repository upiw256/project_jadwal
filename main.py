import streamlit as st
import pdfplumber
import pandas as pd
import re
import json
import os

# Nama file database penyimpanan sementara
DB_FILE = "database_jadwal.json"

# ==========================================
# 1. FUNGSI UTILITAS (SIMPAN/BACA JSON)
# ==========================================
def simpan_database(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f)

def baca_database():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return None

def reset_database():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    st.rerun()

# ==========================================
# 2. FUNGSI EKSTRAKSI (PDF -> DATA MENTAH)
# ==========================================
def identifikasi_halaman(pdf):
    hal_guru = None
    hal_jadwal = []
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        text_upper = text.upper()
        
        # Ciri halaman guru
        if (("NAMA" in text_upper and "KODE" in text_upper) or "DAFTAR GURU" in text_upper) and "PUKUL" not in text_upper:
            hal_guru = i
        
        # Ciri halaman jadwal
        keywords = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT", "WAKTU", "JAM KE"]
        if sum(1 for k in keywords if k in text_upper) >= 2:
            hal_jadwal.append(i)
    return hal_guru, hal_jadwal

def ekstrak_semua_guru(pdf, nomor_halaman):
    data_guru = {}
    if nomor_halaman is None: return {}
    
    page = pdf.pages[nomor_halaman]
    tables = page.extract_tables()
    for table in tables:
        for row in table:
            clean_row = [str(x).strip() for x in row if x]
            # Pola 3 kolom: Index 0, 3, 6
            for i in [0, 3, 6]:
                if i + 1 < len(clean_row):
                    kode = clean_row[i]
                    nama = clean_row[i+1]
                    if re.match(r'^\d+[A-Z]?$', kode) and len(nama) > 2:
                        data_guru[kode] = nama.replace('\n', ' ')
    return data_guru

def ekstrak_seluruh_jadwal(pdf, halaman_jadwal_list):
    """
    Membaca SELURUH isi tabel jadwal dan menyimpannya ke list.
    Tidak memfilter guru tertentu, tapi mengambil semua sel.
    """
    master_jadwal = []
    
    # Konfigurasi
    LIST_HARI = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT"]
    BARIS_PER_HARI = 13
    counter_baris = 0

    # Rumus Kelas
    def tebak_kelas(idx):
        if 3 <= idx <= 14: return f"X-{idx - 2}"
        elif 15 <= idx <= 26: return f"XI-{idx - 14}"
        elif 27 <= idx <= 38: return f"XII-{idx - 26}"
        return "?"

    for i in halaman_jadwal_list:
        page = pdf.pages[i]
        tables = page.extract_tables({
            "vertical_strategy": "lines", 
            "horizontal_strategy": "lines",
            "intersection_y_tolerance": 5,
        })
        
        for table in tables:
            for row in table:
                clean_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                
                # Filter baris sampah/header
                if len(clean_row) < 5: continue
                cek_header = "".join(clean_row).upper()
                if "WAKTU" in cek_header or "JAM KE" in cek_header: continue

                # Tentukan Hari
                idx_hari = counter_baris // BARIS_PER_HARI
                hari = LIST_HARI[idx_hari] if idx_hari < len(LIST_HARI) else "Lainnya"
                
                # Tentukan Waktu
                waktu = clean_row[1] if len(clean_row) > 1 else "-"

                # Loop semua sel (Kolom Kelas)
                for col_idx, isi_sel in enumerate(clean_row):
                    if col_idx < 3: continue # Skip metadata
                    
                    # Jika sel ada isinya (Kode Guru)
                    if isi_sel and len(isi_sel) < 5: # Validasi kode guru biasanya pendek
                         # Bersihkan kode (kadang ada spasi nyelip)
                         kode_bersih = isi_sel.strip()
                         
                         kelas = tebak_kelas(col_idx)
                         if kelas != "?":
                             master_jadwal.append({
                                 "kode_guru": kode_bersih,
                                 "hari": hari,
                                 "waktu": waktu,
                                 "kelas": kelas
                             })
                
                counter_baris += 1
                
    return master_jadwal

# ==========================================
# 3. USER INTERFACE (STREAMLIT)
# ==========================================
st.set_page_config(page_title="TugasKu - Jadwal Sekolah", layout="wide")

# --- HEADER & TOMBOL RESET ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title("🏫 TugasKu: Jadwal Sekolah")
with col_head2:
    # Cek apakah database ada
    db_exist = os.path.exists(DB_FILE)
    if db_exist:
        if st.button("🔄 Reset / Upload Ulang", type="secondary"):
            reset_database()

st.divider()

# --- LOGIKA UTAMA ---

# KONDISI 1: DATA SUDAH ADA (TAMPILKAN SEARCH)
if db_exist:
    # Load data dari JSON (Sangat Cepat)
    database = baca_database()
    dict_guru = database['guru']
    list_jadwal = database['jadwal']
    
    st.success("📂 Data Jadwal Terload dari Database Lokal.")
    
    # UI Pencarian
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Pencarian Guru")
        # Dropdown Nama
        sorted_nama = sorted(list(dict_guru.values()))
        pilihan_nama = st.selectbox("Pilih Nama Guru:", sorted_nama)
        
        # Cari Kode
        kode_terpilih = [k for k, v in dict_guru.items() if v == pilihan_nama][0]
        st.info(f"Kode Guru: **{kode_terpilih}**")
    
    with col2:
        st.subheader(f"Jadwal: {pilihan_nama}")
        
        # Filter data jadwal menggunakan Pandas (Filtering DataFrame)
        df_master = pd.DataFrame(list_jadwal)
        
        # Cari yang kodenya cocok (Exact Match)
        df_hasil = df_master[df_master['kode_guru'] == kode_terpilih]
        
        if not df_hasil.empty:
            # Urutkan hari biar rapi
            hari_order = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT"]
            df_hasil['hari'] = pd.Categorical(df_hasil['hari'], categories=hari_order, ordered=True)
            df_hasil = df_hasil.sort_values(['hari', 'waktu'])
            
            # Tampilkan
            st.dataframe(
                df_hasil[['hari', 'waktu', 'kelas']], 
                width="stretch",
                hide_index=True
            )
        else:
            st.warning("Guru ini tidak ditemukan di grid jadwal (Mungkin Guru BK/Piket).")

# KONDISI 2: DATA BELUM ADA (TAMPILKAN UPLOAD)
else:
    st.info("👋 Halo! Belum ada data jadwal. Silakan upload PDF Jadwal KBM (Merged) untuk inisialisasi.")
    
    uploaded_file = st.file_uploader("Upload PDF Jadwal", type="pdf")
    
    if uploaded_file:
        progress_bar = st.progress(0, text="Menganalisis file PDF...")
        
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                # 1. Identifikasi
                idx_guru, idx_jadwal = identifikasi_halaman(pdf)
                
                # Fallback halaman guru
                if idx_guru is None: idx_guru = 1 if len(pdf.pages) > 1 else 0
                
                if not idx_jadwal:
                    st.error("Gagal mendeteksi halaman jadwal. Pastikan PDF benar.")
                else:
                    progress_bar.progress(30, text="Mengekstrak Data Guru...")
                    
                    # 2. Ekstrak Guru
                    guru_dict = ekstrak_semua_guru(pdf, idx_guru)
                    
                    progress_bar.progress(60, text="Mengekstrak Seluruh Grid Jadwal (Ini mungkin butuh 10-20 detik)...")
                    
                    # 3. Ekstrak Jadwal (ETL Proses Berat)
                    jadwal_list = ekstrak_seluruh_jadwal(pdf, idx_jadwal)
                    
                    # 4. Simpan ke JSON
                    full_data = {
                        "guru": guru_dict,
                        "jadwal": jadwal_list
                    }
                    simpan_database(full_data)
                    
                    progress_bar.progress(100, text="Selesai!")
                    st.success("✅ Database berhasil dibuat! Halaman akan dimuat ulang...")
                    
                    # Reload otomatis agar masuk ke KONDISI 1
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")