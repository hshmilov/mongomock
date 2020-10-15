#!/usr/bin/env bash
source bash_imports.sh
sleep 5
mkdir -p logs/manager
docker stop $DOCKER_NAME
docker rm $DOCKER_NAME
create_axonius_manager
docker exec axonius-manager python3 ./devops/create_pth.py