#!/usr/bin/env bash

export CORTEX_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $CORTEX_ROOT/venv/bin/activate

docker kill $(docker ps -q)
docker rm $(docker ps -a -q)
docker rm $(docker ps -a -q) # docker graph dependency issue
docker volume rm $(docker volume ls -q)
if [[ $1 == "images" ]]; then
    docker rmi $(docker images -aq)
    docker rmi $(docker images -aq)
fi
