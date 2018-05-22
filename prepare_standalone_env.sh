#!/usr/bin/env bash
# Only to be used by a linux user on a non-operational environment.
export CORTEX_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export PYTHONPATH="$PYTHONPATH:$CORTEX_ROOT:\
$CORTEX_ROOT/axonius-libs/src/libs/axonius-py:\
$CORTEX_ROOT/plugins:\
$CORTEX_ROOT/adapters:\
$CORTEX_ROOT/devops:\
$CORTEX_ROOT/testing"