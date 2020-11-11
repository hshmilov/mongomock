#!/usr/bin/env bash
set -e # from now on exit on any error
cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1
source bash_imports.sh
if [ `docker ps | grep -c $DOCKER_NAME` -eq "0" ]; then
  echo "host container is not running..."
  exit 1
fi

source ./prepare_python_env.sh

if [[ $(uname -r) =~ .*Microsoft || $(uname -s) =~ MINGW.* || "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows host
    if [[ ! $(uname -r) =~ .*Microsoft ]]; then
      docker() {
          if [ -f '/c/Program Files/Docker/Docker/Resources/bin/docker' ];then
            realdocker='/c/Program Files/Docker/Docker/Resources/bin/docker'
          else
            realdocker=`which docker.exe`
          fi
          export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"
          printf "%s\0" "$@" > /tmp/args.txt
          winpty bash -c "xargs -0a /tmp/args.txt '$realdocker'"
      }
    fi
    docker exec -it $DOCKER_NAME /bin/bash -c "python3 ./devops/create_pth.py; bash"
    unset -f docker
    exit 0
else
  docker exec -it $DOCKER_NAME /bin/bash -c "python3 ./devops/create_pth.py; bash"
fi