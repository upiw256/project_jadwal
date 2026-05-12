import streamlit as st
import pdfplumber
import pandas as pd
import re
import json
import os
import io
import pickle
from fpdf import FPDF
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Nama file database
DB_FILE = "database_jadwal.json"
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.pickle"
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# ==========================================
# GOOGLE CALENDAR LOGIC
# ==========================================
def get_google_calendar_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        except Exception:
            creds = None
    
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CLIENT_SECRET_FILE):
                    st.error(f"File {CLIENT_SECRET_FILE} tidak ditemukan. Silakan unduh dari Google Cloud Console.")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        except Exception as e:
            st.error(f"Gagal autentikasi Google: {e}")
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE) # Hapus token rusak
            return None
            
    return build('calendar', 'v3', credentials=creds)

def sync_to_google_calendar(events_data, start_monday, num_weeks=1):
    service = get_google_calendar_service()
    if not service:
        return False
    
    # 1. Hapus jadwal lama terlebih dahulu untuk rentang waktu yang dipilih
    with st.spinner(f"Membersihkan jadwal lama untuk {num_weeks} minggu ke depan..."):
        delete_from_google_calendar(start_monday, "System", num_weeks=num_weeks, show_ui=False)
    
    hari_map = {"SENIN": 0, "SELASA": 1, "RABU": 2, "KAMIS": 3, "JUMAT": 4}
    
    progress_bar = st.progress(0, text="Memulai sinkronisasi massal...")
    
    total_inserts = len(events_data) * num_weeks
    current_count = 0
    
    try:
        for week in range(num_weeks):
            week_monday = start_monday + timedelta(weeks=week)
            
            for ev in events_data:
                days_to_add = hari_map.get(ev['hari'], 0)
                event_date = week_monday + timedelta(days=days_to_add)
                
                times = ev['waktu'].split('-')
                start_t = times[0].strip().replace('.', ':')
                end_t = times[1].strip().replace('.', ':')
                
                if len(start_t.split(':')[0]) == 1: start_t = "0" + start_t
                if len(end_t.split(':')[0]) == 1: end_t = "0" + end_t

                start_iso = f"{event_date.strftime('%Y-%m-%d')}T{start_t}:00"
                end_iso = f"{event_date.strftime('%Y-%m-%d')}T{end_t}:00"
                
                event_body = {
                    'summary': f"Mengajar: {ev['kelas']}",
                    'description': f"Guru: {st.session_state.get('pilihan_nama', 'Unknown')}\nMata Pelajaran: {ev['mapel']}\nHari: {ev['hari']}\nJam Ke: {ev['jam_ke_clean']}",
                    'start': {'dateTime': start_iso, 'timeZone': 'Asia/Jakarta'},
                    'end': {'dateTime': end_iso, 'timeZone': 'Asia/Jakarta'},
                    # Tambahkan Recurrence rule agar lebih ringan sebenarnya bisa, 
                    # tapi karena permintaannya "sync ulang hapus dulu", kita pakai loop saja agar kontrol lebih presisi
                }
                
                service.events().insert(calendarId='primary', body=event_body).execute()
                current_count += 1
                
                if current_count % 5 == 0:
                    progress_bar.progress(current_count / total_inserts, text=f"Sinkronisasi {current_count}/{total_inserts} event...")
        
        st.success(f"✅ Berhasil sinkronisasi {total_inserts} jadwal untuk {num_weeks} minggu ke depan!")
        return True
    except Exception as e:
        st.error(f"Terjadi kesalahan saat sinkronisasi: {e}")
        return False

def delete_from_google_calendar(start_monday, teacher_name, num_weeks=1, show_ui=True):
    service = get_google_calendar_service()
    if not service:
        return False
    
    # Tentukan rentang waktu (sampai akhir minggu ke-N)
    time_min = start_monday.strftime('%Y-%m-%dT00:00:00+07:00')
    time_max = (start_monday + timedelta(weeks=num_weeks)).strftime('%Y-%m-%dT00:00:00+07:00')
    
    if show_ui: progress_bar = st.progress(0, text="Mencari event lama...")
    
    try:
        # Google API list max is usually 250 per page, for 6 months we might have ~1000 events
        # We need to handle pagination or just set maxResults higher
        events = []
        page_token = None
        while True:
            events_result = service.events().list(calendarId='primary', timeMin=time_min, timeMax=time_max,
                                                singleEvents=True, orderBy='startTime', pageToken=page_token).execute()
            events.extend(events_result.get('items', []))
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break
        
        if not events:
            if show_ui: st.info("Tidak ditemukan event jadwal lama pada rentang tersebut.")
            return True
        
        deleted_count = 0
        total_events = len(events)
        
        for i, event in enumerate(events):
            summary = event.get('summary', '')
            if "Mengajar:" in summary:
                service.events().delete(calendarId='primary', eventId=event['id']).execute()
                deleted_count += 1
            
            if show_ui: progress_bar.progress((i + 1) / total_events, text=f"Menghapus event lama {i+1}/{total_events}...")
            
        if show_ui and deleted_count > 0:
            st.success(f"🗑️ Berhasil menghapus {deleted_count} event jadwal lama.")
        return True
    except Exception as e:
        if show_ui: st.error(f"Gagal menghapus event: {e}")
        return False

