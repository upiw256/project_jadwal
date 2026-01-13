# Menggunakan base image Python yang ringan
FROM python:3.9-slim

# Mengatur working directory di dalam container
WORKDIR /app

# Menyalin file requirements terlebih dahulu (agar cache bekerja efisien)
COPY requirements.txt .

# Install dependencies
# (Menambahkan rm -rf agar image tetap kecil)
RUN pip install --no-cache-dir -r requirements.txt

# Menyalin seluruh sisa kode aplikasi ke dalam container
COPY . .

# Membuka port default Streamlit
EXPOSE 8501

# Perintah agar aplikasi berjalan saat container dimulai
ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]