FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Install ffmpeg (required by yt-dlp to convert to audio)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --upgrade --no-cache-dir yt-dlp

# Copy the application code
COPY app.py .
COPY templates/ ./templates/

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]