# ─── Use a slim Python 3.11 base image ────────────────────────────────────────
FROM python:3.11-slim

# Prevent Python from writing .pyc files and ensure logs show immediately
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ─── Set the working directory inside the container ───────────────────────────
WORKDIR /app

# ─── Install system dependencies ──────────────────────────────────────────────
# Needed by packages like chromadb and sentence-transformers
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ─── Copy and install Python dependencies ─────────────────────────────────────
# Copy requirements first so Docker can cache this layer efficiently
COPY backend/requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── Copy the entire backend source code into the container ───────────────────
COPY backend/ .

# ─── Expose the port FastAPI runs on ──────────────────────────────────────────
EXPOSE 8000

# ─── Start the FastAPI server using Uvicorn ───────────────────────────────────
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
