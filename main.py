import streamlit as st
import pdfplumber
import pandas as pd
import re
import json
import os
import io
from fpdf import FPDF

# Nama file database
DB_FILE = "database_jadwal.json"

# ==========================================
# 0. KAMUS & PEMBERSIH KODE (LOGIKA CERDAS)
# ==========================================
def bersihkan_kode(raw_text, hari=None):
    """
    Membersihkan kode guru dengan konteks HARI.
    """
    if not raw_text or raw_text == "-":
        return []

    # Pecah teks berdasarkan spasi/enter
    tokens = re.split(r'[\s\n]+', str(raw_text).strip())
    
    cleaned_codes = []
    for token in tokens:
        token = token.strip()
        if not token: continue
        
        # --- FIX TYPO SPESIFIK ---
        
        # KASUS: 32A di hari JUMAT adalah Typo (Harusnya 35A - Reiza)
        # Tapi di hari lain, 32A adalah Valid (Lukman - Informatika)
        if hari == "JUMAT" and token == "32A":
            token = "35A"
            
        # KASUS OCR (Salah baca angka mirip huruf)
        if re.match(r'^\d+8$', token): token = token[:-1] + "B" # 328 -> 32B
        elif re.match(r'^\d+4$', token): token = token[:-1] + "A" # 774 -> 77A
        elif token == "O5": token = "05"
        elif token == "l2": token = "12"
            
        cleaned_codes.append(token)
        
    return cleaned_codes

def get_guru_info_display(raw_kode_list, dict_guru):
    """Mengubah list kode menjadi teks 'Mapel (Guru)'"""
    if not raw_kode_list: return "-"
    
    display_list = []
    for kode in raw_kode_list:
        if kode in dict_guru:
            g = dict_guru[kode]
            nama_pendek = g['nama'].split(',')[0]
            display_list.append(f"{g['mapel']} ({nama_pendek})")
        else:
            display_list.append(kode)
            
    return "\n+\n".join(display_list)

# ==========================================
# 1. FUNGSI FORMATTING
# ==========================================
def buat_tabel_matriks(df_input, value_col):
    # Pivot
    df_pivot = df_input.pivot_table(index='jam_ke_clean', columns='hari', values=value_col, aggfunc='first')
    
    hari_order = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT"]
    df_pivot = df_pivot.reindex(columns=hari_order)
    
    df_pivot = df_pivot.sort_index()
    df_pivot = df_pivot.reset_index()
    df_pivot = df_pivot.fillna("-")
    
    df_pivot.rename(columns={'jam_ke_clean': 'Jam Ke'}, inplace=True)
    return df_pivot

# ==========================================
# 2. FUNGSI DOWNLOAD
# ==========================================
def buat_excel(df_display, nama_guru, color_map):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_display.to_excel(writer, index=False, sheet_name='Jadwal')
        workbook = writer.book
        worksheet = writer.sheets['Jadwal']
        
        fmt_wrap = workbook.add_format({'text_wrap': True, 'valign': 'vcenter', 'align': 'center', 'border': 1})
        fmt_header = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#444444', 'font_color': 'white', 'border': 1})
        fmt_jam = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#DDDDDD', 'border': 1})

        for col_num, value in enumerate(df_display.columns.values):
            worksheet.write(0, col_num, value, fmt_header)
            width = 25 if col_num > 0 else 10
            worksheet.set_column(col_num, col_num, width)
            
        for row_num, row_data in enumerate(df_display.values):
            worksheet.write(row_num + 1, 0, row_data[0], fmt_jam)
            for col_num, cell_value in enumerate(row_data[1:], start=1):
                col_name = df_display.columns[col_num]
                # Pewarnaan Excel (Optional Logic Here if needed, currently generic)
                worksheet.write(row_num + 1, col_num, cell_value, fmt_wrap)
                
    return output.getvalue()

