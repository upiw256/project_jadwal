import streamlit as st
import pdfplumber
import pandas as pd
import re

# ==========================================
# 1. FUNGSI IDENTIFIKASI HALAMAN
# ==========================================
def identifikasi_halaman(pdf):
    hal_guru = None
    hal_jadwal = []

    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        if text:
            text_upper = text.upper()
            
            # Ciri halaman guru: Ada kata "NAMA" dan "KODE" atau "DAFTAR GURU"
            # Kita hindari halaman yang ada kata "PUKUL" (biasanya jadwal)
            if (("NAMA" in text_upper and "KODE" in text_upper) or "DAFTAR GURU" in text_upper) and "PUKUL" not in text_upper:
                hal_guru = i
            
            # Ciri halaman jadwal: Ada kata kunci jadwal
            keywords_jadwal = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT", "WAKTU", "JAM KE"]
            matches = sum(1 for k in keywords_jadwal if k in text_upper)
            
            if matches >= 2:
                hal_jadwal.append(i)
    
    return hal_guru, hal_jadwal

# ==========================================
# 2. FUNGSI EKSTRAK DATA GURU
# ==========================================
def ekstrak_data_guru(pdf, nomor_halaman):
    data_guru = {} 
    if nomor_halaman is None: return {}

    page = pdf.pages[nomor_halaman]
    tables = page.extract_tables()

    for table in tables:
        for row in table:
            clean_row = [str(x).strip() for x in row if x]
            
            # Struktur tabel guru: 3 Kolom berulang (Kode, Nama, Mapel)
            # Index: 0, 3, 6
            indices_kode = [0, 3, 6] 
            for i in indices_kode:
                if i + 1 < len(clean_row): 
                    kode = clean_row[i]
                    nama = clean_row[i+1]
                    
                    if re.match(r'^\d+[A-Z]?$', kode) and len(nama) > 2:
                        nama = nama.replace('\n', ' ')
                        data_guru[kode] = nama
    return data_guru

# ==========================================
# 3. FUNGSI CARI JADWAL (POLA 13 BARIS)
# ==========================================
def cari_jadwal_guru(pdf, halaman_jadwal_list, kode_guru, geser_kolom=0):
    hasil_pencarian = []
    
    # Konfigurasi Pola
    LIST_HARI = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT"]
    BARIS_PER_HARI = 13  # Pola 13 baris per hari
    
    counter_baris_data = 0 

    # --- RUMUS PEMETAAN KELAS ---
    def tebak_kelas(idx, offset):
        posisi_relatif = idx + offset
        
        # Kelas 10 (X) -> Estimasi Kolom 3 s/d 14
        if 3 <= posisi_relatif <= 14:
            return f"X-{posisi_relatif - 2}"
        # Kelas 11 (XI) -> Estimasi Kolom 15 s/d 26
        elif 15 <= posisi_relatif <= 26:
            return f"XI-{posisi_relatif - 14}"
        # Kelas 12 (XII) -> Estimasi Kolom 27 s/d 38
        elif 27 <= posisi_relatif <= 38:
            return f"XII-{posisi_relatif - 26}"
        else:
            return "?"

    for i in halaman_jadwal_list:
        page = pdf.pages[i]
        
        # Ekstrak tabel dengan strategi garis ketat
        tables = page.extract_tables({
            "vertical_strategy": "lines", 
            "horizontal_strategy": "lines",
            "intersection_y_tolerance": 5,
        })
        
        for table in tables:
            for row in table:
                clean_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                
                # Filter baris valid
                if len(clean_row) < 5: continue
                
                cek_header = "".join(clean_row).upper()
                if "WAKTU" in cek_header or "JAM KE" in cek_header:
                    continue 

                # Hitung Hari (Matematika)
                index_hari = counter_baris_data // BARIS_PER_HARI
                
                if index_hari < len(LIST_HARI):
                    hari_sekarang = LIST_HARI[index_hari]
                else:
                    hari_sekarang = "Lainnya"

                waktu_ajar = clean_row[1] if len(clean_row) > 1 else "-"
                
                # Cari Kode Guru
                for col_idx, isi_sel in enumerate(clean_row):
                    if col_idx < 3: continue 
                    
                    if re.search(rf"\b{kode_guru}\b", isi_sel):
                        nama_kelas = tebak_kelas(col_idx, geser_kolom)
                        if nama_kelas != "?":
                            hasil_pencarian.append({
                                "Hari": hari_sekarang,
                                "Waktu": waktu_ajar,
                                "Kelas": nama_kelas,
                            })
                
                counter_baris_data += 1

    return hasil_pencarian

