# Use the official ultralytics base image
FROM ultralytics/ultralytics:latest

RUN apt-get update && apt-get install ffmpeg -y
    
# Set the working directory in the container
WORKDIR /app

# Copy the entire current directory to the container
COPY . .

    
ENTRYPOINT ["python3", "main.py"]
