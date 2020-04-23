# Use our own openresty, which is compiled without the support of SSE4_2, to support old cpu's.
# This is the build instructions:
# git clone https://github.com/openresty/docker-openresty.git
# cd docker-openresty
# docker build -f xenial/Dockerfile --build-arg "RESTY_CONFIG_OPTIONS_MORE=--with-luajit-xcflags='-mno-sse4.2'" -t axonius/openresty:xenial.
# docker login ....
# docker push axonius/openresty:xenial
# docker logout
FROM axonius/openresty:xenial

WORKDIR /home/axonius
ENV HOME /home/axonius

# Disable SSL Verify and Hostname Verify
COPY nexus-apt /etc/apt/apt.conf.d/nexus
# Install dependencies and configure the rest of the things we need.
RUN apt-get update && \
    apt-get install -y ssh git libxmlsec1-dev apt-transport-https ca-certificates \
    supervisor software-properties-common python-software-properties odbc-postgresql freetds-dev freetds-bin unixodbc-dev tdsodbc && \
    add-apt-repository "deb https://axoniusreadonly:7wr7E6kfttdVgn5e@nexus.pub.axonius.com/repository/proxy-python3.6 xenial main" && \
    curl -sSk https://nexus.pub.axonius.com/ppa_certs/deadcert.key | apt-key add - && \
    apt-get update && \
    apt-get install -y python3.6 python3.6-dev python3.6-venv ipython python-pip && \
    curl https://bootstrap.pypa.io/get-pip.py | python3.6 && \
    ln -s /usr/bin/python3.6 /usr/local/bin/python3 && \
    apt-get install -y libpango1.0-0 && \
    apt-get install -y libcairo2 && \
    apt-get install -y libffi-dev && \
    apt-get install -y vim && \
    apt-get install -y nano && \
    apt-get install -y net-tools && \
    apt-get install -y iputils-ping && \
    apt-get install -y libpq-dev && \
    apt-get install libaio1

RUN /bin/bash -c 'echo -e "[FreeTDS]\nDescription=FreeTDS Driver\nDriver=/usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so\nSetup=/usr/lib/x86_64-linux-gnu/odbc/libtdsS.so" > /etc/odbcinst.ini'
RUN /bin/bash -c 'echo -e "\n\n[PostgreSQL Unicode]\nDescription=PostgreSQL ODBC Driver (Unicode version)\nDriver=/usr/lib/x86_64-linux-gnu/odbc/psqlodbcw.so\nSetup=/usr/lib/x86_64-linux-gnu/odbc/libodbcpsqlS.so\nDebug=0\nCommLog=1\nUsageCount=1" >> /etc/odbcinst.ini'

# Install AWS dependencies
RUN curl -o /usr/bin/aws-iam-authenticator https://amazon-eks.s3-us-west-2.amazonaws.com/1.10.3/2018-07-26/bin/linux/amd64/aws-iam-authenticator && \
    chmod +x /usr/bin/aws-iam-authenticator

# Install more gui dependencies.

RUN curl -sL https://deb.nodesource.com/setup_8.x | bash - && \
    apt-get install -y nodejs && nodejs -v && node -v && npm -v

COPY pip.conf /etc/pip.conf
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

# Install Oracle Instant Client as instructed here
# https://oracle.github.io/odpi/doc/installation.html#oracle-instant-client-zip
COPY instantclient-basiclite-linux.x64-19.3.0.0.0dbru.zip /home/axonius/temp/instantclient-basiclite-linux.x64-19.3.0.0.0dbru.zip
RUN mkdir -p /opt/oracle && cd /opt/oracle && unzip /home/axonius/temp/instantclient-basiclite-linux.x64-19.3.0.0.0dbru.zip && echo /opt/oracle/instantclient_19_3 > /etc/ld.so.conf.d/oracle-instantclient.conf && ldconfig

RUN rm -rf temp

RUN mkdir temp_openssl
# Build Fips object module
RUN cd temp_openssl && curl -O https://www.openssl.org/source/openssl-fips-2.0.16.tar.gz && \
    tar xf openssl-fips-2.0.16.tar.gz && \
    cd openssl-fips-2.0.16 && \
    ./config && \
    make && \
    make install

# Build OpenSSL with FIPS
RUN cd temp_openssl && curl -O https://www.openssl.org/source/old/1.0.2/openssl-1.0.2u.tar.gz && \
    tar xf openssl-1.0.2u.tar.gz && \
    cd openssl-1.0.2u && \
    ./config shared fips --with-fipslibdir=/usr/local/ssl/fips-2.0/lib/  && \
    make depend && \
    make && \
    make install

# Build cryptography with our new openssl
# Please check that cryptography matches cryptography version on requirements.txt
RUN export CFLAGS="-I/usr/local/share/ssl/include -DOPENSSL_FIPS=1" \
    LDFLAGS="-L/usr/local/share/ssl/lib" \
    cd temp_openssl \
    && pip wheel --no-cache --no-binary :all: cryptography==2.8 \
    && pip install -I cryptography*.whl \
    && unset CFLAGS LDFLAGS

RUN rm -rf temp_openssl

# Update system openssl
RUN cp /usr/local/ssl/lib/libcrypto.so.* /lib/x86_64-linux-gnu/ && \
    cp /usr/local/ssl/lib/libssl.so.* /lib/x86_64-linux-gnu/

# Set a label for this image.
LABEL "com.axonius.image-type"="axonius"
