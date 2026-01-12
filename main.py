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
# 1. FUNGSI FORMATTING & STYLING (WARNA-WARNI)
# ==========================================
def buat_tabel_matriks(df_input, value_col):
    """Mengubah data list menjadi tabel matriks (Waktu x Hari)."""
    # Pivot Data
    df_pivot = df_input.pivot_table(index='waktu', columns='hari', values=value_col, aggfunc='first')
    
    # Reindex agar urutan hari benar
    hari_order = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT"]
    df_pivot = df_pivot.reindex(columns=hari_order)
    
    # Sort Waktu & Reset Index
    df_pivot = df_pivot.sort_index()
    df_pivot = df_pivot.reset_index()
    df_pivot = df_pivot.fillna("-")
    
    return df_pivot

# ==========================================
# 2. FUNGSI DOWNLOAD (EXCEL & PDF)
# ==========================================
def buat_excel(df_kelas, df_mapel, nama_guru, color_map):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_kelas.to_excel(writer, index=False, sheet_name='Jadwal')
        workbook = writer.book
        worksheet = writer.sheets['Jadwal']
        
        # Style Definitions
        fmt_header = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'fg_color': '#444444', 'font_color': 'white', 'border': 1})
        fmt_waktu = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#F5F5F5', 'border': 1})
        fmt_kosong = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_color': '#BDBDBD', 'border': 1})
        
        # Buat format dinamis berdasarkan warna mapel
        formats_mapel = {}
        for mapel, hex_color in color_map.items():
            formats_mapel[mapel] = workbook.add_format({
                'align': 'center', 'valign': 'vcenter', 
                'fg_color': hex_color, 'border': 1, 'bold': True
            })

        # Apply Header
        for col_num, value in enumerate(df_kelas.columns.values):
            worksheet.write(0, col_num, value, fmt_header)
            width = 15 if col_num == 0 else 10
            worksheet.set_column(col_num, col_num, width)
        
        # Apply Body
        # Kita butuh data mapel untuk menentukan warna
        # Konversi df_mapel ke dict untuk lookup cepat: mapel_dict[row_idx][col_name]
        
        for row_num, row_data in enumerate(df_kelas.values):
            # Tulis Waktu
            worksheet.write(row_num + 1, 0, row_data[0], fmt_waktu)
            
            # Tulis Hari
            for col_num, cell_value in enumerate(row_data[1:], start=1):
                col_name = df_kelas.columns[col_num] # Nama Hari
                
                # Ambil Mapel dari df_mapel untuk sel ini
                # Row di df_mapel sama urutannya dengan df_kelas karena index waktu sama
                mapel_val = df_mapel.iloc[row_num][col_name]
                
                if cell_value != "-" and mapel_val in formats_mapel:
                    worksheet.write(row_num + 1, col_num, cell_value, formats_mapel[mapel_val])
                else:
                    worksheet.write(row_num + 1, col_num, cell_value, fmt_kosong)
            
    return output.getvalue()

