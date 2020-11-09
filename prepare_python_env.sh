#!/usr/bin/env bash
# docker shortcuts. Notice ! This file is used by customers, so we should not put here dangerous aliases.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
alias dkill='docker kill $(docker ps -q)'
alias drm='docker rm $(docker ps -a -q)'
alias dclear='dkill;drm'
alias drvol='docker volume rm $(docker volume ls -q)'
alias dlogs='find ${CORTEX_ROOT}/logs | grep "\.log" | xargs rm'
alias softclean='dkill;drm;dlogs'
alias dstat='docker stats $(docker ps --format={{.Names}})'
alias cdax='cd ${CORTEX_ROOT}/axonius-libs/src/libs/axonius-py/axonius'
alias axd=$DIR/devops_debug_wrapper.sh
