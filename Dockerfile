# # Use the official Python image as a base
# FROM python:3.11-slim

# # Set environment variables
# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# # Set the working directory in the container
# WORKDIR /app

# # Install system dependencies
# RUN apt-get update && apt-get install -y \
#     libpq-dev \
#     gcc \
#     python3-dev \
#     musl-dev \
#     && apt-get clean

# # Install Python dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy the rest of the application
# COPY . .

# # Expose the application on port 8000
# EXPOSE 8000

# # Run the Django development server
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


ENV PYTHONUNBUFFERED=1


# Make port 8000 available to the world outside this container
EXPOSE 8000

RUN pip install gunicorn


# Run Django using Gunicorne
CMD ["gunicorn", "Manasu.wsgi:application", "--bind", "0.0.0.0:8000"]


