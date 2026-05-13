import pdfplumber
import re

def clean_period_code(period_str):
    """Extracts numeric period from string like '1. ', '2-3. '"""
    if not period_str: return ""
    nums = re.findall(r'\d+', period_str)
    return "-".join(nums)

def extract_schedule_from_pdf(pdf_file):
    """Parses school schedule PDF and returns a list of dictionaries."""
    all_data = []
    current_day = "UNKNOWN"
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table: continue
            
            headers = table[0]
            # Expected headers: Day/Time, Period, Class1, Class2...
            
            for row in table[1:]:
                if not any(row): continue
                
                # Check for day name in first column
                day_match = re.search(r'(SENIN|SELASA|RABU|KAMIS|JUMAT|SABTU)', str(row[0]).upper())
                if day_match:
                    current_day = day_match.group(1)
                
                time_range = str(row[0]) if row[0] else ""
                period_raw = str(row[1]) if row[1] else ""
                period_clean = clean_period_code(period_raw)
                
                # Iterate through class columns (starting from index 2)
                for col_idx in range(2, len(row)):
                    class_name = headers[col_idx] if headers[col_idx] else f"Class-{col_idx}"
                    cell_content = row[col_idx]
                    
                    if cell_content:
                        # Extract teacher codes (e.g. "AB, CD")
                        teacher_codes = [c.strip() for c in str(cell_content).split(',') if c.strip()]
                        
                        all_data.append({
                            "hari": current_day, # Keeping Indonesian for day name consistency with internal logic
                            "waktu": time_range.replace('\n', ' '),
                            "jam_ke_raw": period_raw,
                            "jam_ke_clean": period_clean,
                            "kelas": class_name.replace('\n', ' '),
                            "list_kode_guru": teacher_codes
                        })
    return all_data

def get_teacher_info_display(codes, teacher_dict):
    """Converts code list to display names."""
    names = []
    for c in codes:
        name = teacher_dict.get(c, c)
        names.append(name)
    return ", ".join(names)
