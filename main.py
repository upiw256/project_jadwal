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
# 1. FUNGSI FORMATTING (MATRIX BY JAM KE)
# ==========================================
def buat_tabel_matriks(df_input, value_col):
    """Mengubah data list menjadi tabel matriks (Jam Ke x Hari)."""
    
    # Helper untuk sorting jam ke (1, 2, 3... 10)
    def bersihkan_jam_ke(x):
        angka = re.findall(r'\d+', str(x))
        return int(angka[0]) if angka else 999

    df_input['sort_key'] = df_input['jam_ke'].apply(bersihkan_jam_ke)

    # Pivot Data
    df_pivot = df_input.pivot_table(index=['sort_key', 'jam_ke'], columns='hari', values=value_col, aggfunc='first')
    
    # Reindex hari
    hari_order = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT"]
    df_pivot = df_pivot.reindex(columns=hari_order)
    
    # Sort & Reset
    df_pivot = df_pivot.sort_index(level=0)
    df_pivot = df_pivot.reset_index()
    
    # Bersihkan kolom helper
    df_pivot = df_pivot.drop(columns=['sort_key'])
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
        fmt_jam = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#F5F5F5', 'font_color': 'black', 'border': 1})
        fmt_kosong = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_color': '#BDBDBD', 'border': 1})
        
        # Format untuk sel berisi (Wrap text aktif agar (Waktu) bisa turun ke bawah jika sempit)
        formats_mapel = {}
        for mapel, hex_color in color_map.items():
            formats_mapel[mapel] = workbook.add_format({
                'align': 'center', 'valign': 'vcenter', 
                'fg_color': hex_color, 
                'font_color': 'black', 
                'border': 1, 'bold': True,
                'text_wrap': True 
            })

        # Atur Lebar Kolom
        for col_num, value in enumerate(df_kelas.columns.values):
            worksheet.write(0, col_num, value, fmt_header)
            # Lebarkan kolom hari (index > 0) karena isinya sekarang "Kelas (Waktu)"
            width = 25 if col_num > 0 else 10 
            worksheet.set_column(col_num, col_num, width)
        
        for row_num, row_data in enumerate(df_kelas.values):
            worksheet.write(row_num + 1, 0, row_data[0], fmt_jam)
            for col_num, cell_value in enumerate(row_data[1:], start=1):
                col_name = df_kelas.columns[col_num]
                mapel_val = df_mapel.iloc[row_num][col_name]
                
                if cell_value != "-" and mapel_val in formats_mapel:
                    worksheet.write(row_num + 1, col_num, cell_value, formats_mapel[mapel_val])
                else:
                    worksheet.write(row_num + 1, col_num, cell_value, fmt_kosong)
            
        start_legend = len(df_kelas) + 3
        worksheet.write(start_legend, 0, "KETERANGAN MAPEL:", workbook.add_format({'bold': True}))
        row_leg = start_legend + 1
        for mapel, fmt in formats_mapel.items():
            worksheet.write(row_leg, 0, "", fmt)
            worksheet.write(row_leg, 1, mapel)
            row_leg += 1
            
    return output.getvalue()

def buat_pdf(df_kelas, df_mapel, nama_guru, color_map_rgb):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 16)
            self.set_text_color(0, 0, 0)
            self.cell(0, 10, f'Jadwal: {nama_guru}', ln=True, align='C')
            self.ln(5)
    
    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    col_w_jam = 15
    col_w_hari = 52 # Agak lebar untuk muat teks
    col_h = 12 # Tinggi baris ditambah biar muat 2 baris (Kelas + Waktu)
    headers = df_kelas.columns.tolist()
    
    # Header
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(68, 68, 68) 
    pdf.set_text_color(255, 255, 255)
    pdf.cell(col_w_jam, col_h, "KE", border=1, align='C', fill=True)
    for h in headers[1:]:
        pdf.cell(col_w_hari, col_h, h, border=1, align='C', fill=True)
    pdf.ln()
    
    # Body
    pdf.set_font("Arial", size=9) # Font agak kecil
    for i, row in df_kelas.iterrows():
        # Kolom Jam Ke
        pdf.set_font("Arial", 'B', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(col_w_jam, col_h, str(row['jam_ke']), border=1, align='C', fill=True)
        
        # Kolom Hari
        pdf.set_font("Arial", '', 9)
        for col_name in headers[1:]:
            isi = str(row[col_name])
            mapel = df_mapel.iloc[i][col_name]
            
            if isi != "-" and mapel in color_map_rgb:
                r, g, b = color_map_rgb[mapel]
                pdf.set_fill_color(r, g, b)
                pdf.set_text_color(0, 0, 0)
                # MultiCell simulation agar teks wrap
                x = pdf.get_x()
                y = pdf.get_y()
                pdf.cell(col_w_hari, col_h, isi, border=1, align='C', fill=True)
            else:
                pdf.set_text_color(0, 0, 0)
                pdf.cell(col_w_hari, col_h, isi, border=1, align='C', fill=False)
        pdf.ln()
    
    # Legend
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "KETERANGAN MAPEL:", ln=True)
    
    pdf.set_font("Arial", size=10)
    for mapel, rgb in color_map_rgb.items():
        r, g, b = rgb
        pdf.set_fill_color(r, g, b)
        pdf.cell(10, 6, "", border=1, fill=True)
        pdf.cell(0, 6, f"  :  {mapel}", ln=True)
        pdf.ln(2)
        
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 3. CORE LOGIC (EKSTRAKSI)
# ==========================================
def simpan_database(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f)

