#!/usr/bin/env bash

export CORTEX_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $CORTEX_ROOT/venv/bin/activate

# docker shortcuts. Notice ! This file is used by customers, so we should not put here dangerous aliases.
alias dkill='docker kill $(docker ps -q)'
alias drm='docker rm $(docker ps -a -q)'
alias dclear='dkill;drm'
alias dlogs='find ${CORTEX_ROOT}/logs | grep "\.log" | xargs rm'
alias softclean='dkill;drm;dlogs'
alias dstat='docker stats $(docker ps --format={{.Names}})'
alias cdax='cd ${CORTEX_ROOT}/axonius-libs/src/libs/axonius-py/axonius'
