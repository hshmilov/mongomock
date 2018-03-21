FROM axonius/axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app

# Copy the current directory contents into the container at /app
COPY ./ ./eset_adapter/

# Copying needed shared library /usr/bin for debugging and /usr/local/bin for prod.
COPY ./ERAApi/Network.so /usr/bin/
COPY ./ERAApi/Network.so /usr/local/bin/

# Copying the eset_connect.cpp
COPY ./ERAApi/* /home/axonius/bin/

# Compiling the eset_connect.cpp
RUN cd /home/axonius/bin && make