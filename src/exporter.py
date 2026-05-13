import io
import pandas as pd
from fpdf import FPDF
import xlsxwriter

def export_to_excel(df, teacher_name, color_map):
    """Original logic: generates Excel file with coloring."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Jadwal')
        workbook = writer.book
        worksheet = writer.sheets['Jadwal']
        
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
    return output.getvalue()

def export_to_pdf(df, teacher_name):
    """Original logic: generates PDF file."""
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Jadwal Mengajar: {teacher_name}", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    col_width = 270 / len(df.columns)
    for col in df.columns:
        pdf.cell(col_width, 10, str(col), border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        for item in row:
            pdf.cell(col_width, 10, str(item), border=1, align='C')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')
