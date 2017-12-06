# Use openresty.
FROM openresty/openresty:xenial

WORKDIR /home/axonius
ENV HOME /home/axonius

# Install dependencies and configure the rest of the things we need.
RUN apt-get update && \
    apt-get install -y ssh git \
    supervisor software-properties-common python-software-properties && \
    add-apt-repository ppa:jonathonf/python-3.6 && \
    apt-get update && \
    apt-get install -y python3.6 python3.6-dev python3.6-venv && \
    curl https://bootstrap.pypa.io/get-pip.py | python3.6 && \
    ln -s /usr/bin/python3.6 /usr/local/bin/python3

COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Install more gui dependencies.
RUN curl -sL https://deb.nodesource.com/setup_6.x | bash - && \
    apt-get install -y nodejs && nodejs -v && node -v && npm -v

# Set a label for this image.
LABEL "com.axonius.image-type"="axonius"
