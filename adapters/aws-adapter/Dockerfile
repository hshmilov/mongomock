# Use an official Python runtime as a parent image
FROM python:3.6-alpine

# Set the working directory to /app
WORKDIR /home/aws_adapter

# Copy the current directory contents into the container at /app
ADD src /home/aws_adapter
ADD requirements.txt /home/aws_adapter/

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 5000

# Run app.py when the container launches
CMD ["python", "src/main.py"]

