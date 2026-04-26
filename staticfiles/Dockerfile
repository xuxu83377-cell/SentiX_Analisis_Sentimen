# Base image Playwright — sudah include Node.js + Chromium dependencies
FROM mcr.microsoft.com/playwright:v1.44.0-jammy

WORKDIR /app

# Install Python & pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright Chromium browser
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npx playwright install chromium --with-deps

# Verifikasi Node.js & npx tersedia
RUN node --version && npm --version && npx --version

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt --break-system-packages

# Copy semua file project
COPY . .

# Buat folder untuk hasil crawling
RUN mkdir -p tweets-data

EXPOSE 8000

# Jalankan Django pakai gunicorn
CMD ["gunicorn", "mysite.wsgi:application", "--bind", "0.0.0.0:8000", "--timeout", "180", "--workers", "2"]
