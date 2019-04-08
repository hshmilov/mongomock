# Inherit from ubuntu 18.04 - python3.6 pre-installed
FROM ubuntu:18.04

WORKDIR /home/axonius
ENV HOME /home/axonius
ENV DOMAIN builds.in.axonius.lan

# Install nginx-uwsgi-flask stack, pip3, pip2, python2
RUN apt-get -y update && apt-get -y install python3-pip python3-dev python python-pip python-dev nginx
RUN pip3 install uwsgi flask
RUN pip2 install supervisor

# Copy the app and config
RUN mkdir /home/axonius/logs
COPY app ./app
COPY config ./config

# Self-sign
RUN mkdir /home/axonius/keys
RUN openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 \
    -subj "/C=US/O=Axonius/CN=$DOMAIN" \
    -keyout /home/axonius/keys/nginx.key  -out /home/axonius/keys/nginx.crt
RUN openssl dhparam -out /home/axonius/keys/dhparam.pem 2048

# Implicitly trust our self-signed key
RUN cp /home/axonius/keys/nginx.crt /usr/local/share/ca-certificates/nginx.crt
RUN update-ca-certificates

# Install pip requirements
RUN pip3 install -r /home/axonius/app/requirements.txt

# Generate secret token
RUN openssl rand -hex 16 > /home/axonius/secret.txt

CMD ["supervisord", "-c", "/home/axonius/config/supervisord.conf"]
