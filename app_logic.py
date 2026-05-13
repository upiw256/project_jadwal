import pandas as pd

def create_schedule_matrix(df, value_col):
    """Transforms flat schedule data into a Monday-Friday pivot table."""
    days = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT"]
    periods = sorted(df['jam_ke_clean'].unique(), key=lambda x: int(x.split('-')[0]) if x and '-' in x else (int(x) if x and x.isdigit() else 0))
    
    matrix = pd.DataFrame(index=periods, columns=days).fillna("")
    
    for _, row in df.iterrows():
        day = row['hari']
        period = row['jam_ke_clean']
        val = row[value_col]
        if day in days:
            matrix.at[period, day] = val
            
    matrix.reset_index(inplace=True)
    matrix.rename(columns={'index': 'Period'}, inplace=True)
    return matrix

def generate_color_map(subjects):
    """Assigns unique colors to subjects for UI highlighting."""
    colors = [
        '#FFADAD', '#FFD6A5', '#FDFFB6', '#CAFFBF', '#9BF6FF', 
        '#A0C4FF', '#BDB2FF', '#FFC6FF', '#FFFFFC'
    ]
    color_map = {}
    for i, subject in enumerate(sorted(list(subjects))):
        if subject:
            color_map[subject] = colors[i % len(colors)]
    return color_map
