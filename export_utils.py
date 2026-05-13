import io
import pandas as pd
from fpdf import FPDF
import xlsxwriter

def create_excel_download(df_matrix, teacher_name, color_map):
    """Generates a styled Excel file in memory."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_matrix.to_excel(writer, sheet_name='Schedule', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Schedule']
        
        # Simple formatting
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
        for col_num, value in enumerate(df_matrix.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
    return output.getvalue()

def create_pdf_download(df_matrix, teacher_name):
    """Generates a PDF file in memory."""
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Teaching Schedule: {teacher_name}", ln=True, align='C')
    pdf.ln(5)
    
    # Table headers
    pdf.set_font("Arial", 'B', 10)
    col_width = 270 / len(df_matrix.columns)
    for col in df_matrix.columns:
        pdf.cell(col_width, 10, str(col), border=1, align='C')
    pdf.ln()
    
    # Table data
    pdf.set_font("Arial", '', 9)
    for _, row in df_matrix.iterrows():
        for item in row:
            pdf.cell(col_width, 10, str(item), border=1, align='C')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')
