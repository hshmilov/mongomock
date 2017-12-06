# Use axonius-base-image. This gets is from a private repository in docker hub, use docker login to login!
FROM axonius/axonius-base-image

WORKDIR /home/axonius
ENV HOME /home/axonius

# Just copy configuration.
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# The following changes a lot, we want less build-time so its a different RUN command.
RUN mkdir /home/axonius/logs

# At this point we have openresty, python3, and axonius-libs installed.
# Lets set up configuration files to have our final https server running.
COPY src/config/uwsgi.ini ./config/uwsgi.ini
COPY src/app/main.py ./app/main.py
COPY src/config/supervisord.conf /etc/supervisor/supervisord.conf
COPY src/config/nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
COPY src/keys/nginx-selfsigned.crt /etc/ssl/certs/nginx-selfsigned.crt
COPY src/keys/nginx-selfsigned.key /etc/ssl/private/nginx-selfsigned.key
COPY src/keys/dhparam.pem /etc/ssl/certs/dhparam.pem
COPY src/config/nginx-ssl /etc/nginx/snippets/

# Install axonius-libs.
COPY src/libs /home/axonius/libs
COPY src/hacks /home/axonius/hacks
RUN pip3 install -e /home/axonius/libs/axonius-py

# Make port 80 available to the world outside this container
EXPOSE 80

# Notice that supervisord runs a couple of processes (look at supervisord.conf).
# We need both uwsgi and nginx in the same docker environment, and we need them 'operational',
# so supervisord takes care of re-running them in case they crashed, plus it directs stdout to /dev/stdout
# and stderr to /dev/stderr to make the output be shown in the terminal when we use docker run.
# Notice also that supervisord takes care of sigterm signals so if we press ctrl+c or shut down the docker
# it all works like a charm.
CMD ["supervisord"]
