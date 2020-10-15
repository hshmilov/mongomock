#!/usr/bin/env bash
source bash_imports.sh
sleep 5
mkdir -p logs/manager
docker exec $DOCKER_NAME python3 ./devops/scripts/watchdog/watchdog_main.py stop
docker stop $DOCKER_NAME
docker rm $DOCKER_NAME
create_axonius_manager
docker exec $DOCKER_NAME python3 ./devops/create_pth.py