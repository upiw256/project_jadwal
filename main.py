import streamlit as st
import pdfplumber
import pandas as pd
import re
import json
import os
import io
from fpdf import FPDF

# Nama file database penyimpanan sementara
DB_FILE = "database_jadwal.json"

# ==========================================
# 1. FUNGSI FORMATTING (MATRIX & STYLING)
# ==========================================
def buat_tabel_matriks(df_input):
    """Mengubah data list panjang menjadi tabel matriks (Waktu x Hari)."""
    # Pivot Data
    df_pivot = df_input.pivot_table(index='waktu', columns='hari', values='kelas', aggfunc='first')
    
    # Reindex agar urutan hari benar
    hari_order = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT"]
    df_pivot = df_pivot.reindex(columns=hari_order)
    
    # Sort Waktu & Reset Index
    df_pivot = df_pivot.sort_index()
    df_pivot = df_pivot.reset_index()
    df_pivot = df_pivot.fillna("-")
    
    return df_pivot

# ==========================================
# 2. FUNGSI DOWNLOAD (EXCEL & PDF CANTIK)
# ==========================================
def buat_excel(df, nama_guru):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Jadwal Mingguan')
        workbook = writer.book
        worksheet = writer.sheets['Jadwal Mingguan']
        
        # Style Definitions
        fmt_header = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'fg_color': '#4CAF50', 'font_color': 'white', 'border': 1})
        fmt_isi = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'fg_color': '#E8F5E9', 'font_color': '#1B5E20', 'border': 1})
        fmt_kosong = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_color': '#BDBDBD', 'border': 1})
        fmt_waktu = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#F5F5F5', 'border': 1})

        # Apply Header
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, fmt_header)
            width = 15 if col_num == 0 else 12
            worksheet.set_column(col_num, col_num, width)
        
        # Apply Body
        for row_num, row_data in enumerate(df.values):
            worksheet.write(row_num + 1, 0, row_data[0], fmt_waktu)
            for col_num, cell_value in enumerate(row_data[1:], start=1):
                if cell_value != "-":
                    worksheet.write(row_num + 1, col_num, cell_value, fmt_isi)
                else:
                    worksheet.write(row_num + 1, col_num, cell_value, fmt_kosong)
            
    return output.getvalue()

