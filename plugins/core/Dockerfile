FROM axonius/axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app

# Copy the current directory contents into the container at /app
COPY src/ ./

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

EXPOSE 5050
