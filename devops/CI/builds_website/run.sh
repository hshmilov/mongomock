#!/usr/bin/env bash
set -e

docker-compose build --no-cache
docker-compose down

if [ "$1" == "debug" ]; then
    echo Running builds in debug mode..
    docker-compose -f docker-compose.yml -f docker-compose.debug.yml up -d
else
    echo Running builds in prod mode..
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
fi
echo Done running builds.