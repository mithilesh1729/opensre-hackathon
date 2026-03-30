FROM python:3.10-slim

# Install system utilities
RUN apt-get update && apt-get install -y \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create the non-root user Hugging Face requires!
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Copy requirements and install
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your files
COPY --chown=user . .

# Expose the port
EXPOSE 7860

# Keep the Space alive safely without crashing on missing imports
CMD ["python", "-m", "http.server", "7860", "--bind", "0.0.0.0"]