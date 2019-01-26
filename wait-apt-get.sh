#!/bin/bash
i=0

until /usr/bin/apt-get "$@"
do
    ((i=i+1))
    if [ $i -gt 20 ]
    then
        echo "Timeout reached on $@!"
        exit 1
    fi
    echo "Waiting $i..."
    sleep 60
done