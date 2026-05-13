import streamlit as st
import pandas as pd
import pdfplumber
from datetime import datetime, timedelta

# Import Modules
from src.database_manager import read_database, save_database, reset_database
from src.pdf_parser import identify_pages, extract_all_teachers, extract_all_schedules
from src.data_processor import create_matrix_table, get_teacher_info_display
from src.exporter import export_to_excel, export_to_pdf
from src.google_calendar import sync_to_google_calendar, delete_from_google_calendar

# ==========================================
# CONFIGURATION & STYLING
# ==========================================
st.set_page_config(page_title="TugasKu - Jadwal Sekolah", layout="wide")

st.markdown("""
<style>
    thead tr th { background-color: #444444 !important; color: white !important; text-align: center !important; }
    .stDataFrame { width: 100% !important; }
</style>
""", unsafe_allow_html=True)

def main():
    # Header
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1: st.title("🏫 TugasKu: Jadwal Sekolah")
    st.divider()

    # Admin Zone
    is_reset_mode = st.query_params.get("mode") == "reset"
    if is_reset_mode:
        st.error("⚠️ **ADMIN ZONE: RESET DATABASE**")
        admin_pass = st.text_input("Masukkan Password Admin:", type="password")
        if admin_pass == "5414450":
            if st.button("🗑️ HAPUS DATABASE & RESET", type="primary"):
                reset_database()
        st.divider()

    # Load Database
    database = read_database()

    if database is not None:
        dict_guru = database['guru']
        list_jadwal = database['jadwal']
        st.success("📂 Database Siap.")
        
        # UI: Filter & Download
        with st.expander("🔍 Klik untuk Cari Guru / Download", expanded=True):
            col_filter1, col_filter2 = st.columns([2, 2])
            with col_filter1:
                st.markdown("### 1. Pilih Guru")
                unique_names = sorted(list(set([v['nama'] for v in dict_guru.values()]))) if dict_guru else []
                pilihan_nama = st.selectbox("Ketik Nama Guru:", unique_names) if unique_names else None
                st.session_state['pilihan_nama'] = pilihan_nama
                
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
                        df_matriks_display = create_matrix_table(df_res, 'tampilan')
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            file_excel = export_to_excel(df_matriks_display, pilihan_nama, color_map)
                            st.download_button("📄 Excel", file_excel, f'Jadwal_{pilihan_nama}.xlsx', use_container_width=True)
                        with c2:
                            file_pdf = export_to_pdf(df_matriks_display, pilihan_nama)
                            st.download_button("📑 PDF", file_pdf, f'Jadwal_{pilihan_nama}.pdf', use_container_width=True)
                    else:
                        st.warning("Data jadwal kosong.")

            # Google Calendar Section
            st.divider()
            st.markdown("### 3. Google Calendar Sync")
            if pilihan_nama and 'processed_data' in locals() and processed_data:
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
                        sync_to_google_calendar(processed_data, sync_date, num_weeks=num_weeks)
                with col_btn2:
                    if st.button("🗑️ Bersihkan Calendar", type="secondary", use_container_width=True):
                        delete_from_google_calendar(sync_date, pilihan_nama, num_weeks=num_weeks)

        # TAMPILAN GURU
        if pilihan_nama and 'processed_data' in locals() and processed_data:
            with st.expander(f"📅 Jadwal Mengajar: {pilihan_nama}", expanded=True):
                df_display = create_matrix_table(pd.DataFrame(processed_data), 'tampilan')
                df_meta = create_matrix_table(pd.DataFrame(processed_data), 'mapel')
                
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
                    df_kelas_filtered['isi_sel'] = df_kelas_filtered['list_kode_guru'].apply(lambda x: get_teacher_info_display(x, dict_guru))
                    df_kelas_filtered['isi_lengkap'] = df_kelas_filtered.apply(lambda x: f"{x['isi_sel']}\n({x['waktu']})", axis=1)
                    df_matrix_kelas = create_matrix_table(df_kelas_filtered, 'isi_lengkap')
                    st.dataframe(df_matrix_kelas, width=2000, use_container_width=True, hide_index=True)

    else:
        st.info("👋 Belum ada data. Silakan upload PDF Jadwal (Merged).")
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        if uploaded_file:
            progress_bar = st.progress(0, text="Analisis PDF...")
            try:
                with pdfplumber.open(uploaded_file) as pdf:
                    idx_guru, idx_jadwal = identify_pages(pdf)
                    if idx_guru is None: idx_guru = 1 if len(pdf.pages) > 1 else 0
                    if not idx_jadwal: st.error("Halaman jadwal tidak ditemukan.")
                    else:
                        progress_bar.progress(30, text="Baca Data Guru & Mapel...")
                        guru_dict = extract_all_teachers(pdf, idx_guru)
                        progress_bar.progress(60, text="Baca Grid Jadwal...")
                        jadwal_list = extract_all_schedules(pdf, idx_jadwal)
                        save_database({"guru": guru_dict, "jadwal": jadwal_list})
                        progress_bar.progress(100, text="Selesai!")
                        st.rerun()
            except Exception as e: st.error(f"Error: {e}")

if __name__ == "__main__":
    main()