#!/usr/bin/env bash
echo "Removing all containers, volumes, networks, and axonius images"
docker network rm axonius
RUNNING_DOCKERS=$( docker ps -a -q )
if [ "$RUNNING_DOCKERS" != "" ]; then
    docker rm -f ${RUNNING_DOCKERS}
fi
AVAILABLE_VOLUMES=$( docker volume ls -q )
if [ "$AVAILABLE_VOLUMES" != "" ]; then
    docker volume rm ${AVAILABLE_VOLUMES}
fi
AVAILABLE_IMAGES=$( docker images -q --filter=reference='axonius/*' )
if [ "$AVAILABLE_IMAGES" != "" ]; then
    docker rmi ${AVAILABLE_IMAGES}
fi

set -e # from now on exit on any error 

echo "Logging to docker hub and pulling axonius-base-image"
source testing/test_credentials/docker_login.sh
time docker pull axonius/axonius-base-image

echo "Creating network"
docker network create axonius

# Note! prepare_setup.py should be the last thing in the script, since the return value
# of the whole script will be its return value. The CI uses this return value to know if
# we continue to the other stages.

echo "Building all images"
python3.6 devops/prepare_setup.py
