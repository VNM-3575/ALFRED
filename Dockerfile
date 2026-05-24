# 1. Use a lightweight Python base
FROM python:3.12-slim

# 2. Set environment variables to optimize Python
# Prevents Python from writing .pyc files to disk and forces unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Install system-level dependencies
# We need 'nmap' for AFANDE and 'libpq-dev' for the Postgres database connection
# --no-install-recommends prevents downloading unnecessary bloatware
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 5. Copy your requirements file first (this maximizes Docker layer caching)
COPY requirements.txt .

# 6. Install Python libraries
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 7. Copy the rest of your project code into the container
COPY . .

# 8. Expose the port Streamlit uses
EXPOSE 8501

# The 'command' is usually handled by docker-compose, 
# but we can set a default here just in case.
CMD ["streamlit", "run", "main.py"]
