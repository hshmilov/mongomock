#!/usr/bin/env bash

source venv/bin/activate

export CORTEX_ROOT=`cd "$(dirname "$0")" && pwd`
export PYTHONPATH="$PYTHONPATH:$CORTEX_ROOT:\
$CORTEX_ROOT/axonius-libs/src/libs/axonius-py:\
$CORTEX_ROOT/plugins:\
$CORTEX_ROOT/adapters:\
$CORTEX_ROOT/devops:\
$CORTEX_ROOT/testing"