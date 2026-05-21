# 1. Use a lightweight Python base
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Install system-level dependencies
# We need 'nmap' for AFANDE and 'libpq-dev' for the Postgres database connection
RUN apt-get update && apt-get install -y \
    nmap \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy your requirements file first (this speeds up future builds)
COPY requirements.txt .

# 5. Install Python libraries
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of your project code into the container
COPY . .

# 7. Expose the port Streamlit uses
EXPOSE 8501

# The 'command' is usually handled by docker-compose, 
# but we can set a default here just in case.
CMD ["streamlit", "run", "main.py"]