def baca_database():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
                if data and isinstance(data, dict) and 'guru' in data and 'jadwal' in data:
                    return data
                return None
        except (json.JSONDecodeError, ValueError):
            return None
    return None

def reset_database():
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.query_params.clear()
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
                if i + 2 < len(clean_row): 
                    kode = clean_row[i]
                    nama = clean_row[i+1]
                    mapel = clean_row[i+2]
                    if re.match(r'^\d+[A-Z]?$', kode) and len(nama) > 2:
                        data_guru[kode] = {'nama': nama.replace('\n', ' '), 'mapel': mapel.replace('\n', ' ')}
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
                if "WAKTU" in cek_header and "JAM KE" in cek_header: continue 
                
                waktu = clean_row[1] if len(clean_row) > 1 else "-"
                jam_ke = clean_row[2] if len(clean_row) > 2 else "?" 
                
                if "06.3" in waktu or "06:3" in waktu: current_hari_index += 1
                hari = LIST_HARI[current_hari_index] if 0 <= current_hari_index < len(LIST_HARI) else "Lainnya"
                
                if not jam_ke or len(jam_ke) > 3: continue 

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
                                 "jam_ke": jam_ke, 
                                 "kelas": kelas
                             })
    return master_jadwal

# ==========================================
# 4. USER INTERFACE
# ==========================================
st.set_page_config(page_title="TugasKu - Jadwal Sekolah", layout="wide")

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
        pass 
st.divider()

# --- MODE RESET ---
is_reset_mode = st.query_params.get("mode") == "reset"
if is_reset_mode:
    st.error("⚠️ **ADMIN ZONE: RESET DATABASE**")
    st.markdown("Halaman ini terkunci. Masukkan password untuk melanjutkan.")
    admin_pass = st.text_input("Masukkan Password Admin:", type="password")
    if admin_pass == "5414450":
        st.success("Akses Diterima ✅")
        st.warning("Peringatan: Tindakan ini akan menghapus semua data jadwal!")
        if st.button("🗑️ HAPUS DATABASE & RESET", type="primary"):
            reset_database()
    elif admin_pass:
        st.error("Password Salah! ❌")
    st.divider()

# --- LOGIKA UTAMA ---
database = baca_database()

