FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua file
COPY . .

# Buat volume untuk persistent data
VOLUME ["/app/data"]

# Jalankan bot
CMD ["python", "bot.py"]