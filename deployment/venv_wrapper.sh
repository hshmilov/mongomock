#!/usr/bin/env bash

# a simple wrapper around calling the python from current venv with a provided script and arguments.

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ -d "${CURRENT_DIR}/../venv/bin" ]; then
    ACTIVATE=${CURRENT_DIR}/../venv/bin/activate
else
    if [ -d "${CURRENT_DIR}/../venv/Scripts" ]; then
        ACTIVATE=${CURRENT_DIR}/../venv/Scripts/activate
    else
        echo Missing bin folder
        exit 1
    fi
fi
# wrapper for venv's python
source ${ACTIVATE}

python3 $*
