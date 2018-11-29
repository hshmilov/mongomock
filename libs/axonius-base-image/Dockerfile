# Use openresty.
FROM openresty/openresty:xenial

WORKDIR /home/axonius
ENV HOME /home/axonius

# Install dependencies and configure the rest of the things we need.
RUN apt-get update && \
    apt-get install -y ssh git libxmlsec1-dev \
    supervisor software-properties-common python-software-properties freetds-dev freetds-bin unixodbc-dev tdsodbc && \
    add-apt-repository ppa:jonathonf/python-3.6 && \
    apt-get update && \
    apt-get install -y python3.6 python3.6-dev python3.6-venv ipython python-pip && \
    curl https://bootstrap.pypa.io/get-pip.py | python3.6 && \
    ln -s /usr/bin/python3.6 /usr/local/bin/python3 && \
    apt-get install -y libpango1.0-0 && \
    apt-get install -y libcairo2 && \
    apt-get install -y vim && \
    apt-get install -y nano && \
    apt-get install -y net-tools && \
    apt-get install -y iputils-ping && \
    apt-get install -y libpq-dev

RUN /bin/bash -c 'echo -e "[FreeTDS]\nDescription=FreeTDS Driver\nDriver=/usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so\nSetup=/usr/lib/x86_64-linux-gnu/odbc/libtdsS.so" > /etc/odbcinst.ini'

# Install AWS dependencies
RUN curl -o /usr/bin/aws-iam-authenticator https://amazon-eks.s3-us-west-2.amazonaws.com/1.10.3/2018-07-26/bin/linux/amd64/aws-iam-authenticator && \
    chmod +x /usr/bin/aws-iam-authenticator

# Install more gui dependencies.

RUN curl -sL https://deb.nodesource.com/setup_6.x | bash - && \
    apt-get install -y nodejs && nodejs -v && node -v && npm -v

# Install python requirements

COPY requirements2.txt .
RUN pip2 install -r requirements2.txt

COPY requirements.txt .
RUN pip3 install -r requirements.txt

# this SDK isn't available under public PIP
# https://vdc-download.vmware.com/vmwb-repository/dcr-public/8c68a127-a4fd-4535-a819-3a64d94ca5cb/2b4c33f5-6011-4b43-99c7-1a14b1855f4b/VMware-vCloud-Suite-SDK-Python-6.0.0-2561074-READMEs/client/vCloud-Suite-Client-SDK-Python-README.html
# https://github.com/vmware/vsphere-automation-sdk-python

RUN mkdir temp
COPY VMware-vCloud-Suite-SDK-Python-6.0.0-2561074.zip /home/axonius/temp/cloud_suite.zip
RUN cd temp && unzip cloud_suite.zip

# you might be wondering why I'm using --no-deps here
# It's because I love it when you install an old package that has an old requirement
# so pip uninstalls the current, not old, requirement
# but pip also depends on that requirement not being too old
# so pip breaks itself
# so far this works so please don't touch

RUN cd temp && pip3 install VMware-vCloud-Suite-SDK-Python-6.0.0/client/lib/vapi_runtime-1.0.0.zip --no-deps
RUN cd temp && pip3 install VMware-vCloud-Suite-SDK-Python-6.0.0/client/lib/vapi_common_client-1.0.0.zip --no-deps
RUN cd temp && pip3 install VMware-vCloud-Suite-SDK-Python-6.0.0/client/lib/vapi_client_bindings-1.0.0.zip --no-deps

RUN rm -rf temp

# Set a label for this image.
LABEL "com.axonius.image-type"="axonius"
