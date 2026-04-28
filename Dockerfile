# Node 18 + Python + Playwright
FROM node:18-bullseye

WORKDIR /app

# Install Python & pip & system dependencies untuk Playwright + Xvfb
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
    libxfixes3 \
    libxrandr2 \
    libxcomposite1 \
    libxdamage1 \
    libxtst6 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    wget \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Verifikasi Node 18
RUN node --version && npm --version

# Install tweet-harvest 2.0.4 global
RUN npm install -g tweet-harvest@2.0.4

# Install Playwright Chromium
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npx playwright install chromium --with-deps

# Verifikasi tweet-harvest tersedia
RUN which tweet-harvest && echo "tweet-harvest OK"

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy semua file project
COPY . .

# Buat folder untuk hasil crawling
RUN mkdir -p tweets-data

# Retrain model
RUN python3 retrain.py

# Jalankan Xvfb lalu gunicorn
CMD Xvfb :99 -screen 0 1280x1024x24 -ac & sleep 2 && gunicorn mysite.wsgi:application --bind 0.0.0.0:$PORT --timeout 300 --workers 1 --threads 4