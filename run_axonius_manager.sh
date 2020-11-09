#!/usr/bin/env bash
cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1
source bash_imports.sh
sleep 3
mkdir -p logs/manager
if [ $(docker ps --filter "name=$DOCKER_NAME" -q | wc -l) -gt 0 ]; then
  docker exec -d $DOCKER_NAME python3 ./devops/scripts/watchdog/watchdog_main.py stop detached
  sleep 15
fi
docker stop $DOCKER_NAME
docker rm $DOCKER_NAME
create_axonius_manager
docker exec $DOCKER_NAME python3 ./devops/create_pth.py
docker exec $DOCKER_NAME ipython -c "exit()"
docker exec $DOCKER_NAME python3 ./devops/scripts/fast_axonius/install.py