def buat_pdf(df_display, nama_guru):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 14)
            self.cell(0, 10, f'Jadwal: {nama_guru}', ln=True, align='C')
            self.ln(5)
            
    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    headers = df_display.columns.tolist()
    w_cols = [15, 50, 50, 50, 50, 50] 
    
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(200, 200, 200)
    for i, h in enumerate(headers):
        pdf.cell(w_cols[i], 10, h, border=1, fill=True, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", size=8)
    for index, row in df_display.iterrows():
        line_height = 5
        max_lines = 1
        for i, h in enumerate(headers):
            txt = str(row[h])
            lines = pdf.multi_cell(w_cols[i], line_height, txt, border=0, split_only=True)
            if len(lines) > max_lines: max_lines = len(lines)
        row_height = max_lines * line_height
        
        if pdf.get_y() + row_height > 190:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 10)
            for i, h in enumerate(headers):
                pdf.cell(w_cols[i], 10, h, border=1, fill=True, align='C')
            pdf.ln()
            pdf.set_font("Arial", size=8)

        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        pdf.set_font("Arial", 'B', 9)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(w_cols[0], row_height, str(row[headers[0]]), border=1, fill=True, align='C')
        
        pdf.set_font("Arial", '', 8)
        x_current = x_start + w_cols[0]
        for i in range(1, len(headers)):
            h = headers[i]
            txt = str(row[h])
            pdf.set_xy(x_current, y_start)
            pdf.multi_cell(w_cols[i], line_height, txt, border=1, align='C')
            x_current += w_cols[i]
            
        pdf.set_xy(x_start, y_start + row_height)
        
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
        except: return None
    return None

