# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN apt-get update && apt-get install -y libpq-dev gcc python3-dev musl-dev && apt-get clean
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn
RUN pip install gunicorn

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run Django using Gunicorn with specified workers and timeout
CMD ["gunicorn", "--workers", "3", "--timeout", "60", "--bind", "0.0.0.0:8000", "Manasu.wsgi:application"]
