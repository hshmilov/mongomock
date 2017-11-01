# Use an official Axonius Image parent image.
# Notice! The compilation script will fail if this is not develop-latest or master-latest if you are
# PR'ing this code into develop or master.
FROM axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app

# Copy the current directory contents into the container at /app
COPY src/ ./
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Make port 80,443 available to the world outside this container
EXPOSE 80
EXPOSE 443