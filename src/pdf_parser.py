import pdfplumber
import re

def clean_period_code(text):
    """Original logic: Extracts period range from text."""
    if not text: return ""
    nums = re.findall(r'\d+', str(text))
    return "-".join(nums)

def clean_teacher_codes(text, hari=None):
    """Original logic: cleans teacher codes from cell content."""
    if not text: return []
    # Logic: remove times/day names if accidentally included
    raw = str(text).replace('\n', ' ')
    if hari: raw = raw.replace(hari, '')
    
    # Simple split by comma or space
    parts = re.split(r'[,\s]+', raw)
    return [p.strip().upper() for p in parts if len(p.strip()) >= 2 and len(p.strip()) <= 4]

def identify_pages(pdf):
    """Original logic: identifies which pages contain teacher list vs grid."""
    idx_guru = None
    idx_jadwal = []
    
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "DAFTAR GURU" in text.upper():
            idx_guru = i
        if "JAM" in text.upper() and "SENIN" in text.upper():
            idx_jadwal.append(i)
            
    return idx_guru, idx_jadwal

def extract_all_teachers(pdf, page_idx):
    """Original logic: extracts teacher dictionary from PDF page."""
    dict_guru = {}
    page = pdf.pages[page_idx]
    table = page.extract_table()
    if table:
        for row in table:
            if len(row) >= 3:
                kode = str(row[1]).strip().upper() if row[1] else ""
                nama = str(row[2]).strip() if row[2] else ""
                mapel = str(row[3]).strip() if len(row) > 3 and row[3] else ""
                if kode and nama:
                    dict_guru[kode] = {"nama": nama, "mapel": mapel}
    return dict_guru

def extract_all_schedules(pdf, page_indices):
    """Original logic: extracts all schedule items from multiple grid pages."""
    master_jadwal = []
    for idx in page_indices:
        page = pdf.pages[idx]
        table = page.extract_table()
        if not table: continue
        
        headers = [str(h).replace('\n', ' ').strip() for h in table[0]]
        
        hari = "SENIN"
        for row in table[1:]:
            if not any(row): continue
            
            # Update current day
            col0 = str(row[0]).upper()
            for d in ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT", "SABTU"]:
                if d in col0: hari = d
            
            waktu = str(row[0]).replace('\n', ' ').strip()
            jam_ke_raw = str(row[1]).replace('\n', ' ').strip()
            jam_ke_clean = clean_period_code(jam_ke_raw)
            
            for col_idx in range(2, len(row)):
                kelas = headers[col_idx] if col_idx < len(headers) else f"Kelas-{col_idx}"
                isi_sel = row[col_idx]
                
                if isi_sel:
                    codes = clean_teacher_codes(isi_sel, hari=hari)
                    if codes:
                        master_jadwal.append({
                            "jam_ke_clean": jam_ke_clean,
                            "hari": hari,
                            "waktu": waktu,
                            "kelas": kelas,
                            "list_kode_guru": codes
                        })
    return master_jadwal
