# Use openresty.
FROM openresty/openresty:xenial

WORKDIR /home/axonius
ENV HOME /home/axonius

# Install dependencies and configure the rest of the things we need.
RUN apt-get update && \
    apt-get install -y ssh git \
    supervisor software-properties-common python-software-properties freetds-dev freetds-bin unixodbc-dev tdsodbc && \
    add-apt-repository ppa:jonathonf/python-3.6 && \
    apt-get update && \
    apt-get install -y python3.6 python3.6-dev python3.6-venv ipython python-pip && \
    curl https://bootstrap.pypa.io/get-pip.py | python3.6 && \
    ln -s /usr/bin/python3.6 /usr/local/bin/python3 && \
    apt-get install -y libpango1.0-0 && \
    apt-get install -y libcairo2 && \
    apt-get install -y libpq-dev

RUN /bin/bash -c 'echo -e "[FreeTDS]\nDescription=FreeTDS Driver\nDriver=/usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so\nSetup=/usr/lib/x86_64-linux-gnu/odbc/libtdsS.so" > /etc/odbcinst.ini'

# Install more gui dependencies.

RUN curl -sL https://deb.nodesource.com/setup_6.x | bash - && \
    apt-get install -y nodejs && nodejs -v && node -v && npm -v

# Install python requirements

COPY requirements2.txt .
RUN pip2 install -r requirements2.txt

COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Set a label for this image.
LABEL "com.axonius.image-type"="axonius"
