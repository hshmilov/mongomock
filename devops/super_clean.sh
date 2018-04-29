#!/usr/bin/env bash

echo "Removing all containers, volumes, networks, and axonius images"
RUNNING_DOCKERS=$( docker ps -a -q )
if [ "$RUNNING_DOCKERS" != "" ]; then
    docker rm -f ${RUNNING_DOCKERS}
    RUNNING_DOCKERS=$( docker ps -a -q )
    if [ "$RUNNING_DOCKERS" != "" ]; then
        exit 1
    fi
fi
AVAILABLE_VOLUMES=$( docker volume ls -q )
if [ "$AVAILABLE_VOLUMES" != "" ]; then
    docker volume rm -f ${AVAILABLE_VOLUMES}
    AVAILABLE_VOLUMES=$( docker volume ls -q )
    if [ "$AVAILABLE_VOLUMES" != "" ]; then
        exit 1
    fi
fi
AVAILABLE_IMAGES=$( docker images -q --filter=reference='axonius/*' )
if [ "$AVAILABLE_IMAGES" != "" ]; then
    docker rmi ${AVAILABLE_IMAGES}
    AVAILABLE_IMAGES=$( docker images -q --filter=reference='axonius/*' )
    if [ "$AVAILABLE_IMAGES" != "" ]; then
        exit 1
    fi
fi
AVAILABLE_NETWORKS=$( docker network ls -q --filter name=axonius )
if [ "$AVAILABLE_NETWORKS" != "" ]; then
    docker network rm axonius
    AVAILABLE_NETWORKS=$( docker network ls -q --filter name=axonius )
    if [ "$AVAILABLE_NETWORKS" != "" ]; then
        exit 1
    fi
fi
