# Use an official openresty runtime as a parent image
FROM openresty/openresty:trusty

# Set the working directory to /app
WORKDIR /home/gui

# Copy the current directory contents into the container at /app
ADD src/ /home/gui

# Install any needed packages specified in requirements.txt
RUN apt-get install -y python3-pip
RUN pip3 install -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80
EXPOSE 443

# Run app.py when the container launches
CMD ["python3", "app.py"]
