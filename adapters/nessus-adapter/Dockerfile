FROM axonius/axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app

# Copy the current directory contents into the container at /app
COPY src/ ./

RUN pip3 install -r requirements.txt

EXPOSE 5555