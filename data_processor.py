import pandas as pd

def create_matrix_table(df, value_column):
    """Original logic: creates a matrix (pivot) table for display."""
    days = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT", "SABTU"]
    # Sorting periods numerically
    try:
        unique_periods = sorted(df['jam_ke_clean'].unique(), 
                              key=lambda x: int(x.split('-')[0]) if '-' in str(x) else int(x))
    except:
        unique_periods = sorted(df['jam_ke_clean'].unique())
        
    matrix = pd.DataFrame(index=unique_periods, columns=days).fillna("")
    
    for _, row in df.iterrows():
        d = row['hari']
        p = row['jam_ke_clean']
        v = row[value_column]
        if d in days:
            matrix.at[p, d] = v
            
    matrix.reset_index(inplace=True)
    matrix.rename(columns={'index': 'Jam Ke'}, inplace=True)
    return matrix

def get_teacher_info_display(codes, teacher_dict):
    """Original logic: gets teacher names from codes list."""
    res = []
    for c in codes:
        name = teacher_dict.get(c, {}).get('nama', c)
        res.append(name)
    return ", ".join(res)
