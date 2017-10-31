# Use openresty.
FROM openresty/openresty:xenial

WORKDIR /home/axonius

# Install dependencies and configure the rest of the things we need.
RUN apt-get update && \
    apt-get install -y ssh git \
    supervisor software-properties-common python-software-properties && \
    add-apt-repository ppa:jonathonf/python-3.6 && \
    apt-get update && \
    apt-get install -y python3.6 python3.6-dev python3.6-venv && \
    curl https://bootstrap.pypa.io/get-pip.py | python3.6 && \
    ln -s /usr/bin/python3.6 /usr/local/bin/python3

# The following changes a lot, we want less build-time so its a different RUN command.
RUN pip3 install uwsgi flask apscheduler retrying && \
    mkdir /home/axonius/logs

# Set a label for this image.
LABEL "com.axonius.image-type"="axonius-libs"

# At this point we have openresty, python3, and axonius-libs installed.
# Lets set up configuration files to have our final https server running.

COPY src/app/uwsgi.ini .
COPY src/app/main.py ./app/main.py
COPY src/config/supervisord.conf /etc/supervisor/supervisord.conf
COPY src/config/nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
COPY src/keys/nginx-selfsigned.crt /etc/ssl/certs/nginx-selfsigned.crt
COPY src/keys/nginx-selfsigned.key /etc/ssl/private/nginx-selfsigned.key
COPY src/keys/dhparam.pem /etc/ssl/certs/dhparam.pem
COPY src/config/nginx-ssl /etc/nginx/snippets/

# Install axonius-libs.
COPY src/libs /home/axonius/libs
RUN pip3 install -e /home/axonius/libs/axonius-py

# Make port 443 available to the world outside this container
EXPOSE 443

# Notice that supervisord runs a couple of processes (look at supervisord.conf).
# We need both uwsgi and nginx in the same docker environment, and we need them 'operational',
# so supervisord takes care of re-running them in case they crashed, plus it directs stdout to /dev/stdout
# and stderr to /dev/stderr to make the output be shown in the terminal when we use docker run.
# Notice also that supervisord takes care of sigterm signals so if we press ctrl+c or shut down the docker
# it all works like a charm.
CMD ["supervisord"]
