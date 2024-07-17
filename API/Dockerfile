# Use the official Python base image
FROM python:3.12-slim

RUN apt-get update && apt-get install ffmpeg -y

# Set the working directory in the container
WORKDIR /app

# Copy the entire current directory to the container
COPY . .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]