#!/usr/bin/env bash

echo "Removing all containers, volumes, networks, and axonius images"
docker network rm axonius
docker rm -f $(docker ps -a -q)
docker volume rm $(docker volume ls -q)
docker rmi $(docker images -q --filter=reference='axonius/*')

echo "Logging to docker hub and pulling axonius-base-image"
source testing/test_credentials/docker_login.sh
time docker pull axonius/axonius-base-image

echo "Building all images"
python3.6 devops/prepare_setup.py

echo "Creating network"
docker network create axonius
