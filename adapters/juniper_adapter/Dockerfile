FROM axonius/axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app

# Copy the current directory contents into the container at /app
COPY ./ ./juniper/

# installing the juniper space rest platform package.
RUN pip3 install ./py-space-platform
