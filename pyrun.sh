#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
cd $DIR
ARGS=$@
docker exec axonius-manager /bin/bash -c "python3 ./devops/create_pth.py; python3 $ARGS"
