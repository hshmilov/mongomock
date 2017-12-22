#!/usr/bin/env bash

echo "Removing all containers, volumes, and axonius images"
docker rm -f $(docker ps -a -q)
docker volume rm $(docker volume ls -q)
docker rmi $(docker images -q --filter=reference='axonius/*')

echo "Logging to docker hub and pulling axonius-base-image"
docker login -u axoniusdockerreadonly -p 48GguwDPOQbMNYj08Pmb
docker pull axonius/axonius-base-image

echo "Building all images"
python devops/prepare_setup.py
