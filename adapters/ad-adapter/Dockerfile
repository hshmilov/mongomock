# Use an official Python runtime as a parent image
FROM python:3.6-alpine

# Set the working directory to /app
WORKDIR /home/ad_adapter

# Copy the current directory contents into the container at /app
ADD src /home/ad_adapter
ADD externals /home/ad_adapter/externals
ADD requirements.txt /home/ad_adapter/

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt
RUN pip install -e ./externals/axonius-libs

# Make port 80 available to the world outside this container
EXPOSE 5000

# Run app.py when the container launches
CMD ["python", "src/main.py"]

