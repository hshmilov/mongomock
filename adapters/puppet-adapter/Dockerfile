# Use an official Python runtime as a parent image
FROM python:3.6-slim

# Set the working directory to /app
WORKDIR /home/puppet_adapter

# Copy the current directory contents into the container at /app
ADD src /home/puppet_adapter
ADD requirements.txt /home/puppet_adapter/

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 5000

# Run app.py when the container launches
CMD ["python", "src/PuppetPlugin.py"]

