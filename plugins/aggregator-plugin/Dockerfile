# Use an official Python runtime as a parent image
FROM python:3.6-alpine

# Set the working directory to /app
WORKDIR /home/aggregator_plugin

# Copy the current directory contents into the container at /app
ADD src /home/aggregator_plugin
ADD requirements.txt /home/aggregator_plugin/

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 5000

# Run app.py when the container launches
CMD ["python", "src/main.py"]

