#!/usr/bin/env bash

DOCKER_NAME='axonius-manager'
IMAGE_NAME='nexus.pub.axonius.com/axonius/axonius-manager'
DOCKER_SOCK='/var/run/docker.sock'
WEAVE_SOCK='/var/run/weave/weave.sock'
WEAVE_PATH='/var/run/weave'
WEAVE_BIN_PATH=$(command -v weave) || WEAVE_BIN_PATH='/usr/local/bin/weave'
AXONIUS_SH='/home/ubuntu/cortex/axonius.sh'
CORTEX_PATH='/home/ubuntu/cortex'
INSTANCE_CONTROL_SSH_KEYS='plugins/instance_control/rsa_keys'
DEFAULT_ROOT_DOCKER_DIR='/var/lib/docker'

DOCKER_NETWORK_NAME='axonius'
CUSTOMER_CONF_PATH='.axonius_settings/customer_conf.json'
DEFAULT_DOCKER_SUBNET_IP_RANGE='172.18.254.0/24'
DOCKER_BRIDGE_INTERFACE_NAME='br-ax-docker'

function create_docker_network {
  create_jq
  if [ -f "$CUSTOMER_CONF_PATH" ]; then
    docker_network_subnet=$(./infrastructures/host/utils/jq .'"docker-network-subnet"' "$CUSTOMER_CONF_PATH")
  else
    docker_network_subnet=null
  fi
  [ "$docker_network_subnet" = null ] && docker_network_subnet=$DEFAULT_DOCKER_SUBNET_IP_RANGE
  if ! docker network inspect "$DOCKER_NETWORK_NAME" > /dev/null 2>&1 ; then
    echo "Creating docker network $docker_network_subnet"
    docker network create --subnet="$docker_network_subnet" --opt "com.docker.network.bridge.name=$DOCKER_BRIDGE_INTERFACE_NAME" "$DOCKER_NETWORK_NAME"
  fi
}

function create_jq {
  if [[ $(uname -r) =~ .*Microsoft || $(uname -s) =~ MINGW.* || "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    if [ ! -f ./infrastructures/host/utils/jq.exe ]; then
      cp -p ./infrastructures/host/utils/jq-win32.exe ./infrastructures/host/utils/jq.exe
    fi
  else
    if [ ! -f ./infrastructures/host/utils/jq ]; then
      if [[ "$OSTYPE" == "darwin"* ]]; then
        # OSX
        cp -p ./infrastructures/host/utils/jq-osx-amd64 ./infrastructures/host/utils/jq
      else
        # Linux
        cp -p ./infrastructures/host/utils/jq-linux32 ./infrastructures/host/utils/jq
      fi
    fi
  fi
}

function run_in_axonius_manager {
    python3 ./devops/create_pth.py >/dev/null
    cd "$(dirname "$0")"
    cd devops
    python3 -u axonius_system.py "$@"
}

function unset_docker_if_needed {
  if [[ $(uname -s) =~ MINGW.* || "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    unset -f docker
  fi
}

function create_axonius_manager {
  create_docker_network
  mkdir -p logs/manager
  if [[ $(uname -r) =~ .*Microsoft || $(uname -s) =~ MINGW.* || "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows host
    if [[ ! $(uname -r) =~ .*Microsoft ]]; then
      # Fix docker winpty in mingw
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
    if [ $(/bin/sh -c "docker ps | grep -c $DOCKER_NAME") -eq "0" ]; then
      docker run -d -e DOCKER_HOST="tcp://host.docker.internal:2375" -e SERVICE_DIR="$(pwd)" -v "$(pwd)":"$(pwd)" -v "$(pwd)":/home/ubuntu/cortex --name="$DOCKER_NAME" --net="$DOCKER_NETWORK_NAME" $IMAGE_NAME
    fi
    return 0
  fi
  if [ $(docker ps | grep -c $DOCKER_NAME) -eq "0" ]; then
    ./get_metrics.sh &
    weave_mount=''
    pwd_mount=''
    [ -f "${WEAVE_BIN_PATH}" ] && [ ! -d "${WEAVE_PATH}" ] && sudo mkdir "${WEAVE_PATH}"
    [ -d "${WEAVE_PATH}" ] && weave_mount="-v ${WEAVE_PATH}:${WEAVE_PATH}"
    [ "$(pwd)" != "$CORTEX_PATH" ] && pwd_mount="-v $(pwd):$(pwd)"
    echo docker run -d -v "$DOCKER_SOCK":"$DOCKER_SOCK" -v "$DEFAULT_ROOT_DOCKER_DIR":"$DEFAULT_ROOT_DOCKER_DIR" "$weave_mount" "$pwd_mount" -e SERVICE_DIR="$(pwd)" -v "$(pwd)":/home/ubuntu/cortex -v "$(pwd)"/"$INSTANCE_CONTROL_SSH_KEYS":/root/.ssh --name="$DOCKER_NAME" --net="$DOCKER_NETWORK_NAME" --network-alias="$DOCKER_NAME" "$IMAGE_NAME" | /bin/sh
  fi
}

alias dkill='docker kill $(docker ps -q)'
alias drm='docker rm $(docker ps -a -q)'
alias dclear='dkill;drm'
alias drvol='docker volume rm $(docker volume ls -q)'
alias dlogs='find ${CORTEX_ROOT}/logs | grep "\.log" | xargs rm'
alias softclean='dkill;drm;dlogs'
alias dstat='docker stats $(docker ps --format={{.Names}})'
alias cdax='cd ${CORTEX_ROOT}/axonius-libs/src/libs/axonius-py/axonius'
