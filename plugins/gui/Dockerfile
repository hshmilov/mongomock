FROM axonius/axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app

# Copy the current directory contents into the container at /app
COPY src/ ./
COPY /config/nginx_conf.d/ /home/axonius/config/nginx_conf.d/
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Install more dependencies and build gui.
RUN curl -sL https://deb.nodesource.com/setup_6.x | bash - && \
    apt-get install -y nodejs && nodejs -v && node -v && npm -v

# After installation, we need to compile it.
RUN cd ./frontend && npm install && npm run dev-build

# Make port 80,443 available to the world outside this container
EXPOSE 80
EXPOSE 443