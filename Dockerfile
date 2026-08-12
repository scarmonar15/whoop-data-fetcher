FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set work directory
WORKDIR /app

# Install system dependencies (sqlite3 for DB inspections if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy project files
COPY . /app/

# Expose port
EXPOSE 8080

# Run Flask server via Gunicorn WSGI
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8080", "server:app"]