def reset_database():
    with open(DB_FILE, 'w') as f: json.dump({}, f)
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
                    # Ambil kode guru. Fix typo 328->32B dilakukan disini tapi JANGAN 32A->35A
                    raw_kode = clean_row[i].split()[0] if clean_row[i] else ""
                    if re.match(r'^\d+8$', raw_kode): raw_kode = raw_kode[:-1] + "B"
                    
                    nama = clean_row[i+1]
                    mapel = clean_row[i+2]
                    
                    if re.match(r'^\d+[A-Z]?$', raw_kode) and len(nama) > 2:
                        data_guru[raw_kode] = {'nama': nama.replace('\n', ' '), 'mapel': mapel.replace('\n', ' ')}
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
                
                # Raw data untuk kode
                raw_row_data = [str(cell).strip() if cell else "" for cell in row]
                
                waktu = clean_row[1] if len(clean_row) > 1 else "-"
                jam_ke_raw = clean_row[2] if len(clean_row) > 2 else ""
                
                try: jam_ke_clean = int(re.findall(r'\d+', jam_ke_raw)[0])
                except: jam_ke_clean = 99
                
                if "06.3" in waktu or "06:3" in waktu: current_hari_index += 1
                hari = LIST_HARI[current_hari_index] if 0 <= current_hari_index < len(LIST_HARI) else "Lainnya"
                
                if len(waktu) < 3 and jam_ke_clean == 99: continue

                for col_idx, isi_sel in enumerate(raw_row_data):
                    if col_idx < 3: continue 
                    if isi_sel and len(isi_sel) < 100:
                         kelas = tebak_kelas(col_idx)
                         if kelas != "?": 
                             # [FIX UTAMA] Kirim 'hari' ke fungsi bersihkan_kode
                             cleaned_codes = bersihkan_kode(isi_sel, hari=hari)
                             
                             if cleaned_codes:
                                 master_jadwal.append({
                                     "jam_ke_clean": jam_ke_clean, 
                                     "hari": hari, 
                                     "waktu": waktu,   
                                     "kelas": kelas,
                                     "list_kode_guru": cleaned_codes 
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
st.divider()

is_reset_mode = st.query_params.get("mode") == "reset"
if is_reset_mode:
    st.error("⚠️ **ADMIN ZONE: RESET DATABASE**")
    admin_pass = st.text_input("Masukkan Password Admin:", type="password")
    if admin_pass == "5414450":
        if st.button("🗑️ HAPUS DATABASE & RESET", type="primary"):
            reset_database()
    st.divider()

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
            pilihan_nama = st.selectbox("Ketik Nama Guru:", unique_names) if unique_names else None
            
            found_codes = []
            if pilihan_nama:
                found_codes = [k for k, v in dict_guru.items() if v['nama'] == pilihan_nama]
                st.info(f"Kode: {', '.join(found_codes)}")
                
                colors_hex = ["#94FA98", "#FAF19F", "#9FD4FF", "#FFA7B0"]
                unique_mapels = sorted(list(set([dict_guru[k]['mapel'] for k in found_codes])))
                color_map = {m: colors_hex[i % len(colors_hex)] for i, m in enumerate(unique_mapels)}
                
                cols_legenda = st.columns(len(unique_mapels))
                for i, m in enumerate(unique_mapels):
                    c = color_map[m]
                    cols_legenda[i].markdown(f"<div style='background-color:{c};color:black;padding:5px;border-radius:5px;text-align:center'><b>{m}</b></div>", unsafe_allow_html=True)
            else:
                color_map = {}

        with col_filter2:
            st.markdown("### 2. Download Jadwal")
            if pilihan_nama and found_codes:
                df_master = pd.DataFrame(list_jadwal)
                guru_mapel_lookup = {k: dict_guru[k]['mapel'] for k in found_codes}

                processed_data = []
                for idx, row in df_master.iterrows():
                    cell_codes = row['list_kode_guru']
                    match = set(cell_codes) & set(found_codes)
                    
                    if match:
                        matched_code = list(match)[0]
                        mapel_val = guru_mapel_lookup.get(matched_code, "")
                        
                        processed_data.append({
                            "jam_ke_clean": row['jam_ke_clean'],
                            "hari": row['hari'],
                            "tampilan": f"{row['kelas']} ({row['waktu']})",
                            "mapel": mapel_val
                        })

                if processed_data:
                    df_res = pd.DataFrame(processed_data)
                    df_matriks_display = buat_tabel_matriks(df_res, 'tampilan')
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        file_excel = buat_excel(df_matriks_display, pilihan_nama, color_map)
                        st.download_button("📄 Excel", file_excel, f'Jadwal_{pilihan_nama}.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
                    with c2:
                        file_pdf = buat_pdf(df_matriks_display, pilihan_nama)
                        st.download_button("📑 PDF", file_pdf, f'Jadwal_{pilihan_nama}.pdf', 'application/pdf', use_container_width=True)
                else:
                    st.warning("Data jadwal kosong.")

    # TAMPILAN GURU
    if pilihan_nama and 'processed_data' in locals() and processed_data:
        with st.expander(f"📅 Jadwal Mengajar: {pilihan_nama}", expanded=True):
            df_display = buat_tabel_matriks(pd.DataFrame(processed_data), 'tampilan')
            df_meta = buat_tabel_matriks(pd.DataFrame(processed_data), 'mapel')
            
            def style_color(row):
                styles = []
                if row.name in df_meta.index:
                    meta_row = df_meta.loc[row.name]
                else:
                    return [''] * len(row)

                for col, val in row.items():
                    if col in ['Jam Ke', 'index']:
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
            st.dataframe(styled_df, width=2000, use_container_width=True, hide_index=True)

    # TAMPILAN KELAS
    st.divider()
    st.subheader("🏫 Jadwal Berdasarkan Kelas")
    if list_jadwal:
        all_classes = sorted(list(set([j['kelas'] for j in list_jadwal])))
        pilihan_kelas = st.selectbox("Pilih Kelas:", all_classes)
        if pilihan_kelas:
            df_master = pd.DataFrame(list_jadwal)
            df_kelas_filtered = df_master[df_master['kelas'] == pilihan_kelas].copy()
            
            if not df_kelas_filtered.empty:
                df_kelas_filtered['isi_sel'] = df_kelas_filtered['list_kode_guru'].apply(lambda x: get_guru_info_display(x, dict_guru))
                df_kelas_filtered['isi_lengkap'] = df_kelas_filtered.apply(lambda x: f"{x['isi_sel']}\n({x['waktu']})", axis=1)
                
                df_matrix_kelas = buat_tabel_matriks(df_kelas_filtered, 'isi_lengkap')
                st.dataframe(df_matrix_kelas, width=2000, use_container_width=True, hide_index=True)
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