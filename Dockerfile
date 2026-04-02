FROM python:3.11-slim

WORKDIR /app

# Install requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything else
COPY . .

# Set the Python path so it can find your modules in /src
ENV PYTHONPATH=/app/src

# Run the main script
CMD ["python", "src/main.py"]