if database is not None:
    dict_guru = database['guru']
    list_jadwal = database['jadwal']
    st.success("📂 Database Siap.")
    
    with st.expander("🔍 Klik untuk Cari Guru / Download", expanded=True):
        col_filter1, col_filter2 = st.columns([2, 2])
        
        with col_filter1:
            st.markdown("### 1. Pilih Guru")
            unique_names = sorted(list(set([v['nama'] for v in dict_guru.values()]))) if dict_guru else []
            
            pilihan_nama = None
            found_codes = []
            
            if unique_names:
                pilihan_nama = st.selectbox("Ketik Nama Guru:", unique_names)
                found_codes = [k for k, v in dict_guru.items() if v['nama'] == pilihan_nama]
                mapel_info = {k: dict_guru[k]['mapel'] for k in found_codes}
                
                st.info(f"Kode: {', '.join(found_codes)}")
                
                colors_hex = ["#94FA98", "#FAF19F", "#9FD4FF", "#FFA7B0"]
                colors_rgb = [(200, 230, 201), (255, 249, 196), (187, 222, 251), (255, 205, 210)]
                unique_mapels = sorted(list(set(mapel_info.values())))
                
                if len(unique_mapels) > 0:
                    color_map = {m: colors_hex[i % len(colors_hex)] for i, m in enumerate(unique_mapels)}
                    color_map_rgb = {m: colors_rgb[i % len(colors_rgb)] for i, m in enumerate(unique_mapels)}
                    
                    cols_legenda = st.columns(len(unique_mapels))
                    for i, m in enumerate(unique_mapels):
                        c = color_map[m]
                        cols_legenda[i].markdown(f"<div style='background-color:{c};color:black;padding:5px;border-radius:5px;margin: 10px;text-align:center;border:1px solid #ccc'><b>{m}</b></div>", unsafe_allow_html=True)
                else:
                    color_map = {}
                    color_map_rgb = {}
                    st.caption("Tidak ada data mapel spesifik.")
            else:
                st.warning("Data guru kosong.")

        with col_filter2:
            st.markdown("### 2. Download Jadwal")
            if pilihan_nama and found_codes:
                df_master = pd.DataFrame(list_jadwal)
                df_raw = df_master[df_master['kode_guru'].isin(found_codes)].copy()
                df_raw['mapel'] = df_raw['kode_guru'].map(lambda x: mapel_info.get(x, '-'))
                
                if not df_raw.empty:
                    # --- [UPDATE] BUAT ISI SEL JADI "KELAS (WAKTU)" ---
                    # Kita buat kolom baru 'tampilan_sel'
                    df_raw['tampilan_sel'] = df_raw.apply(lambda x: f"{x['kelas']} ({x['waktu']})", axis=1)
                    
                    # Gunakan 'tampilan_sel' sebagai nilai matriks
                    df_matriks_display = buat_tabel_matriks(df_raw, 'tampilan_sel')
                    df_matriks_mapel = buat_tabel_matriks(df_raw, 'mapel')
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        file_excel = buat_excel(df_matriks_display, df_matriks_mapel, pilihan_nama, color_map)
                        st.download_button("📄 Excel", file_excel, f'Jadwal_{pilihan_nama}.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
                    with c2:
                        try:
                            file_pdf = buat_pdf(df_matriks_display, df_matriks_mapel, pilihan_nama, color_map_rgb)
                            st.download_button("📑 PDF", file_pdf, f'Jadwal_{pilihan_nama}.pdf', 'application/pdf', use_container_width=True)
                        except Exception as e: st.error(f"PDF Error: {e}")
                else:
                    st.warning("Data jadwal kosong.")

    # 2. TABEL GURU
    if pilihan_nama:
        with st.expander(f"📅 Jadwal Mengajar: {pilihan_nama}", expanded=True):
            if 'df_raw' in locals() and not df_raw.empty:
                # --- [UPDATE] TAMPILAN WEB JUGA IKUT FORMAT BARU ---
                if 'tampilan_sel' not in df_raw.columns:
                     df_raw['tampilan_sel'] = df_raw.apply(lambda x: f"{x['kelas']} ({x['waktu']})", axis=1)
                
                df_display = buat_tabel_matriks(df_raw, 'tampilan_sel')
                df_meta = buat_tabel_matriks(df_raw, 'mapel') 
                
                def style_color(row):
                    styles = []
                    meta_row = df_meta.loc[row.name] 
                    for col, val in row.items():
                        if col in ['jam_ke', 'sort_key', 'index']:
                            styles.append('')
                            continue
                        
                        mapel_val = meta_row[col]
                        if mapel_val in color_map:
                            bg = color_map[mapel_val]
                            styles.append(f'background-color: {bg}; color: black; font-weight: bold; border: 1px solid white')
                        else:
                            styles.append('')
                    return styles

                styled_df = df_display.style.apply(style_color, axis=1).set_properties(**{'text-align': 'center'})

                st.dataframe(
                    styled_df, 
                    width=2000, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "jam_ke": st.column_config.TextColumn("Jam Ke", width="small"),
                        "SENIN": st.column_config.TextColumn("Senin", width="medium"),
                        "SELASA": st.column_config.TextColumn("Selasa", width="medium"),
                        "RABU": st.column_config.TextColumn("Rabu", width="medium"),
                        "KAMIS": st.column_config.TextColumn("Kamis", width="medium"),
                        "JUMAT": st.column_config.TextColumn("Jumat", width="medium"),
                    }
                )
            else:
                st.warning("Guru ini tidak memiliki jadwal mengajar di tabel utama.")

    # 3. TABEL KELAS
    st.divider()
    st.subheader("🏫 Jadwal Berdasarkan Kelas")
    
    if list_jadwal:
        all_classes = sorted(list(set([j['kelas'] for j in list_jadwal])))
        pilihan_kelas = st.selectbox("Pilih Kelas:", all_classes)
        
        if pilihan_kelas:
            df_master = pd.DataFrame(list_jadwal)
            df_kelas_filtered = df_master[df_master['kelas'] == pilihan_kelas].copy()
            
            if not df_kelas_filtered.empty:
                def get_display_text(row):
                    kode = row['kode_guru']
                    waktu = row['waktu']
                    if kode in dict_guru:
                        g = dict_guru[kode]
                        nama_pendek = g['nama'].split(',')[0]
                        # Format: Mapel (Guru) (Waktu)
                        return f"{g['mapel']} ({nama_pendek})\n({waktu})"
                    return f"{kode} ({waktu})"

                df_kelas_filtered['isi_sel'] = df_kelas_filtered.apply(get_display_text, axis=1)
                
                df_matrix_kelas = buat_tabel_matriks(df_kelas_filtered, 'isi_sel')
                
                st.dataframe(
                    df_matrix_kelas,
                    width=2000,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "jam_ke": st.column_config.TextColumn("Jam Ke", width="small"),
                        "SENIN": st.column_config.TextColumn("Senin", width="medium"),
                        "SELASA": st.column_config.TextColumn("Selasa", width="medium"),
                        "RABU": st.column_config.TextColumn("Rabu", width="medium"),
                        "KAMIS": st.column_config.TextColumn("Kamis", width="medium"),
                        "JUMAT": st.column_config.TextColumn("Jumat", width="medium"),
                    }
                )
            else:
                st.info("Jadwal kelas ini tidak ditemukan.")

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