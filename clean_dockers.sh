#!/usr/bin/env bash

export CORTEX_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $CORTEX_ROOT/venv/bin/activate

docker kill $(docker ps -aq | grep -v -E $(docker ps -aq --filter='name=weave' | paste -sd "|" -))
docker rm $(docker ps -aq | grep -v -E $(docker ps -aq --filter='name=weave' | paste -sd "|" -))
docker rm $(docker ps -aq | grep -v -E $(docker ps -aq --filter='name=weave' | paste -sd "|" -)) # docker graph dependency issue
docker volume rm $(docker volume ls -q)
if [[ $1 == "images" ]]; then
    docker rmi $(docker images -aq)
    docker rmi $(docker images -aq)
fi
