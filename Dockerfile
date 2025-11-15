# ---- Frontend builder ----
FROM node:20-slim AS frontend-builder
WORKDIR /frontend

# Copy package files for dependency installation (using lockfile for reproducible builds)
COPY frontend/package*.json ./
COPY frontend/package-lock.json ./

# Install frontend dependencies with lockfile
RUN npm ci --legacy-peer-deps

# Copy source code and build
COPY frontend/ .
RUN npm run build

# Clean up npm cache to reduce layer size
RUN npm cache clean --force && rm -rf /frontend/node_modules

# ---- Backend dependencies installer ----
FROM python:3.12-slim AS backend-deps

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build dependencies for Python packages that need compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Remove build dependencies after installing Python packages
RUN apt-get remove -y build-essential && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ---- Production image ----
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copy installed Python dependencies from the backend-deps stage
COPY --from=backend-deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-deps /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Copy built frontend assets from builder stage
COPY --from=frontend-builder /frontend/dist ./frontend/dist

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
