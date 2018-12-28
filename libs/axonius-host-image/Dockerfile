# This Dockerfile specifies the dependencies we need for running an Axonius system.
# Take the latest stable docker-in-docker and installs all of the host image dependencies in it
FROM docker:18.09.0-dind

WORKDIR /home/axonius
ENV HOME /home/axonius

RUN apk update && apk upgrade && apk add --no-cache bash linux-headers nano vim curl pkgconfig python3-dev python-dev openssl-dev libffi-dev libxml2-dev libxslt-dev musl-dev make gcc tcl-dev tk-dev tiff-dev openjpeg-dev lcms2-dev freetype-dev zlib-dev jpeg-dev openssl git python python3
RUN ln -sf /usr/bin/python3 /usr/bin/python && ln -sf /usr/bin/python3-config /usr/bin/python && python2 -m ensurepip && python3 -m ensurepip && python2 -m pip install --upgrade pip && python3 -m pip install --upgrade pip && pip2 install virtualenv && pip3 install virtualenv && rm -rf /root/.cache && pip2 install --upgrade setuptools && pip3 install --upgrade setuptools
RUN curl -L git.io/weave -o /usr/local/bin/weave && chmod a+x /usr/local/bin/weave
