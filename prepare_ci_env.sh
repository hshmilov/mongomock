#!/usr/bin/env bash

echo "Removing all containers, volumes, and axonius images"
docker rm -f $(docker ps -a -q)
docker volume rm $(docker volume ls -q)
docker rmi $(docker images -q --filter=reference='axonius/*')

echo "Logging to docker hub and pulling axonius-base-image"
docker login -u axoniusdockerreadonly -p 48GguwDPOQbMNYj08Pmb
docker pull axonius/axonius-base-image

echo "Building all images"
(
docker pull axonius/axonius-base-image
docker build -t axonius/axonius-libs plugins/axonius-libs
docker build -t axonius/core plugins/core
docker build -t axonius/aggregator plugins/aggregator-plugin
#docker build -t axonius/watch-service plugins/watch-service
docker build -t axonius/gui plugins/gui
docker build -t axonius/ad-adapter adapters/ad-adapter
docker build -t axonius/aws-adapter adapters/aws-adapter
docker build -t axonius/esx-adapter adapters/esx-adapter
docker build -t axonius/epo-adapter adapters/epo-adapter
)

echo "Create venv"
./create_venv.sh
