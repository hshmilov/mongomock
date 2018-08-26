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

# We need to remove dangling images or else we wouldn't be able to remove all axonius images, since they
# could be parent images of these images
echo "Removing dangling docker images"
DANGLING_IMAGES=$(docker images --filter "dangling=true" -q --no-trunc)
if [ "$DANGLING_IMAGES" != "" ]; then
    docker rmi ${DANGLING_IMAGES}
    DANGLING_IMAGES=$(docker images --filter "dangling=true" -q --no-trunc)
    if [ "$DANGLING_IMAGES" != "" ]; then
        exit 1
    fi
fi

AVAILABLE_IMAGES=$( docker images -q --filter=reference='axonius/*' )
if [ "$AVAILABLE_IMAGES" != "" ]; then
    docker rmi -f ${AVAILABLE_IMAGES}
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
