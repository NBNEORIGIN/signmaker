# Use Playwright's official Python image with browsers pre-installed
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 10000

# Start command
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
