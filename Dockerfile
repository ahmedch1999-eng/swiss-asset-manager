FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal build tools required for some scientific packages, upgrade pip tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gfortran \
    && pip install --upgrade pip setuptools wheel \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to take advantage of Docker layer caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . /app

EXPOSE 8000

# Default port environment variable (app.py reads PORT)
ENV PORT=8000

CMD ["python", "app.py"]