def buat_pdf(df_kelas, df_mapel, nama_guru, color_map_rgb):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 16)
            self.cell(0, 10, f'Jadwal: {nama_guru}', ln=True, align='C')
            self.ln(5)
    
    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    col_w_waktu = 35
    col_w_hari = 48
    col_h = 10
    headers = df_kelas.columns.tolist()
    
    # Header
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(col_w_waktu, col_h, "JAM", border=1, align='C', fill=True)
    for h in headers[1:]:
        pdf.cell(col_w_hari, col_h, h, border=1, align='C', fill=True)
    pdf.ln()
    
    # Body
    pdf.set_font("Arial", size=10)
    for i, row in df_kelas.iterrows():
        # Waktu
        pdf.set_font("Arial", 'B', 9)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(col_w_waktu, col_h, str(row['waktu']), border=1, align='C', fill=True)
        
        # Hari
        pdf.set_font("Arial", '', 10)
        for col_name in headers[1:]:
            isi = str(row[col_name])
            mapel = df_mapel.iloc[i][col_name]
            
            if isi != "-" and mapel in color_map_rgb:
                r, g, b = color_map_rgb[mapel]
                pdf.set_fill_color(r, g, b)
                pdf.cell(col_w_hari, col_h, isi, border=1, align='C', fill=True)
            else:
                pdf.cell(col_w_hari, col_h, isi, border=1, align='C', fill=False)
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 3. CORE LOGIC (EKSTRAKSI DATA)
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
            # Pola 3 kolom: Kode, Nama, Mapel (Index 0,1,2 | 3,4,5 | 6,7,8)
            for i in [0, 3, 6]:
                if i + 2 < len(clean_row): # Pastikan ada kolom Mapel (i+2)
                    kode = clean_row[i]
                    nama = clean_row[i+1]
                    mapel = clean_row[i+2] # Ambil Mapel
                    
                    if re.match(r'^\d+[A-Z]?$', kode) and len(nama) > 2:
                        # Simpan Object Lengkap
                        data_guru[kode] = {
                            'nama': nama.replace('\n', ' '),
                            'mapel': mapel.replace('\n', ' ')
                        }
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
                         if kelas != "?": 
                             master_jadwal.append({
                                 "kode_guru": kode_bersih, 
                                 "hari": hari, 
                                 "waktu": waktu, 
                                 "kelas": kelas
                             })
    return master_jadwal

# ==========================================
# 4. USER INTERFACE (ULTIMATE)
# ==========================================
st.set_page_config(page_title="TugasKu - Jadwal Sekolah", layout="wide")