def buat_pdf(df, nama_guru):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 16)
            self.set_text_color(33, 33, 33)
            self.cell(0, 10, f'Jadwal Mengajar: {nama_guru}', ln=True, align='C')
            self.ln(5)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(128)
            self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    col_w_waktu = 40
    col_w_hari = 45
    col_height = 10
    headers = df.columns.tolist() 
    
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(200, 200, 200)
    
    pdf.cell(col_w_waktu, col_height, "JAM / WAKTU", border=1, align='C', fill=True)
    for h in headers[1:]:
        pdf.cell(col_w_hari, col_height, h, border=1, align='C', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", size=10)
    for index, row in df.iterrows():
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(col_w_waktu, col_height, str(row['waktu']), border=1, align='C')
        pdf.set_font("Arial", '', 10)
        for col_name in headers[1:]:
            isi = str(row[col_name])
            if isi != "-":
                pdf.set_fill_color(232, 245, 233)
                pdf.cell(col_w_hari, col_height, isi, border=1, align='C', fill=True)
            else:
                pdf.cell(col_w_hari, col_height, isi, border=1, align='C', fill=False)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 3. FUNGSI DATABASE & EKSTRAKSI (CORE)
# ==========================================
def simpan_database(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f)

def baca_database():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f: return json.load(f)
    return None

def reset_database():
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.rerun()

def identifikasi_halaman(pdf):
    hal_guru = None; hal_jadwal = []
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""; text_upper = text.upper()
        if (("NAMA" in text_upper and "KODE" in text_upper) or "DAFTAR GURU" in text_upper) and "PUKUL" not in text_upper:
            hal_guru = i
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
            for i in [0, 3, 6]:
                if i + 1 < len(clean_row):
                    kode = clean_row[i]; nama = clean_row[i+1]
                    if re.match(r'^\d+[A-Z]?$', kode) and len(nama) > 2:
                        data_guru[kode] = nama.replace('\n', ' ')
    return data_guru

def ekstrak_seluruh_jadwal(pdf, halaman_jadwal_list):
    master_jadwal = []; LIST_HARI = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT"]; current_hari_index = -1
    def tebak_kelas(idx):
        if 3 <= idx <= 14: return f"X-{idx - 2}"
        elif 15 <= idx <= 26: return f"XI-{idx - 14}"
        elif 27 <= idx <= 38: return f"XII-{idx - 26}"
        return "?"
    for i in halaman_jadwal_list:
        page = pdf.pages[i]
        tables = page.extract_tables({"vertical_strategy": "lines", "horizontal_strategy": "lines", "intersection_y_tolerance": 5})
        for table in tables:
            for row in table:
                clean_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                if len(clean_row) < 5: continue
                cek_header = "".join(clean_row).upper()
                if "WAKTU" in cek_header or "JAM KE" in cek_header: continue
                waktu = clean_row[1] if len(clean_row) > 1 else "-"
                if "06.3" in waktu or "06:3" in waktu: current_hari_index += 1
                hari = LIST_HARI[current_hari_index] if 0 <= current_hari_index < len(LIST_HARI) else "Lainnya"
                for col_idx, isi_sel in enumerate(clean_row):
                    if col_idx < 3: continue 
                    if isi_sel and len(isi_sel) < 5: 
                         kode_bersih = isi_sel.strip()
                         kelas = tebak_kelas(col_idx)
                         if kelas != "?": master_jadwal.append({"kode_guru": kode_bersih, "hari": hari, "waktu": waktu, "kelas": kelas})
    return master_jadwal

# ==========================================
# 4. USER INTERFACE (EXPANDER MODE)
# ==========================================
st.set_page_config(page_title="TugasKu - Jadwal Sekolah", layout="wide")

# CSS: Header tabel hijau & Full Width
st.markdown("""
<style>
    thead tr th {
        background-color: #4CAF50 !important;
        color: white !important;
        text-align: center !important;
    }
    .stDataFrame { width: 100% !important; }
</style>
""", unsafe_allow_html=True)

col_head1, col_head2 = st.columns([3, 1])
with col_head1: st.title("🏫 TugasKu: Jadwal Sekolah")
with col_head2:
    if os.path.exists(DB_FILE):
        if st.button("🔄 Reset / Upload Ulang", type="secondary"): reset_database()
st.divider()

if os.path.exists(DB_FILE):
    database = baca_database()
    dict_guru = database['guru']
    list_jadwal = database['jadwal']
    st.success("📂 Database Siap.")
    
    # --- BAGIAN 1: FILTER (DISEMBUNYIKAN DI EXPANDER) ---
    with st.expander("🔍 Klik untuk Cari Guru / Download File", expanded=True):
        col_filter1, col_filter2 = st.columns([2, 2])
        
        with col_filter1:
            st.markdown("### 1. Pilih Guru")
            sorted_nama = sorted(list(dict_guru.values()))
            pilihan_nama = st.selectbox("Ketik Nama Guru:", sorted_nama)
            kode_terpilih = [k for k, v in dict_guru.items() if v == pilihan_nama][0]
            st.info(f"Kode Guru: **{kode_terpilih}**")
            
        with col_filter2:
            st.markdown("### 2. Download Jadwal")
            # Generate Data for Download
            df_master = pd.DataFrame(list_jadwal)
            df_raw = df_master[df_master['kode_guru'] == kode_terpilih].copy()
            
            if not df_raw.empty:
                df_matriks = buat_tabel_matriks(df_raw)
                c1, c2 = st.columns(2)
                with c1:
                    file_excel = buat_excel(df_matriks, pilihan_nama)
                    st.download_button("📄 Download Excel", file_excel, f'Jadwal_{pilihan_nama}.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
                with c2:
                    try:
                        file_pdf = buat_pdf(df_matriks, pilihan_nama)
                        st.download_button("📑 Download PDF", file_pdf, f'Jadwal_{pilihan_nama}.pdf', 'application/pdf', use_container_width=True)
                    except: st.error("PDF Error")
            else:
                st.warning("Data kosong, tidak bisa download.")

    # --- BAGIAN 2: TAMPILAN TABEL (FULL WIDTH) ---
    st.subheader(f"📅 Jadwal Mengajar: {pilihan_nama}")
    
    if not df_raw.empty:
        df_display = buat_tabel_matriks(df_raw)
        
        # Styling Table
        def highlight_cells(val):
            return 'background-color: #d4edda; color: #155724; font-weight: bold' if val != "-" else 'color: #ced4da'

        styled_df = df_display.style.map(
            highlight_cells, 
            subset=["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT"]
        ).set_properties(**{'text-align': 'center'})

        st.dataframe(
            styled_df, 
            width=2000, # Memaksa lebar maksimal
            use_container_width=True, # Responsif
            hide_index=True,
            column_config={
                "waktu": st.column_config.TextColumn("🕒 Jam", width="small"),
                "SENIN": st.column_config.TextColumn("Senin", width="medium"),
                "SELASA": st.column_config.TextColumn("Selasa", width="medium"),
                "RABU": st.column_config.TextColumn("Rabu", width="medium"),
                "KAMIS": st.column_config.TextColumn("Kamis", width="medium"),
                "JUMAT": st.column_config.TextColumn("Jumat", width="medium"),
            }
        )
    else:
        st.warning("Guru ini tidak memiliki jadwal mengajar di tabel utama (Kemungkinan Guru BK atau Piket).")

else:
    st.info("👋 Belum ada data. Silakan upload PDF Jadwal (Merged).")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    if uploaded_file:
        progress_bar = st.progress(0, text="Analisis PDF...")
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                idx_guru, idx_jadwal = identifikasi_halaman(pdf)
                if idx_guru is None: idx_guru = 1 if len(pdf.pages) > 1 else 0
                if not idx_jadwal: st.error("Halaman jadwal tidak ditemukan.")
                else:
                    progress_bar.progress(30, text="Baca Data Guru...")
                    guru_dict = ekstrak_semua_guru(pdf, idx_guru)
                    progress_bar.progress(60, text="Baca Grid Jadwal...")
                    jadwal_list = ekstrak_seluruh_jadwal(pdf, idx_jadwal)
                    simpan_database({"guru": guru_dict, "jadwal": jadwal_list})
                    progress_bar.progress(100, text="Selesai!")
                    st.rerun()
        except Exception as e: st.error(f"Error: {e}")