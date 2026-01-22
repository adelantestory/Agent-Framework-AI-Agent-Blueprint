# Use official Python 3.13 slim image
FROM python:3.13-slim

# Set working directory in container
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements-lock.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-lock.txt

# Copy application code
COPY . .

# Expose port 5000
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]