#!/usr/bin/env bash
source bash_imports.sh
sleep 3
mkdir -p logs/manager
if [ $(docker ps --filter "name=$DOCKER_NAME" -q | wc -l) -eq 1 ]; then
  docker exec -d $DOCKER_NAME python3 ./devops/scripts/watchdog/watchdog_main.py stop detached
  sleep 2
fi
docker stop $DOCKER_NAME
docker rm $DOCKER_NAME
create_axonius_manager
docker exec $DOCKER_NAME python3 ./devops/create_pth.py