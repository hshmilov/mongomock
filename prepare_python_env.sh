#!/usr/bin/env bash

set -e # from now on exit on any error

export CORTEX_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $CORTEX_ROOT/venv/bin/activate

#docker shortcuts
alias dkill='docker kill $(docker ps -q)'
alias drm='docker rm $(docker ps -a -q)'
alias drmi='docker rmi $(docker images -q -f dangling=true)'
alias dclear='dkill;drm;drmi'
alias drvol='docker volume rm $(docker volume ls -q)'
alias dlogs='find ${CORTEX_ROOT}/logs | grep "\.log" | xargs rm'
alias softclean='dkill;drm;drvol;dlogs'
alias dstat='docker stats $(docker ps --format={{.Names}})'
