FROM axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app

# Copy the current directory contents into the container at /app
COPY src/ ./
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip3 install -r requirements.txt
RUN pip3 uninstall requests -y
RUN pip3 install requests


EXPOSE 5001