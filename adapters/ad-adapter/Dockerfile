FROM axonius/axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app

# Copy the current directory contents into the container at /app
COPY src/ ./

# Install any needed packages specified in requirements.txt
RUN pip3 install -r requirements.txt

# Install any needed packages specified in requirements2.txt (for python 2)
RUN apt-get install -y python-pip && pip2 install -r requirements2.txt