# CSS Styling
st.markdown("""
<style>
    thead tr th { background-color: #444444 !important; color: white !important; text-align: center !important; }
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
    dict_guru = database['guru'] # Format: {kode: {'nama': ..., 'mapel': ...}}
    list_jadwal = database['jadwal']
    st.success("📂 Database Siap.")
    
    # 1. EXPANDER PENCARIAN
    with st.expander("🔍 Klik untuk Cari Guru / Download", expanded=True):
        col_filter1, col_filter2 = st.columns([2, 2])
        
        with col_filter1:
            st.markdown("### 1. Pilih Guru")
            # Ambil set nama unik
            unique_names = sorted(list(set([v['nama'] for v in dict_guru.values()])))
            pilihan_nama = st.selectbox("Ketik Nama Guru:", unique_names)
            
            # Cari SEMUA Kode milik guru tersebut (Contoh: 32A dan 32B)
            found_codes = [k for k, v in dict_guru.items() if v['nama'] == pilihan_nama]
            
            # Mapping Kode -> Mapel untuk guru ini
            mapel_info = {k: dict_guru[k]['mapel'] for k in found_codes}
            
            st.info(f"Kode Terdeteksi: {', '.join(found_codes)}")
            
            # Buat Legenda Warna
            st.markdown("**Keterangan Mapel:**")
            
            # Warna Palette (Hijau, Kuning, Biru, Merah)
            colors_hex = ['#C8E6C9', '#FFF9C4', '#BBDEFB', '#FFCDD2']
            colors_rgb = [(200, 230, 201), (255, 249, 196), (187, 222, 251), (255, 205, 210)]
            
            # Map setiap Mapel unik ke warna
            unique_mapels = sorted(list(set(mapel_info.values())))
            color_map = {m: colors_hex[i % len(colors_hex)] for i, m in enumerate(unique_mapels)}
            color_map_rgb = {m: colors_rgb[i % len(colors_rgb)] for i, m in enumerate(unique_mapels)}
            
            # Tampilkan Chips Warna
            cols_legenda = st.columns(len(unique_mapels))
            for i, m in enumerate(unique_mapels):
                c = color_map[m]
                cols_legenda[i].markdown(f"<div style='background-color:{c};padding:5px;border-radius:5px;text-align:center;border:1px solid #ccc'><b>{m}</b></div>", unsafe_allow_html=True)

        with col_filter2:
            st.markdown("### 2. Download Jadwal")
            df_master = pd.DataFrame(list_jadwal)
            # Filter jadwal berdasarkan LIST KODE (bukan cuma 1 kode)
            df_raw = df_master[df_master['kode_guru'].isin(found_codes)].copy()
            
            # Tambahkan kolom Mapel ke df_raw untuk pewarnaan
            df_raw['mapel'] = df_raw['kode_guru'].map(lambda x: mapel_info.get(x, '-'))
            
            if not df_raw.empty:
                # Kita butuh 2 matriks: 1 untuk Teks (Kelas), 1 untuk Metadata (Mapel/Warna)
                df_matriks_kelas = buat_tabel_matriks(df_raw, 'kelas')
                df_matriks_mapel = buat_tabel_matriks(df_raw, 'mapel')
                
                c1, c2 = st.columns(2)
                with c1:
                    file_excel = buat_excel(df_matriks_kelas, df_matriks_mapel, pilihan_nama, color_map)
                    st.download_button("📄 Excel", file_excel, f'Jadwal_{pilihan_nama}.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
                with c2:
                    try:
                        file_pdf = buat_pdf(df_matriks_kelas, df_matriks_mapel, pilihan_nama, color_map_rgb)
                        st.download_button("📑 PDF", file_pdf, f'Jadwal_{pilihan_nama}.pdf', 'application/pdf', use_container_width=True)
                    except Exception as e: st.error(f"PDF Error: {e}")
            else:
                st.warning("Data kosong.")

    # 2. TAMPILAN TABEL UTAMA
    st.subheader(f"📅 Jadwal Mengajar: {pilihan_nama}")
    
    if not df_raw.empty:
        df_display = buat_tabel_matriks(df_raw, 'kelas')
        df_meta = buat_tabel_matriks(df_raw, 'mapel') # Matrix ini isinya nama mapel
        
        # Fungsi Styling Pandas
        def style_color(row):
            # Kita butuh index baris untuk mencocokkan dengan df_meta
            # Sayangnya 'apply' per baris agak tricky untuk cross-reference dataframe lain di Pandas Styler standard
            # Jadi kita loop manual styles list
            styles = []
            
            # Dapatkan index baris saat ini di df_meta
            # Asumsi index row sama persis (karena berasal dari pivot yang sama)
            meta_row = df_meta.loc[row.name] 
            
            for col, val in row.items():
                if col in ['waktu', 'index']:
                    styles.append('')
                    continue
                    
                mapel_val = meta_row[col]
                if mapel_val in color_map:
                    bg = color_map[mapel_val]
                    styles.append(f'background-color: {bg}; color: black; font-weight: bold; border: 1px solid white')
                else:
                    styles.append('color: #e0e0e0') # Abu-abu untuk sel kosong
            return styles

        # Terapkan Style
        # Note: axis=1 artinya apply per baris
        styled_df = df_display.style.apply(style_color, axis=1).set_properties(**{'text-align': 'center'})

        st.dataframe(
            styled_df, 
            width=2000, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "waktu": st.column_config.TextColumn("🕒 Jam", width="small"),
                "SENIN": st.column_config.TextColumn("Senin", width="small"),
                "SELASA": st.column_config.TextColumn("Selasa", width="small"),
                "RABU": st.column_config.TextColumn("Rabu", width="small"),
                "KAMIS": st.column_config.TextColumn("Kamis", width="small"),
                "JUMAT": st.column_config.TextColumn("Jumat", width="small"),
            }
        )
    else:
        st.warning("Guru ini tidak memiliki jadwal mengajar di tabel utama.")

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
                    progress_bar.progress(30, text="Baca Data Guru & Mapel...")
                    guru_dict = ekstrak_semua_guru(pdf, idx_guru)
                    progress_bar.progress(60, text="Baca Grid Jadwal...")
                    jadwal_list = ekstrak_seluruh_jadwal(pdf, idx_jadwal)
                    simpan_database({"guru": guru_dict, "jadwal": jadwal_list})
                    progress_bar.progress(100, text="Selesai!")
                    st.rerun()
        except Exception as e: st.error(f"Error: {e}")