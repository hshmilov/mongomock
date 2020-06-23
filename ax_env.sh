#!/usr/bin/env bash

export CORTEX_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $CORTEX_ROOT/venv/bin/activate
source $CORTEX_ROOT/devops/devops.rc

alias se=/home/ubuntu/cortex/se.sh
eval "$(_AX_COMPLETE=source ax)"