# ==========================================
# 4. TAMPILAN APLIKASI (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Jadwal Guru SMAN 1 Margaasih", layout="wide")

st.title("🏫 Aplikasi Jadwal Guru")
st.markdown("Upload PDF Jadwal. Sistem menggunakan pola **13 Baris per Hari**.")

# --- SIDEBAR PENGATURAN ---
st.sidebar.header("🔧 Pengaturan Manual")

st.sidebar.caption("Jika 'Halaman Jadwal' tidak ketemu:")
force_page = st.sidebar.checkbox("Set Halaman Jadwal Manual")
manual_page_num = st.sidebar.number_input("Nomor Halaman (Mulai 0)", min_value=0, value=0)

st.sidebar.markdown("---")

st.sidebar.caption("Jika nama kelas salah (misal X-1 jadi X-2):")
offset_val = st.sidebar.slider("Geser Posisi Kelas", min_value=-5, max_value=5, value=0)

# --- AREA UPLOAD ---
uploaded_file = st.file_uploader("Upload PDF Jadwal Disini", type="pdf")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        
        # 1. Identifikasi Halaman
        idx_guru, idx_jadwal = identifikasi_halaman(pdf)
        
        if force_page:
            idx_jadwal = [manual_page_num]
            st.info(f"Mode Manual: Menggunakan Halaman {manual_page_num + 1} sebagai Jadwal.")

        if idx_guru is None:
            idx_guru = 1 if len(pdf.pages) > 1 else 0

        # 2. Ekstrak Data Guru
        dict_guru = ekstrak_data_guru(pdf, idx_guru)
        
        if not dict_guru:
            st.error("❌ Gagal membaca Data Guru. Pastikan format tabel di PDF benar.")
        else:
            st.success(f"✅ Data Guru Terbaca: {len(dict_guru)} orang.")
            
            st.markdown("---")
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("Pilih Guru")
                list_nama = sorted(list(dict_guru.values()))
                pilihan_nama = st.selectbox("Nama Guru:", list_nama)
                
                kode_terpilih = [k for k, v in dict_guru.items() if v == pilihan_nama][0]
                st.info(f"Kode Guru: **{kode_terpilih}**")
                
                tombol_cek = st.button("🔍 Cek Jadwal", type="primary")

            with col2:
                if tombol_cek:
                    if not idx_jadwal:
                        st.error("❌ Halaman jadwal belum terdeteksi. Gunakan menu 'Pengaturan Manual' di sebelah kiri.")
                    else:
                        with st.spinner("Sedang memproses pola 13 baris..."):
                            hasil = cari_jadwal_guru(pdf, idx_jadwal, kode_terpilih, offset_val)
                        
                        if hasil:
                            st.subheader(f"Jadwal: {pilihan_nama}")
                            df = pd.DataFrame(hasil)
                            # --- PERBAIKAN DI SINI ---
                            # Menggunakan width="stretch" menggantikan use_container_width=True
                            st.dataframe(df, width="stretch") 
                        else:
                            st.warning("Jadwal tidak ditemukan. Pastikan 'Kalibrasi Posisi Kelas' di sidebar sudah pas.")