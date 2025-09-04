# Menggunakan Python 3.9 sebagai base image. Kamu bisa ganti versi ini sesuai kebutuhan.
FROM python:3.9-slim

# Menentukan direktori kerja di dalam container.
WORKDIR /app

# Menyalin file requirements.txt ke direktori kerja container. Ini penting karena
# Docker akan menggunakan cache untuk langkah ini, mempercepat build selanjutnya.
COPY ./requirements.txt /app/requirements.txt

# Menginstal semua dependensi dari requirements.txt. Opsi "--no-cache-dir"
# akan mengurangi ukuran image.
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Menyalin seluruh kode proyekmu ke dalam direktori kerja container.
COPY . /app

# Memberitahu Docker bahwa aplikasi akan berjalan di port 8000.
EXPOSE 8000

# Perintah untuk menjalankan aplikasi FastAPI menggunakan Uvicorn. Pastikan
# "main:app" sesuai dengan nama file dan objek FastAPI-mu.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]