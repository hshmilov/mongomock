FROM axonius/axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app

# Copy the current directory contents into the container at /app
COPY src/ ./
COPY /config/nginx_conf.d/ /home/axonius/config/nginx_conf.d/

# Removing folders generated from build, so that next command will build properly
RUN cd ./frontend && rm -rf dist node_modules

# Compile npm. we assume we have it from axonius-libs
RUN cd ./frontend && npm set progress=false && npm install && npm run build