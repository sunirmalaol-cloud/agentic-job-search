FROM  python:3.11

WORKDIR /job_search.py

# Prevent Python from generating bytecode
ENV PYTHONDONTWRITEBYTECODE=1

# Display logs immediately
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY job_search.py .

COPY requirements1.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN python -m pip install --no-cache-dir --timeout 120 --retries 10 -r requirements1.txt

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "job_search.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]