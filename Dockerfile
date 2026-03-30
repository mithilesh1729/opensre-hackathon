FROM python:3.10-slim

# Install system utilities required for SRE troubleshooting
RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache optimisation)
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 -r requirements.txt

COPY . .

# HF Spaces requires port 7860
EXPOSE 7860

# Start a lightweight built-in Python web server to keep the Space alive
CMD ["python", "-m", "http.server", "7860", "--bind", "0.0.0.0"]