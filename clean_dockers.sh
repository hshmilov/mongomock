#!/usr/bin/env bash
set -e

export CORTEX_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $CORTEX_ROOT/venv/bin/activate

docker kill $(docker ps -q)
docker rm $(docker ps -a -q)
docker volume rm $(docker volume ls -q)
