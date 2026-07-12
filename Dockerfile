FROM python:3.9-slim

WORKDIR /app

# Install dependencies sistem (opsional tapi disarankan untuk fpdf/pandas)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Buka port untuk Streamlit (8501) dan FastAPI (8000)
EXPOSE 8501
EXPOSE 8000

# Menjalankan FastAPI di background (&) lalu menjalankan Streamlit di foreground
CMD uvicorn api_jadwal:app --host 0.0.0.0 --port 8000 & \
    streamlit run main.py --server.port=8501 --server.address=0.0.0.0