# ==========================================
# 0. KAMUS & PEMBERSIH KODE / WAKTU
# ==========================================
def perbaiki_waktu(waktu_raw):
    """
    Memperbaiki teks waktu yang salah baca atau tidak sesuai keinginan.
    """
    if not waktu_raw: return "-"
    
    # Normalisasi: Ubah titik dua (:) jadi titik (.) agar konsisten
    # Contoh: 12:40 -> 12.40
    w = waktu_raw.replace(':', '.').strip()
    
    # KAMUS PERBAIKAN WAKTU
    # Format: "WAKTU SALAH DI PDF": "WAKTU YANG BENAR"
    KAMUS_WAKTU = {
        # Masalah Anda: Sistem baca 12.40, tapi harusnya 12.10
        "12.40 - 13.20": "12.10 - 13.20",
        
        # Contoh lain jika ada typo OCR
        "07.10 - 07.50": "07.10 - 07.50", 
    }
    
    # Cek apakah waktu ada di kamus (exact match)
    if w in KAMUS_WAKTU:
        return KAMUS_WAKTU[w]
        
    return w

def bersihkan_kode(raw_text, hari=None):
    """
    Membersihkan kode guru dengan logika AMAN (Anti-Hapus Kode 2 Digit).
    """
    if not raw_text or raw_text == "-":
        return []

    tokens = re.split(r'[\s\n]+', str(raw_text).strip())
    
    cleaned_codes = []
    for token in tokens:
        token = token.strip()
        if not token: continue
        
        # --- FIX TYPO SPESIFIK ---
        if hari == "JUMAT" and token == "32A":
            token = "35A"
            
        # Fix Typo OCR (Hanya jika > 2 digit untuk amankan kode 24, 44)
        if len(token) > 2:
            if re.match(r'^\d+8$', token): token = token[:-1] + "B" # 328 -> 32B
            elif re.match(r'^\d+4$', token): token = token[:-1] + "A" # 774 -> 77A
            
        if token == "O5": token = "05"
        elif token == "l2": token = "12"
            
        cleaned_codes.append(token)
        
    return cleaned_codes

def get_guru_info_display(raw_kode_list, dict_guru):
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
                    raw_kode = clean_row[i].split()[0] if clean_row[i] else ""
                    if len(raw_kode) > 2 and re.match(r'^\d+8$', raw_kode): raw_kode = raw_kode[:-1] + "B"
                    
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
                
                raw_row_data = [str(cell).strip() if cell else "" for cell in row]
                
                # --- [FIX WAKTU DISINI] ---
                waktu_raw = clean_row[1] if len(clean_row) > 1 else "-"
                # Terapkan perbaikan waktu
                waktu = perbaiki_waktu(waktu_raw)
                
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
                             cleaned_codes = bersihkan_kode(isi_sel, hari=hari)
                             if cleaned_codes:
                                 master_jadwal.append({
                                     "jam_ke_clean": jam_ke_clean, 
                                     "hari": hari, 
                                     "waktu": waktu, # Sudah diperbaiki 
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
                            "mapel": mapel_val,
                            "waktu": row['waktu'],
                            "kelas": row['kelas']
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
                
                st.markdown("### 3. Google Calendar Sync")
                st.write("Sinkronkan jadwal ini ke kalender pribadi Anda.")
                
                # Simpan nama guru di session state untuk diakses fungsi sync
                st.session_state['pilihan_nama'] = pilihan_nama
                
                today = datetime.now()
                default_monday = today - timedelta(days=today.weekday())
                
                col_sync1, col_sync2 = st.columns(2)
                with col_sync1:
                    sync_date = st.date_input("Pilih Tanggal Mulai (Senin):", default_monday)
                with col_sync2:
                    duration_opt = st.selectbox("Durasi Sinkronisasi:", ["1 Minggu", "6 Bulan (26 Minggu)"])
                    num_weeks = 1 if duration_opt == "1 Minggu" else 26

                if sync_date.weekday() != 0:
                    st.warning("⚠️ Sebaiknya pilih hari Senin agar sinkronisasi hari sesuai.")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🔄 Sync & Update Calendar", type="primary", use_container_width=True):
                        if processed_data:
                            sync_to_google_calendar(processed_data, sync_date, num_weeks=num_weeks)
                        else:
                            st.error("Tidak ada data untuk disinkronkan.")
                
                with col_btn2:
                    if st.button("🗑️ Bersihkan Calendar", type="secondary", use_container_width=True):
                        delete_from_google_calendar(sync_date, pilihan_nama, num_weeks=num_weeks)

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