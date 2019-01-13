#!/usr/bin/env bash

export CORTEX_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $CORTEX_ROOT/prepare_python_env.sh

echo "Killing dockers"
RUNNING_DOCKERS=$( docker ps -q )
if [ "$RUNNING_DOCKERS" != "" ]; then
    docker kill ${RUNNING_DOCKERS}
fi

echo "Removing all containers"
RUNNING_DOCKERS=$( docker ps -a -q )
if [ "$RUNNING_DOCKERS" != "" ]; then
    docker rm -f ${RUNNING_DOCKERS}
    docker rm -f ${RUNNING_DOCKERS} # docker graph dependency issue
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
    docker volume rm -f ${AVAILABLE_VOLUMES} # docker graph dependency issue
    AVAILABLE_VOLUMES=$( docker volume ls -q )
    if [ "$AVAILABLE_VOLUMES" != "" ]; then
        echo "Available volumes remaining: $AVAILABLE_VOLUMES"
        exit 1
    fi
fi

if [[ $1 == "images" ]]; then
    echo "Removing all images"
    AVAILABLE_IMAGES=$( docker images -q --filter=reference='axonius/*' )
    if [ "$AVAILABLE_IMAGES" != "" ]; then
        docker rmi -f ${AVAILABLE_IMAGES}
        docker rmi -f ${AVAILABLE_IMAGES}   # docker graph dependency issue
        AVAILABLE_IMAGES=$( docker images -q --filter=reference='axonius/*' )
        if [ "$AVAILABLE_IMAGES" != "" ]; then
            echo "Axonius images remaining: $AVAILABLE_IMAGES"
            # Problematic in Windows
            # exit 1
        fi
    fi
fi
