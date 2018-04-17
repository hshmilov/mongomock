#!/usr/bin/env bash

export CORTEX_ROOT=`cd "$(dirname "$0")" && pwd`

source $CORTEX_ROOT/venv/bin/activate

export PYTHONPATH="$PYTHONPATH:$CORTEX_ROOT:\
$CORTEX_ROOT/axonius-libs/src/libs/axonius-py:\
$CORTEX_ROOT/plugins:\
$CORTEX_ROOT/adapters:\
$CORTEX_ROOT/devops:\
$CORTEX_ROOT/testing"