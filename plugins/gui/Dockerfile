FROM axonius/axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app

RUN apt-get update && \
    apt-get install -y npm && \
    curl -sL https://deb.nodesource.com/setup_8.x | bash - && \
    apt-get install -y nodejs

# Copy the current directory contents into the container at /app
COPY src/ ./

RUN cd ./frontend && npm install && npm run build

COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Make port 80,443 available to the world outside this container
EXPOSE 5050