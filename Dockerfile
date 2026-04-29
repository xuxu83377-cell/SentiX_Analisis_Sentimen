# Gunakan image yang support Python 3.11 + Node 18
FROM python:3.11-bullseye

WORKDIR /app

# Install Node.js 18
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

# Install system dependencies untuk Playwright + Xvfb
RUN apt-get update && apt-get install -y \
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

# Verifikasi Node & npm
RUN node --version && npm --version

# Install tweet-harvest 2.6.1 global
RUN npm install -g tweet-harvest@2.6.1

# Install Playwright Chromium
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npx playwright install chromium --with-deps

# Verifikasi
RUN which tweet-harvest && echo "tweet-harvest OK"
RUN which npx && echo "npx OK"

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy semua file project
COPY . .

# Buat folder crawling
RUN mkdir -p tweets-data

# Retrain model dengan Python 3.11 + numpy terbaru
RUN python train_model.py

# Jalankan Xvfb + gunicorn
CMD Xvfb :99 -screen 0 1280x1024x24 -ac & sleep 2 && gunicorn mysite.wsgi:application --bind 0.0.0.0:$PORT --timeout 300 --workers 1 --threads 4