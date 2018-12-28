#!/usr/bin/env bash

echo "Removing all containers"
RUNNING_DOCKERS=$( docker ps -a -q )
if [ "$RUNNING_DOCKERS" != "" ]; then
    docker rm -f ${RUNNING_DOCKERS}
    docker rm -f ${RUNNING_DOCKERS}     # docker graph dependency
    RUNNING_DOCKERS=$( docker ps -a -q )
    if [ "$RUNNING_DOCKERS" != "" ]; then
        echo "Running dockers remaining: $RUNNING_DOCKERS"
        exit 1
    fi
fi

echo "Removing all volumes"
AVAILABLE_VOLUMES=$( docker volume ls -q )
if [ "$AVAILABLE_VOLUMES" != "" ]; then
    docker volume rm -f ${AVAILABLE_VOLUMES}
    docker volume rm -f ${AVAILABLE_VOLUMES}    # docker graph dependency
    AVAILABLE_VOLUMES=$( docker volume ls -q )
    if [ "$AVAILABLE_VOLUMES" != "" ]; then
        echo "Available volumes remaining: $AVAILABLE_VOLUMES"
        exit 1
    fi
fi

# We need to remove dangling images or else we wouldn't be able to remove all axonius images, since they
# could be parent images of these images
echo "Removing dangling docker images"
DANGLING_IMAGES=$(docker images --filter "dangling=true" -q --no-trunc)
if [ "$DANGLING_IMAGES" != "" ]; then
    docker rmi ${DANGLING_IMAGES}
    docker rmi ${DANGLING_IMAGES}   # docker graph dependency
    DANGLING_IMAGES=$(docker images --filter "dangling=true" -q --no-trunc)
    if [ "$DANGLING_IMAGES" != "" ]; then
        echo "Dangling images remaining: $DANGLING_IMAGES"
        exit 1
    fi
fi


# Sometimes, we do not want the axonius images to get deleted.
if [ "$1" != "--cache-images" ]; then
    echo "Removing all images"
    AVAILABLE_IMAGES=$( docker images -q --filter=reference='axonius/*' )
    if [ "$AVAILABLE_IMAGES" != "" ]; then
        docker rmi -f ${AVAILABLE_IMAGES}
        docker rmi -f ${AVAILABLE_IMAGES}   # docker graph dependency
        AVAILABLE_IMAGES=$( docker images -q --filter=reference='axonius/*' )
        if [ "$AVAILABLE_IMAGES" != "" ]; then
            echo "Axonius images remaining: $AVAILABLE_IMAGES"
            exit 1
        fi
    fi
fi

echo "Removing all networks"
AVAILABLE_NETWORKS=$( docker network ls -q --filter type=custom)
if [ "$AVAILABLE_NETWORKS" != "" ]; then
    docker network rm ${AVAILABLE_NETWORKS}
    docker network rm ${AVAILABLE_NETWORKS}
    AVAILABLE_NETWORKS=$( docker network ls -q --filter type=custom)
    if [ "$AVAILABLE_NETWORKS" != "" ]; then
        echo "Axonius networks remaining: $AVAILABLE_NETWORKS"
        exit 1
    fi
fi
