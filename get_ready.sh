#!/usr/bin/env bash

echo "Removing all containers, volumes, and axonius images"
RUNNING_DOCKERS=$( docker ps -a -q )
if [ "$RUNNING_DOCKERS" != "" ]; then
    docker rm -f ${RUNNING_DOCKERS}
fi
AVAILABLE_VOLUMES=$( docker volume ls -q )
if [ "$AVAILABLE_VOLUMES" != "" ]; then
    docker volume rm ${AVAILABLE_VOLUMES}
fi
AVAILABLE_IMAGES=$( docker images -q )
if [ "$AVAILABLE_IMAGES" != "" ]; then
    docker rmi ${AVAILABLE_IMAGES}
fi

echo "Logging to docker hub and pulling axonius-base-image"
source testing/test_credentials/docker_login.sh
time docker pull axonius/axonius-base-image

docker build plugins/axonius-libs -t axonius/axonius-libs
